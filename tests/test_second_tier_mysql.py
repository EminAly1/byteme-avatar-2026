"""Real MySQL second-tier evidence, capacity locks and company ledger invariants."""
import copy
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal
from threading import Event
from uuid import uuid4

import pytest
from sqlalchemy import event, func, select
from sqlalchemy.orm import Session

from app import models as m, services, second_tier
from app.commands import get_engine as command_engine
from test_core_mysql import post, assert_ledger
from test_transfers_returns_mysql import snapshot, ordered_race, concurrent

pytestmark = pytest.mark.skipif(os.getenv('AVATAR_CORE_MYSQL_TEST') != '1', reason='Isolated *_test MySQL required')
TIME = '2026-10-26T10:00:00Z'


@pytest.fixture
def delivered(core_client, request):
    c = core_client
    unit = getattr(request, 'param', 'package')
    supplier = post(c, '/parties', {'name':'KURGUSAL tedarikçi','roles':['supplier']})
    a = post(c, '/parties', {'name':'KURGUSAL Market A','roles':['customer'],'contact':'a@example.invalid'})
    x = post(c, '/parties', {'name':'KURGUSAL Dağıtıcı X','roles':['customer'],'contact':'x@example.invalid'})
    w = post(c, '/locations', {'name':'KURGUSAL depo'})
    q = post(c, '/locations', {'name':'KURGUSAL karantina','kind':'quarantine'})
    product = post(c, '/products', {'sku':'SECOND-TIER','name':'KURGUSAL ürün','type':'finished','base_unit':unit,
                                   **({'package_weight_kg':'1'} if unit == 'package' else {})})
    receipt = post(c, '/receipts', {'supplier_id':supplier['id'],'location_id':w['id'],
        'received_at':'2026-10-24T08:00:00Z','lines':[{'product_id':product['id'],'external_lot_code':'KURGUSAL-ST',
        'quantity':'30','total_cost':'300.00'}]})
    lot = receipt['lines'][0]['lot_id']
    sale = post(c, '/sales', {'customer_id':a['id'],'sold_at':'2026-10-25T08:00:00Z',
        'lines':[{'lot_id':lot,'location_id':w['id'],'quantity':'30','unit':unit,'unit_price':'20'}]})
    shipment = post(c, '/shipments', {'customer_id':a['id'],'sale_id':sale['id'],'shipped_at':'2026-10-25T09:00:00Z',
        'lines':[{'sale_line_id':sale['lines'][0]['id'],'lot_id':lot,'location_id':w['id'],'quantity':'30','unit':unit}]})
    return {'c':c,'a':a['id'],'x':x['id'],'w':w['id'],'q':q['id'],'lot':lot,'product':product['id'],
            'sale':sale,'shipment':shipment,'line':shipment['lines'][0],'unit':unit}


def body(s, quantity='12'):
    return {'source_shipment_line_id':s['line']['id'],'recipient_party_id':s['x'],'quantity':quantity,'unit':s['unit'],
            'distributed_at':TIME,'reference':'KURGUSAL-'+str(uuid4()),'evidence_note':'KURGUSAL operatör bildirimi'}


def create(s, data=None, key=None, status=201):
    return post(s['c'], '/distributions/second-tier', data or body(s), key, status)


def returning(s, quantity='18', timestamp=TIME):
    return {'sale_id':s['sale']['id'],'acceptance_location_id':s['q'],'reason':'KURGUSAL iade','returned_at':timestamp,
            'lines':[{'sale_line_id':s['sale']['lines'][0]['id'],'quantity':quantity,'unit':s['unit']}]}


def raw(s, path, data, key=None):
    return s['c'].post('/v1'+path, json=data, headers={'Idempotency-Key':key or str(uuid4())})


def test_record_is_real_fk_snapshot_and_changes_no_old_table(delivered, mysql_core):
    s=delivered; before=snapshot(mysql_core); result=create(s); after=snapshot(mysql_core)
    assert all(before[t]==after[t] for t in before if t not in ['second_tier_distributions','idempotency_requests'])
    assert result['source_lot_id']==s['lot'] and result['product_id']==s['product']
    assert result['source_customer_id']==s['a'] and result['source_shipment_id']==s['shipment']['id']
    assert result['recipient_name']=='KURGUSAL Dağıtıcı X' and result['recipient_contact']=='x@example.invalid'
    assert result['recording_basis']=='system_operator_report_unverified_by_market'
    assert result['market_remaining_quantity'] is result['recipient_physical_stock_quantity'] is None
    assert s['c'].get('/v1/distributions/second-tier/'+result['id']).json()==result
    with Session(mysql_core) as db, db.begin():
        recipient=db.get(m.Party,s['x']);recipient.name='KURGUSAL yeni ad';recipient.contact=None
    assert s['c'].get('/v1/distributions/second-tier/'+result['id']).json()==result
    assert_ledger(mysql_core)


def test_replay_conflict_reference_uniqueness_and_concurrent_same_key(delivered, mysql_core):
    s=delivered; data=body(s); key=str(uuid4()); result=create(s,data,key); before=snapshot(mysql_core)
    assert create(s,data,key)==result and snapshot(mysql_core)==before
    changed=copy.deepcopy(data); changed['quantity']='13'
    assert create(s,changed,key,409)['error']['code']=='IDEMPOTENCY_CONFLICT'
    assert create(s,data,status=409)['error']['code']=='CONFLICT'  # Duplicate source reference, another key.
    assert snapshot(mysql_core)==before
    data=body(s,'2'); key=str(uuid4())
    responses=concurrent([lambda:raw(s,'/distributions/second-tier',data,key)]*2)
    assert [r.status_code for r in responses]==[201,201] and responses[0].json()==responses[1].json()
    with Session(mysql_core) as db:assert db.scalar(select(func.sum(m.SecondTierDistribution.quantity)))==14


@pytest.mark.parametrize('change,status', [
    ({'quantity':'0'},422),({'quantity':'-1'},422),({'quantity':12.0},422),({'quantity':'12.5'},422),
    ({'quantity':'31'},409),({'quantity':'0.0000001'},422),({'unit':'kg'},422),
    ({'source_shipment_line_id':str(uuid4())},404),({'recipient_party_id':str(uuid4())},404),
    ({'distributed_at':'2026-10-24T08:00:00Z'},422),({'distributed_at':'2099-01-01T00:00:00Z'},422),
    ({'distributed_at':'2026-10-26T10:00:00'},422),({'reference':''},422),({'evidence_note':' '},422),
    ({'source_customer_id':str(uuid4())},422),({'source_lot_id':str(uuid4())},422),({'product_id':str(uuid4())},422),
])
def test_invalid_claims_leave_no_writes(delivered,mysql_core,change,status):
    s=delivered; data=body(s); data.update(change); before=snapshot(mysql_core)
    create(s,data,status=status); assert snapshot(mysql_core)==before


@pytest.mark.parametrize('field',['customer','lot','product','movement','quantity'])
def test_inconsistent_real_source_evidence_is_rejected(delivered,mysql_core,field):
    s=delivered
    with Session(mysql_core) as db, db.begin():
        line=db.get(m.ShipmentLine,s['line']['id'])
        if field=='customer':db.get(m.Shipment,s['shipment']['id']).customer_id=s['x']
        elif field=='lot':
            lot=m.Lot(product_id=s['product'],external_code='KURGUSAL wrong',received_at=m.now(),original_quantity=30,total_cost=300)
            db.add(lot);db.flush();line.lot_id=lot.id
        elif field=='product':
            p=m.Product(sku='OTHER',name='KURGUSAL same name',type='finished',base_unit='kg');db.add(p);db.flush();line.product_id=p.id
        elif field=='movement':db.get(m.StockMovement,line.stock_movement_id).type='wrong'
        else:line.quantity=29
    before=snapshot(mysql_core)
    assert create(s,status=409)['error']['code']=='SOURCE_SHIPMENT_MISMATCH'
    assert snapshot(mysql_core)==before


@pytest.mark.parametrize('delivered',['kg','unit'],indirect=True)
def test_units_and_exact_remaining_documentation(delivered):
    s=delivered; quantity='12.123456' if s['unit']=='kg' else '12'; create(s,body(s,quantity))
    trace=s['c'].get('/v1/lots/'+s['lot']+'/trace').json()
    item=trace['unknown_distributions'][0]
    assert item['market_remaining_quantity'] is item['final_consumer_sold_quantity'] is None
    assert item['unallocated_documented_quantities'][0]['quantity']==format(Decimal(30)-Decimal(quantity),'.6f')
    if s['unit']=='unit':create(s,body(s,'0.5'),status=422)


def test_recall_get_and_bidirectional_trace_use_new_evidence_without_new_genealogy(delivered,mysql_core):
    s=delivered; recall=post(s['c'],'/recalls',{'source_lot_id':s['lot'],'reason':'KURGUSAL recall'})
    before=snapshot(mysql_core); result=create(s); after=snapshot(mysql_core)
    assert all(before[t]==after[t] for t in ['lots','lot_links','operations','operation_inputs','operation_outputs','recalls','recall_lots','stock_movements'])
    updated=s['c'].get('/v1/recalls/'+recall['id']).json()
    assert recall['report']['second_tier_distributions']==[]
    assert updated['report']['second_tier_distributions']==[result]
    assert updated['report']['total_shipped_quantities']==recall['report']['total_shipped_quantities']
    assert [b['customer_id'] for b in updated['report']['buyers']]==[s['a']]
    for direction in ['forward','backward']:
        trace=s['c'].get('/v1/lots/'+s['lot']+'/trace',params={'direction':direction}).json()
        assert trace['second_tier_distributions']==[result]
        assert trace['unknown_distributions'][0]['second_tier_recipients'][0]['recipient_party_id']==s['x']
        assert trace['unknown_distributions'][0]['market_remaining_quantity'] is None


@pytest.mark.parametrize('first',['return','distribution'])
def test_return_and_distribution_exact_limit_in_either_order(delivered,first):
    s=delivered; actions={'return':lambda:post(s['c'],'/returns',returning(s)), 'distribution':lambda:create(s)}
    actions[first]();actions['distribution' if first=='return' else 'return']()
    assert create(s,body(s,'1'),status=409)['error']['code']=='DOCUMENTED_QUANTITY_EXCEEDED'
    assert post(s['c'],'/returns',returning(s,'1'),status=409)['error']['code']=='DOCUMENTED_QUANTITY_EXCEEDED'
    report=s['c'].get('/v1/lots/'+s['lot']+'/trace').json()
    assert report['unknown_distributions'][0]['unallocated_documented_quantities'][0]['quantity']=='0.000000'
    assert report['unknown_distributions'][0]['market_remaining_quantity'] is None


@pytest.mark.parametrize('first',['return','distribution'])
def test_temporal_conflict_is_explicit_and_atomic(delivered,mysql_core,first):
    s=delivered
    if first=='return':post(s['c'],'/returns',returning(s,'2','2026-10-26T11:00:00Z'))
    else:
        data=body(s);data['distributed_at']='2026-10-26T11:00:00Z';create(s,data)
    before=snapshot(mysql_core)
    result=create(s,status=409) if first=='return' else post(s['c'],'/returns',returning(s,'2'),status=409)
    assert result['error']['code']=='DISTRIBUTION_CHRONOLOGY_CONFLICT' and snapshot(mysql_core)==before


@pytest.mark.parametrize('first',['return','distribution'])
def test_return_distribution_real_lock_race_both_orders(delivered,mysql_core,monkeypatch,first):
    s=delivered; actions={'return':lambda:raw(s,'/returns',returning(s,'20')),
                          'distribution':lambda:raw(s,'/distributions/second-tier',body(s,'20'))}
    winner,loser=ordered_race(monkeypatch,actions[first],actions['distribution' if first=='return' else 'return'],lock='sale')
    assert winner.status_code==201 and loser.status_code==409
    assert loser.json()['error']['code']=='DOCUMENTED_QUANTITY_EXCEEDED'
    with Session(mysql_core) as db:
        d,r,_=second_tier.totals(db,s['line']['id']);assert d+r==20
    assert_ledger(mysql_core)


def test_two_concurrent_recipients_cannot_overallocate(delivered,mysql_core):
    s=delivered; y=post(s['c'],'/parties',{'name':'KURGUSAL Y','roles':['supplier']})
    a=body(s,'20');b=body(s,'20');b['recipient_party_id']=y['id']
    results=concurrent([lambda:raw(s,'/distributions/second-tier',a),lambda:raw(s,'/distributions/second-tier',b)])
    assert sorted(r.status_code for r in results)==[201,409]
    with Session(mysql_core) as db:assert db.scalar(select(func.sum(m.SecondTierDistribution.quantity)))==20


@pytest.mark.parametrize('first',['recall','distribution'])
def test_recall_distribution_real_lock_race_both_orders(delivered,monkeypatch,first):
    s=delivered; actions={'recall':lambda:raw(s,'/recalls',{'source_lot_id':s['lot'],'reason':'KURGUSAL yarış'}),
                          'distribution':lambda:raw(s,'/distributions/second-tier',body(s))}
    winner,loser=ordered_race(monkeypatch,actions[first],actions['distribution' if first=='recall' else 'recall'])
    assert winner.status_code==loser.status_code==201
    recall=winner.json() if first=='recall' else loser.json()
    report=s['c'].get('/v1/recalls/'+recall['id']).json()['report']
    assert len(report['second_tier_distributions'])==1 and report['lots'][0]['blocked']


def test_late_error_rolls_back_audit_and_idempotency(delivered,mysql_core,monkeypatch):
    s=delivered;before=snapshot(mysql_core);real=second_tier.detail
    def fail(db,row):
        assert db.get(m.SecondTierDistribution,row.id) is not None
        raise RuntimeError('Controlled post-flush failure')
    monkeypatch.setattr(second_tier,'detail',fail)
    with pytest.raises(RuntimeError,match='post-flush'):create(s)
    assert snapshot(mysql_core)==before
    monkeypatch.setattr(second_tier,'detail',real);create(s)


def test_auth_pagination_filters_unknown_and_same_recipient(delivered):
    s=delivered;data=body(s);one=create(s,data);two=create(s,body(s,'3'))
    base='/v1/distributions/second-tier'
    assert s['c'].get(base,headers={'X-API-Key':'invalid'}).status_code==401
    assert s['c'].post(base,json=data).status_code==422
    assert s['c'].get(base+'/'+str(uuid4())).status_code==404
    assert s['c'].get(base+'/not-uuid').status_code==422
    page=s['c'].get(base,params={'limit':1,'source_shipment_line_id':s['line']['id'],'recipient_party_id':s['x']}).json()
    assert page['next_cursor'] and len(page['items'])==1
    next_page=s['c'].get(base,params={'limit':1,'cursor':page['next_cursor']}).json()
    assert {page['items'][0]['id'],next_page['items'][0]['id']}=={one['id'],two['id']}
    assert s['c'].get(base,params={'source_lot_id':str(uuid4())}).json()['items']==[]
    data['recipient_party_id']=s['a'];create(s,data,status=422)


def test_real_second_tier_1213_retries_without_duplicate_evidence(delivered,mysql_core,monkeypatch):
    s=delivered;held,source_held=Event(),Event();calls=[];errors=[];real=services.lock_lots
    with Session(mysql_core) as db,db.begin():
        padding=[m.Party(name='KURGUSAL bakım',roles=['supplier']) for _ in range(60)]
        db.add_all(padding);db.flush();ids=[p.id for p in padding]+[s['x']]
    def locked(db,identifiers):
        result=real(db,identifiers);calls.append(1);source_held.set();return result
    monkeypatch.setattr(services,'lock_lots',locked)
    def maintenance():
        with Session(mysql_core) as db,db.begin():
            rows=db.scalars(select(m.Party).where(m.Party.id.in_(ids)).order_by(m.Party.id).with_for_update()).all()
            for row in rows:row.name+=' held'
            db.flush();held.set();assert source_held.wait(5)
            db.scalar(select(m.Lot).where(m.Lot.id==s['lot']).with_for_update())
    observed=command_engine()
    def capture(context):
        if getattr(context.original_exception,'args',(None,))[0]==1213:errors.append(1213)
    event.listen(observed,'handle_error',capture)
    try:
        with ThreadPoolExecutor(2) as pool:
            blocker=pool.submit(maintenance);assert held.wait(5)
            writer=pool.submit(create,s);result=writer.result(timeout=15);blocker.result(timeout=10)
        assert errors and len(calls)==2 and result['quantity']=='12.000000'
        with Session(mysql_core) as db:assert db.scalar(select(func.count()).select_from(m.SecondTierDistribution))==1
        assert_ledger(mysql_core)
    finally:event.remove(observed,'handle_error',capture)


@pytest.mark.parametrize('state',['blocked','expired'])
def test_historical_reporting_does_not_hide_blocked_or_expired_goods(delivered,mysql_core,state):
    s=delivered
    with Session(mysql_core) as db,db.begin():
        lot=db.get(m.Lot,s['lot'])
        if state=='blocked':lot.blocked=True
        else:lot.expires_at=datetime(2026,10,25).date()
    before=snapshot(mysql_core);create(s);after=snapshot(mysql_core)
    assert all(before[t]==after[t] for t in before if t not in ['second_tier_distributions','idempotency_requests'])


def test_standalone_shipment_evidence_creates_no_sale_or_second_issue(delivered,mysql_core):
    s=delivered;c=s['c']
    supplier=post(c,'/parties',{'name':'KURGUSAL supplier2','roles':['supplier']})
    receipt=post(c,'/receipts',{'supplier_id':supplier['id'],'location_id':s['w'],'received_at':'2026-10-24T08:00:00Z',
        'lines':[{'product_id':s['product'],'external_lot_code':'KURGUSAL independent','quantity':'10','total_cost':'100'}]})
    lot=receipt['lines'][0]['lot_id']
    shipment=post(c,'/shipments',{'customer_id':s['a'],'shipped_at':'2026-10-25T09:00:00Z',
                               'lines':[{'lot_id':lot,'location_id':s['w'],'quantity':'10','unit':s['unit']}]})
    data=body(s,'4');data['source_shipment_line_id']=shipment['lines'][0]['id'];before=snapshot(mysql_core)
    result=create(s,data);after=snapshot(mysql_core)
    assert result['source_lot_id']==lot and all(before[t]==after[t] for t in before if t not in ['second_tier_distributions','idempotency_requests'])
