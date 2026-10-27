"""Task13 acceptance: real InnoDB, append-only corrections and quarantine."""
import copy
import hashlib
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from datetime import datetime, timezone, timedelta
from decimal import Decimal as D
from threading import Barrier, Event, current_thread
from uuid import uuid4

import pytest
from sqlalchemy import event, select, func
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app import models as m, services, inventory_adjustments as adjustments
from app.commands import get_engine as command_engine
from app.errors import DomainError
from test_core_mysql import post, assert_ledger, scenario

pytestmark = pytest.mark.skipif(os.getenv('AVATAR_CORE_MYSQL_TEST') != '1', reason='Separate *_test MySQL required')


@pytest.fixture
def stock_case(core_client):
    c = core_client
    supplier = post(c, '/parties', {'name':'KURGUSAL transfer tedarikçisi','roles':['supplier']})
    customer = post(c, '/parties', {'name':'KURGUSAL müşteri','roles':['customer'],'contact':'fictional@example.invalid'})
    a = post(c, '/locations', {'name':'KURGUSAL Depo A'})
    b = post(c, '/locations', {'name':'KURGUSAL Depo B'})
    q = post(c, '/locations', {'name':'KURGUSAL karantina','kind':'quarantine'})
    q2 = post(c, '/locations', {'name':'KURGUSAL karantina2','kind':'quarantine'})
    product = post(c, '/products', {'sku':'TASK13','name':'KURGUSAL lotlu ürün','type':'raw','base_unit':'kg'})
    receipt = post(c, '/receipts', {'supplier_id':supplier['id'],'location_id':a['id'],'received_at':'2026-10-25T08:00:00Z','lines':[
        {'product_id':product['id'],'external_lot_code':'KURGUSAL-TRANSFER-001','quantity':'20','total_cost':'194.00'}]})
    return {'client':c,'a':a['id'],'b':b['id'],'q':q['id'],'q2':q2['id'],
            'product':product['id'],'customer':customer['id'],'lot':receipt['lines'][0]['lot_id']}


def transfer_body(s, quantity='7', source=None, target=None):
    return {'from_location_id':source or s['a'],'to_location_id':target or s['b'],
            'lot_id':s['lot'],'quantity':quantity,'unit':'kg','reason':'KURGUSAL test transferi'}


def sell(s, quantity='5', price='20.00', location=None):
    return post(s['client'], '/sales', {'customer_id':s['customer'],'lines':[
        {'lot_id':s['lot'],'location_id':location or s['a'],'quantity':quantity,'unit':'kg','unit_price':price}]})


def ship(s, sale):
    return post(s['client'], '/shipments', ship_body(s, sale))


def ship_body(s, sale):
    return {'customer_id':s['customer'],'sale_id':sale['id'],'lines':[
        {'sale_line_id':line['id'],'lot_id':line['lot_id'],'location_id':line['location_id'],
         'quantity':line['quantity'],'unit':line['unit']} for line in sale['lines']]}


def return_body(s, sale, quantity='2'):
    return {'sale_id':sale['id'],'acceptance_location_id':s['q'],'reason':'KURGUSAL müşteri iadesi',
            'lines':[{'sale_line_id':sale['lines'][0]['id'],'quantity':quantity,'unit':'kg'}]}


def cancel_body(s):
    return {'acceptance_location_id':s['q'],'reason':'KURGUSAL sevk öncesi iptal'}


def balance(s, location):
    rows = s['client'].get('/v1/stocks', params={'lot_id':s['lot'],'location_id':location}).json()['items']
    return D(rows[0]['quantity']) if rows else D(0)


def snapshot(engine):
    with engine.connect() as connection:
        return {name:hashlib.sha256('\n'.join(sorted(repr(tuple(row)) for row in connection.execute(table.select()))).encode()).hexdigest()
                for name,table in m.Base.metadata.tables.items()}


def counters(engine, lot_id):
    with Session(engine) as db:
        lot = db.get(m.Lot,lot_id)
        return lot.original_quantity,lot.total_cost,lot.consumed_quantity,lot.consumed_cost


def test_transfer_20_to_13_and_7_preserves_exact_cost_and_fks(stock_case, mysql_core):
    s=stock_case;before=counters(mysql_core,s['lot'])
    result=post(s['client'],'/transfers',transfer_body(s))
    assert (balance(s,s['a']),balance(s,s['b']))==(13,7)
    assert sum((balance(s,s[k]) for k in ['a','b','q']))==20
    assert counters(mysql_core,s['lot'])==before==(D(20),D(194),D(0),D(0))
    assert result['cost_effect']=='none' and result['product_id']==s['product']
    assert [D(row['quantity']) for row in result['movements']]==[-7,7]
    assert {row['transfer_group_id'] for row in result['movements']}=={result['id']}
    assert all(row['operation_id'] is None and row['reversal_of'] is None for row in result['movements'])
    assert s['client'].get('/v1/transfers/'+result['id']).json()==result
    assert s['client'].get('/v1/transfers',params={'lot_id':s['lot']}).json()['items'][0]['id']==result['id']
    post(s['client'],'/transfers',transfer_body(s,'2',s['b'],s['a']))
    assert (balance(s,s['a']),balance(s,s['b']))==(15,5)
    trace=s['client'].get('/v1/lots/'+s['lot']+'/trace').json()
    assert len(trace['transfers'])==2 and trace['source_lot']['id']==s['lot']
    assert_ledger(mysql_core)


@pytest.mark.parametrize('change,status',[
    ({'to_location_id':'same'},422),({'to_location_id':str(uuid4())},404),
    ({'quantity':'21'},409),({'unit':'package'},422),({'quantity':'0'},422),
    ({'quantity':7.0},422),({'reason':''},422),({'transferred_at':'2020-01-01T00:00:00Z'},422)])
def test_invalid_transfers_are_atomic(stock_case,mysql_core,change,status):
    s=stock_case;body=transfer_body(s);change=copy.deepcopy(change)
    if change.get('to_location_id')=='same':change['to_location_id']=s['a']
    body.update(change);before=snapshot(mysql_core)
    post(s['client'],'/transfers',body,status=status)
    assert snapshot(mysql_core)==before


def test_transfer_late_failure_rolls_back_both_sides_and_idempotency(stock_case,mysql_core,monkeypatch):
    s=stock_case;before=snapshot(mysql_core);real=services.move;calls=[]
    def fail_second(*args,**kwargs):
        result=real(*args,**kwargs);calls.append(result.id)
        if len(calls)==2:raise DomainError('CONTROLLED_FAILURE','KURGUSAL rollback testi')
        return result
    monkeypatch.setattr(services,'move',fail_second)
    assert post(s['client'],'/transfers',transfer_body(s),status=409)['error']['code']=='CONTROLLED_FAILURE'
    assert len(calls)==2 and snapshot(mysql_core)==before


def test_transfer_idempotency_and_pagination(stock_case,mysql_core):
    s=stock_case;body=transfer_body(s);key=str(uuid4())
    result=post(s['client'],'/transfers',body,key);before=snapshot(mysql_core)
    assert post(s['client'],'/transfers',body,key)==result and snapshot(mysql_core)==before
    body['quantity']='8'
    assert post(s['client'],'/transfers',body,key,409)['error']['code']=='IDEMPOTENCY_CONFLICT'
    post(s['client'],'/transfers',transfer_body(s,'1'))
    first=s['client'].get('/v1/transfers?limit=1').json();assert first['next_cursor']
    second=s['client'].get('/v1/transfers',params={'limit':1,'cursor':first['next_cursor']}).json()
    assert len({first['items'][0]['id'],second['items'][0]['id']})==2 and second['next_cursor'] is None


@pytest.mark.parametrize('gate',['blocked','expired'])
def test_containment_policy_never_releases_quarantine(stock_case,mysql_core,gate):
    s=stock_case
    with Session(mysql_core) as db,db.begin():
        lot=db.get(m.Lot,s['lot'])
        if gate=='blocked':lot.blocked=True
        else:lot.expires_at=datetime.now(timezone.utc).date()-timedelta(days=1)
    post(s['client'],'/transfers',transfer_body(s),status=409)
    post(s['client'],'/transfers',transfer_body(s,target=s['q']))
    post(s['client'],'/transfers',transfer_body(s,'3',s['q'],s['q2']))
    assert post(s['client'],'/transfers',transfer_body(s,'1',s['q'],s['b']),status=409)['error']['code']=='QUARANTINE_RELEASE_REQUIRED'
    stocks=s['client'].get('/v1/stocks',params={'lot_id':s['lot']}).json()['items']
    assert all(row['available_quantity']=='0.000000' for row in stocks)
    assert counters(mysql_core,s['lot'])[2:]==(0,0)
    assert_ledger(mysql_core)


def test_external_producer_is_not_general_transfer_destination(stock_case,mysql_core):
    s=stock_case;p=post(s['client'],'/parties',{'name':'KURGUSAL üretici','roles':['producer']})
    external=post(s['client'],'/locations',{'name':'KURGUSAL dış konum','kind':'external_producer','party_id':p['id']})
    before=snapshot(mysql_core)
    post(s['client'],'/transfers',transfer_body(s,target=external['id']),status=422)
    assert snapshot(mysql_core)==before


def test_single_shipped_return_is_quarantined_with_exact_financial_fks(stock_case,mysql_core):
    s=stock_case;sale=sell(s);shipment=ship(s,sale);before_counters=counters(mysql_core,s['lot'])
    returned=post(s['client'],'/returns',return_body(s,sale,'5'))
    line=returned['lines'][0]
    assert line['sale_line_id']==sale['lines'][0]['id'] and line['shipment_line_id']==shipment['lines'][0]['id']
    assert line['lot_id']==s['lot'] and line['movement']['reversal_of'] is None
    assert returned['credit_amount']=='100.00' and returned['restored_cost']=='48.500000'
    assert returned['cash_refund_status']=='not_recorded' and returned['inventory_status']=='quarantine_only'
    assert (balance(s,s['a']),balance(s,s['q']))==(15,5)
    assert counters(mysql_core,s['lot'])==before_counters
    assert s['client'].get('/v1/sales/'+sale['id']).json()==sale
    assert s['client'].get('/v1/returns/'+returned['id']).json()==returned
    assert s['client'].get('/v1/returns',params={'sale_id':sale['id']}).json()['items'][0]['id']==returned['id']
    before=snapshot(mysql_core);profit=s['client'].get('/v1/sales/'+sale['id']+'/profitability').json()
    assert profit['net_revenue_eur']=='100.00' and profit['recognized_cost_eur']=='48.500000'
    assert profit['adjustments']['state']=='returned' and profit['net_after_adjustments']['net_revenue_eur']=='0.00'
    assert profit['net_after_adjustments']['gross_profit_eur']=='0.000000' and profit['net_after_adjustments']['margin_percent'] is None
    assert snapshot(mysql_core)==before
    trace=s['client'].get('/v1/lots/'+s['lot']+'/trace').json();entry=trace['buyers'][0]['quantities'][0]
    assert entry['recorded_sale_quantity']==entry['shipped_quantity']==entry['returned_quantity']=='5.000000'
    assert entry['recorded_delivery_less_returns_quantity']=='0.000000'
    assert trace['unknown_distributions'][0]['market_remaining_quantity'] is None
    assert trace['customer_returns'][0]['id']==returned['id']
    assert_ledger(mysql_core)


def test_partial_returns_cumulative_limit_replay_and_exact_rounding(stock_case,mysql_core):
    s=stock_case;sale=sell(s);ship(s,sale);key=str(uuid4());body=return_body(s,sale,'2')
    first=post(s['client'],'/returns',body,key);before=snapshot(mysql_core)
    assert post(s['client'],'/returns',body,key)==first and snapshot(mysql_core)==before
    second=post(s['client'],'/returns',return_body(s,sale,'1'))
    assert balance(s,s['q'])==3
    p=s['client'].get('/v1/sales/'+sale['id']+'/profitability').json()
    assert p['adjustments']['state']=='partially_returned' and p['adjustments']['return_credit_eur']=='60.00'
    assert p['net_after_adjustments']['net_revenue_eur']=='40.00' and p['net_after_adjustments']['recognized_cost_eur']=='19.400000'
    before=snapshot(mysql_core)
    assert post(s['client'],'/returns',return_body(s,sale,'3'),status=409)['error']['code']=='RETURN_EXCEEDS_SALE'
    assert snapshot(mysql_core)==before
    third=post(s['client'],'/returns',return_body(s,sale,'2'))
    assert sum(D(x['credit_amount']) for x in [first,second,third])==D(sale['total_amount'])
    assert sum(D(x['restored_cost']) for x in [first,second,third])==D(sale['lines'][0]['consumed_cost'])
    assert_ledger(mysql_core)


def test_fractional_returns_use_cumulative_credit_not_repeated_unit_rounding(stock_case,mysql_core):
    s=stock_case;sale=sell(s,'3','0.01');ship(s,sale)
    rows=[post(s['client'],'/returns',return_body(s,sale,q)) for q in ['0.5','0.5','2']]
    assert [x['credit_amount'] for x in rows]==['0.01','0.00','0.02']
    assert sum(D(x['restored_cost']) for x in rows)==D(sale['lines'][0]['consumed_cost'])
    assert counters(mysql_core,s['lot'])[2:]==(D(3),D('29.1'))


@pytest.mark.parametrize('case',['warehouse','unshipped','wrong_line','unit','before_delivery','duplicate','float'])
def test_invalid_customer_returns_leave_no_effect(stock_case,mysql_core,case):
    s=stock_case;sale=sell(s)
    if case!='unshipped':ship(s,sale)
    body=return_body(s,sale);status=422
    if case=='warehouse':body['acceptance_location_id']=s['a']
    if case=='unshipped':status=409
    if case=='wrong_line':body['lines'][0]['sale_line_id']=sell(s,'1')['lines'][0]['id']
    if case=='unit':body['lines'][0]['unit']='package'
    if case=='before_delivery':body['returned_at']='2020-01-01T00:00:00Z'
    if case=='duplicate':body['lines']*=2
    if case=='float':body['lines'][0]['quantity']=2.0
    before=snapshot(mysql_core);post(s['client'],'/returns',body,status=status);assert snapshot(mysql_core)==before


def test_full_cancel_preserves_originals_and_only_restores_quarantine(stock_case,mysql_core):
    s=stock_case;sale=sell(s);before_counters=counters(mysql_core,s['lot']);key=str(uuid4());body=cancel_body(s)
    result=post(s['client'],'/sales/'+sale['id']+'/cancel',body,key,200)
    assert result['lines'][0]['movement']['reversal_of']==sale['lines'][0]['stock_movement_id']
    assert result['lines'][0]['movement']['location_id']==s['a']
    hold=result['lines'][0]['quarantine_movements']
    assert [D(row['quantity']) for row in hold]==[-5,5]
    assert [row['location_id'] for row in hold]==[s['a'],s['q']]
    assert {row['transfer_group_id'] for row in hold}=={result['lines'][0]['id']}
    assert result['credit_amount']=='100.00' and result['restored_cost']=='48.500000'
    assert (balance(s,s['a']),balance(s,s['q']))==(15,5)
    assert counters(mysql_core,s['lot'])==before_counters and s['client'].get('/v1/sales/'+sale['id']).json()==sale
    before=snapshot(mysql_core)
    assert post(s['client'],'/sales/'+sale['id']+'/cancel',body,key,200)==result and snapshot(mysql_core)==before
    assert post(s['client'],'/sales/'+sale['id']+'/cancel',body,status=409)['error']['code']=='SALE_ALREADY_CANCELLED'
    assert post(s['client'],'/shipments',ship_body(s,sale),status=409)['error']['code']=='SALE_CANCELLED'
    assert post(s['client'],'/returns',return_body(s,sale),status=409)['error']['code']=='SALE_CANCELLED'
    assert s['client'].get('/v1/sales/'+sale['id']+'/cancellation').json()==result
    p=s['client'].get('/v1/sales/'+sale['id']+'/profitability').json()
    assert p['adjustments']['state']=='cancelled' and p['net_after_adjustments']['recognized_cost_eur']=='0.000000'
    trace=s['client'].get('/v1/lots/'+s['lot']+'/trace').json()
    assert trace['buyers'][0]['quantities'][0]['unshipped_sale_quantity']=='0.000000'
    assert trace['buyers'][0]['quantities'][0]['cancelled_sale_quantity']=='5.000000'
    assert trace['sale_cancellations'][0]['id']==result['id']
    # The database, not only an application check, forbids a second full reversal.
    with Session(mysql_core) as db:
        db.add(m.StockMovement(lot_id=s['lot'],location_id=s['q'],quantity=5,type='controlled-invalid',reversal_of=sale['lines'][0]['stock_movement_id']))
        with pytest.raises(IntegrityError):db.flush()
        db.rollback()
    assert_ledger(mysql_core)


@pytest.mark.parametrize('case',['shipped','warehouse','old_date'])
def test_unsafe_cancellation_rejected(stock_case,mysql_core,case):
    s=stock_case;sale=sell(s);body=cancel_body(s);status=422
    if case=='shipped':ship(s,sale);status=409
    if case=='warehouse':body['acceptance_location_id']=s['a']
    if case=='old_date':body['cancelled_at']='2020-01-01T00:00:00Z'
    before=snapshot(mysql_core);post(s['client'],'/sales/'+sale['id']+'/cancel',body,status=status);assert snapshot(mysql_core)==before


def test_non_tail_cancel_never_rewinds_cost_counters_or_reprices_history(stock_case,mysql_core):
    s=stock_case;first=sell(s,'3');later=sell(s,'7');before=counters(mysql_core,s['lot'])
    cancelled=post(s['client'],'/sales/'+first['id']+'/cancel',cancel_body(s),status=200)
    assert counters(mysql_core,s['lot'])==before==(20,194,10,97)
    final=sell(s,'10')
    assert counters(mysql_core,s['lot'])==(20,194,20,194)
    assert D(final['lines'][0]['consumed_cost'])==97 and balance(s,s['a'])==0 and balance(s,s['q'])==3
    assert s['client'].get('/v1/sales/'+later['id']).json()==later
    # Original gross cost = net recognized sale cost + separately recovered stock cost.
    assert sum(D(x['lines'][0]['consumed_cost']) for x in [later,final])+D(cancelled['restored_cost'])==194
    assert post(s['client'],'/transfers',transfer_body(s,'1',s['q'],s['a']),status=409)['error']['code']=='QUARANTINE_RELEASE_REQUIRED'


def concurrent(calls):
    barrier=Barrier(len(calls))
    def run(call):barrier.wait(timeout=10);return call()
    with ThreadPoolExecutor(len(calls)) as pool:return list(pool.map(run,calls))


def request(s,path,body,key=None):
    return s['client'].post('/v1'+path,json=body,headers={'Idempotency-Key':key or str(uuid4())})


@pytest.mark.parametrize('other',['transfer','sale'])
def test_racing_transfers_or_sale_cannot_overspend(stock_case,mysql_core,other):
    s=stock_case;body=transfer_body(s,'15')
    sale={'customer_id':s['customer'],'lines':[{'lot_id':s['lot'],'location_id':s['a'],'quantity':'15','unit':'kg','unit_price':'20'}]}
    results=concurrent([lambda:request(s,'/transfers',body),lambda:request(s,'/transfers' if other=='transfer' else '/sales',body if other=='transfer' else sale)])
    assert sorted(x.status_code for x in results)==[201,409]
    assert balance(s,s['a'])==5
    q,_,consumed,_=counters(mysql_core,s['lot']);assert balance(s,s['a'])+balance(s,s['b'])+consumed==q
    assert_ledger(mysql_core)


def ordered_race(monkeypatch,first,second,lock='lot'):
    """Hold a real first lock; prove the competing HTTP writer waits on MySQL."""
    held,release,started=Event(),Event(),Event()
    name='lock_lots' if lock=='lot' else 'get';real=getattr(services,name)
    def hooked(*args,**kwargs):
        result=real(*args,**kwargs)
        eligible=lock=='lot' or (len(args)>1 and args[1] is m.Sale and kwargs.get('lock'))
        if eligible and not held.is_set():
            held.set();assert release.wait(5),'Held transaction not released'
        return result
    monkeypatch.setattr(services,name,hooked)
    def loser():started.set();return second()
    with ThreadPoolExecutor(1,thread_name_prefix='winner') as winner,ThreadPoolExecutor(1,thread_name_prefix='loser') as loser_pool:
        f=winner.submit(first);assert held.wait(5);g=loser_pool.submit(loser);assert started.wait(3)
        try:
            with pytest.raises(TimeoutError):g.result(timeout=.15)
        finally:release.set()
        return f.result(timeout=10),g.result(timeout=10)


@pytest.mark.parametrize('first',['transfer','recall'])
def test_recall_transfer_real_lock_race(stock_case,mysql_core,monkeypatch,first):
    s=stock_case
    actions={'transfer':lambda:request(s,'/transfers',transfer_body(s)),
             'recall':lambda:request(s,'/recalls',{'source_lot_id':s['lot'],'reason':'KURGUSAL recall yarışı'})}
    a,b=ordered_race(monkeypatch,actions[first],actions['recall' if first=='transfer' else 'transfer'])
    assert a.status_code==201 and b.status_code==(201 if first=='transfer' else 409)
    stocks=s['client'].get('/v1/stocks',params={'lot_id':s['lot']}).json()['items'];assert all(x['blocked'] and x['available_quantity']=='0.000000' for x in stocks)
    assert_ledger(mysql_core)


def test_two_returns_cannot_exceed_sale_and_same_key_is_once(stock_case,mysql_core):
    s=stock_case;sale=sell(s);ship(s,sale);body=return_body(s,sale,'4')
    responses=concurrent([lambda:request(s,'/returns',body),lambda:request(s,'/returns',body)])
    assert sorted(x.status_code for x in responses)==[201,409] and balance(s,s['q'])==4
    key=str(uuid4());body=return_body(s,sale,'1')
    responses=concurrent([lambda:request(s,'/returns',body,key),lambda:request(s,'/returns',body,key)])
    assert all(x.status_code==201 for x in responses) and responses[0].json()==responses[1].json()
    assert balance(s,s['q'])==5
    with Session(mysql_core) as db:assert db.scalar(select(func.count()).select_from(m.CustomerReturn))==2
    assert_ledger(mysql_core)


@pytest.mark.parametrize('first',['return','cancel'])
@pytest.mark.parametrize('shipped',[False,True])
def test_return_cancel_serializes_source_sale(stock_case,mysql_core,monkeypatch,first,shipped):
    s=stock_case;sale=sell(s)
    if shipped:ship(s,sale)
    actions={'return':lambda:request(s,'/returns',return_body(s,sale)),
             'cancel':lambda:request(s,'/sales/'+sale['id']+'/cancel',cancel_body(s))}
    a,b=ordered_race(monkeypatch,actions[first],actions['cancel' if first=='return' else 'return'],lock='sale')
    results={first:a,('cancel' if first=='return' else 'return'):b}
    assert results['return'].status_code==(201 if shipped else 409)
    assert results['cancel'].status_code==(409 if shipped else 200)
    assert balance(s,s['q'])==(2 if shipped else 5)
    assert_ledger(mysql_core)


@pytest.mark.parametrize('first',['cancel','shipment'])
def test_cancellation_and_shipment_race(stock_case,mysql_core,monkeypatch,first):
    s=stock_case;sale=sell(s)
    actions={'cancel':lambda:request(s,'/sales/'+sale['id']+'/cancel',cancel_body(s)),
             'shipment':lambda:request(s,'/shipments',ship_body(s,sale))}
    a,b=ordered_race(monkeypatch,actions[first],actions['shipment' if first=='cancel' else 'cancel'],lock='sale')
    assert a.status_code==(200 if first=='cancel' else 201) and b.status_code==409
    assert balance(s,s['q'])==(5 if first=='cancel' else 0)
    assert_ledger(mysql_core)


@pytest.mark.parametrize('kind',['return','cancel'])
@pytest.mark.parametrize('first',['correction','recall'])
def test_correction_recall_cannot_make_stock_saleable(stock_case,mysql_core,monkeypatch,kind,first):
    s=stock_case;sale=sell(s)
    if kind=='return':ship(s,sale)
    body=return_body(s,sale) if kind=='return' else cancel_body(s)
    path='/returns' if kind=='return' else '/sales/'+sale['id']+'/cancel'
    actions={'correction':lambda:request(s,path,body),
             'recall':lambda:request(s,'/recalls',{'source_lot_id':s['lot'],'reason':'KURGUSAL düzeltme yarışı'})}
    a,b=ordered_race(monkeypatch,actions[first],actions['recall' if first=='correction' else 'correction'])
    assert a.status_code in (200,201) and b.status_code in (200,201)
    stocks=s['client'].get('/v1/stocks',params={'lot_id':s['lot']}).json()['items']
    assert all(x['blocked'] and x['available_quantity']=='0.000000' for x in stocks)
    assert_ledger(mysql_core)


def test_real_external_deadlock_rolls_back_transfer_and_retries_once(stock_case,mysql_core,monkeypatch):
    s=stock_case;location_held,lot_held=Event(),Event();real=services.lock_lots;attempts=[];errors=[]
    with Session(mysql_core) as db,db.begin():
        padding=[m.Location(name='KURGUSAL maintenance weight',kind='warehouse') for _ in range(60)]
        db.add_all(padding);db.flush();ids=[row.id for row in padding]+[s['b']]
    def lock(db,lot_ids):
        result=real(db,lot_ids);attempts.append(1);lot_held.set();return result
    monkeypatch.setattr(services,'lock_lots',lock)
    def blocker():
        with Session(mysql_core) as db,db.begin():
            rows=db.scalars(select(m.Location).where(m.Location.id.in_(ids)).order_by(m.Location.id).with_for_update()).all()
            for row in rows:row.name+=' locked'
            db.flush();location_held.set();assert lot_held.wait(5)
            db.scalar(select(m.Lot).where(m.Lot.id==s['lot']).with_for_update())
    observed=command_engine()
    def capture(context):
        if getattr(context.original_exception,'args',(None,))[0]==1213:errors.append(1213)
    event.listen(observed,'handle_error',capture)
    try:
        with ThreadPoolExecutor(2) as pool:
            f=pool.submit(blocker);assert location_held.wait(5)
            g=pool.submit(request,s,'/transfers',transfer_body(s));result=g.result(timeout=15);f.result(timeout=10)
        assert result.status_code==201 and errors and len(attempts)==2
        assert (balance(s,s['a']),balance(s,s['b']))==(13,7)
        with Session(mysql_core) as db:
            assert db.scalar(select(func.count()).select_from(m.StockTransfer))==1
            assert db.scalar(select(func.count()).select_from(m.StockMovement).where(m.StockMovement.type.in_(['transfer_in','transfer_out'])))==2
        assert_ledger(mysql_core)
    finally:event.remove(observed,'handle_error',capture)


def test_transfer_retry_exhaustion_rolls_back_every_real_write(stock_case,mysql_core,monkeypatch):
    s=stock_case;real=services.move;calls=[];before=snapshot(mysql_core)
    def deadlock_second(*args,**kwargs):
        result=real(*args,**kwargs);calls.append(result.id)
        if len(calls)%2==0:raise OperationalError('controlled1213',{},Exception(1213,'controlled test'))
        return result
    monkeypatch.setattr(services,'move',deadlock_second)
    assert post(s['client'],'/transfers',transfer_body(s),status=503)['error']['code']=='TRANSACTION_RETRY'
    assert len(calls)==6 and snapshot(mysql_core)==before


def test_multi_line_return_rolls_back_earlier_line_on_late_validation(stock_case,mysql_core):
    s=stock_case;post(s['client'],'/transfers',transfer_body(s))
    sale=post(s['client'],'/sales',{'customer_id':s['customer'],'lines':[
        {'lot_id':s['lot'],'location_id':location,'quantity':quantity,'unit':'kg','unit_price':'20'}
        for location,quantity in [(s['a'],'3'),(s['b'],'2')]]})
    ship(s,sale);body=return_body(s,sale,'1')
    # Match the service's deterministic sale-line order so a real first recovery
    # write happens before the second line fails. No API assertion is bypassed.
    ordered=sorted(sale['lines'],key=lambda line:line['id'])
    body['lines']=[{'sale_line_id':line['id'],'quantity':'1','unit':'kg'} for line in ordered]
    body['lines'][1]['unit']='package';before=snapshot(mysql_core)
    post(s['client'],'/returns',body,status=422);assert snapshot(mysql_core)==before
    body['lines'][1]['unit']='kg';returned=post(s['client'],'/returns',body)
    assert len(returned['lines'])==2 and returned['credit_amount']=='40.00' and balance(s,s['q'])==2
    assert_ledger(mysql_core)


def test_partial_shipment_prevents_whole_sale_cancel(stock_case,mysql_core):
    s=stock_case;post(s['client'],'/transfers',transfer_body(s))
    sale=post(s['client'],'/sales',{'customer_id':s['customer'],'lines':[
        {'lot_id':s['lot'],'location_id':location,'quantity':'2','unit':'kg','unit_price':'20'} for location in [s['a'],s['b']]]})
    body=ship_body(s,sale);body['lines']=body['lines'][:1];post(s['client'],'/shipments',body)
    before=snapshot(mysql_core)
    assert post(s['client'],'/sales/'+sale['id']+'/cancel',cancel_body(s),status=409)['error']['code']=='SALE_ALREADY_SHIPPED'
    assert snapshot(mysql_core)==before


@pytest.mark.parametrize('unit',['unit','package'])
def test_fractional_count_transfer_rejected(stock_case,mysql_core,unit):
    s=stock_case;body={'sku':'COUNT-'+unit,'name':'KURGUSAL adet','type':'finished','base_unit':unit}
    if unit=='package':body['package_weight_kg']='1'
    product=post(s['client'],'/products',body)
    supplier=post(s['client'],'/parties',{'name':'KURGUSAL adet tedarikçi','roles':['supplier']})
    receipt=post(s['client'],'/receipts',{'supplier_id':supplier['id'],'location_id':s['a'],'lines':[
        {'product_id':product['id'],'external_lot_code':'KURGUSAL-COUNT','quantity':'20','total_cost':'194'}]})
    body=transfer_body(s,'0.5');body.update(lot_id=receipt['lines'][0]['lot_id'],unit=unit)
    before=snapshot(mysql_core)
    assert post(s['client'],'/transfers',body,status=422)['error']['code']=='FRACTIONAL_COUNT'
    assert snapshot(mysql_core)==before


def test_new_endpoints_require_auth_and_valid_command_keys(stock_case,mysql_core):
    s=stock_case;sale=sell(s);before=snapshot(mysql_core)
    writes=[('/transfers',transfer_body(s)),('/returns',return_body(s,sale)),('/sales/'+sale['id']+'/cancel',cancel_body(s))]
    for path,body in writes:
        assert s['client'].post('/v1'+path,json=body,headers={'X-API-Key':'invalid','Idempotency-Key':str(uuid4())}).status_code==401
        assert s['client'].post('/v1'+path,json=body).status_code==422
    for path in ['/transfers','/returns','/transfers/'+str(uuid4()),'/returns/'+str(uuid4()),'/sales/'+sale['id']+'/cancellation']:
        assert s['client'].get('/v1'+path,headers={'X-API-Key':'invalid'}).status_code==401
    for path in ['/transfers/'+str(uuid4()),'/returns/'+str(uuid4()),'/sales/'+sale['id']+'/cancellation']:
        assert s['client'].get('/v1'+path).status_code==404
    assert s['client'].get('/v1/transfers?limit=0').status_code==422
    assert s['client'].get('/v1/returns?cursor=invalid').status_code==422
    assert snapshot(mysql_core)==before


def test_inconsistent_legacy_delivery_cannot_create_financial_credit(stock_case,mysql_core):
    s=stock_case;sale=sell(s);shipment=ship(s,sale)
    with Session(mysql_core) as db,db.begin():
        db.get(m.ShipmentLine,shipment['lines'][0]['id']).quantity=D('4')
    before=snapshot(mysql_core)
    assert post(s['client'],'/returns',return_body(s,sale),status=409)['error']['code']=='SOURCE_SHIPMENT_MISMATCH'
    assert snapshot(mysql_core)==before


def test_profitability_read_is_coherent_while_return_commits(stock_case,mysql_core,monkeypatch):
    s=stock_case;sale=sell(s);ship(s,sale);read_started,release=Event(),Event();real=adjustments.financial_adjustments
    def wait_before_adjustments(*args):
        if not read_started.is_set():
            read_started.set();assert release.wait(5)
        return real(*args)
    monkeypatch.setattr(adjustments,'financial_adjustments',wait_before_adjustments)
    with ThreadPoolExecutor(1) as pool:
        reader=pool.submit(s['client'].get,'/v1/sales/'+sale['id']+'/profitability')
        assert read_started.wait(5)
        try:post(s['client'],'/returns',return_body(s,sale))
        finally:release.set()
        old=reader.result(timeout=10).json()
    assert old['adjustments']['state']=='active' and old['adjustments']['return_credit_eur']=='0.00'
    assert old['adjustments']['lines'][0]['returned_quantity']=='0.000000'
    before=snapshot(mysql_core);new=s['client'].get('/v1/sales/'+sale['id']+'/profitability').json()
    assert new['adjustments']['state']=='partially_returned' and new['adjustments']['return_credit_eur']=='40.00'
    assert new['adjustments']['lines'][0]['returned_quantity']=='2.000000' and snapshot(mysql_core)==before


def test_cancellation_late_hold_failure_rolls_back_all_three_movements(stock_case,mysql_core,monkeypatch):
    s=stock_case;sale=sell(s);real=services.move;before=snapshot(mysql_core);calls=[]
    def fail_last(*args,**kwargs):
        movement=real(*args,**kwargs);calls.append(movement.id)
        if len(calls)==3:raise DomainError('CONTROLLED_CANCEL_FAILURE','KURGUSAL son karantina girişi hatası')
        return movement
    monkeypatch.setattr(services,'move',fail_last)
    assert post(s['client'],'/sales/'+sale['id']+'/cancel',cancel_body(s),status=409)['error']['code']=='CONTROLLED_CANCEL_FAILURE'
    assert len(calls)==3 and snapshot(mysql_core)==before


def test_reader_never_sees_intermediate_saleable_cancel_restoration(stock_case,mysql_core,monkeypatch):
    s=stock_case;sale=sell(s);real=services.move;restored,release=Event(),Event()
    def pause_after_reversal(*args,**kwargs):
        movement=real(*args,**kwargs)
        if movement.type=='sale_cancellation':
            restored.set();assert release.wait(5)
        return movement
    monkeypatch.setattr(services,'move',pause_after_reversal)
    with ThreadPoolExecutor(1) as pool:
        writer=pool.submit(request,s,'/sales/'+sale['id']+'/cancel',cancel_body(s))
        assert restored.wait(5)
        try:
            assert balance(s,s['a'])==15 and balance(s,s['q'])==0
        finally:release.set()
        assert writer.result(timeout=10).status_code==200
    assert balance(s,s['a'])==15 and balance(s,s['q'])==5
    assert_ledger(mysql_core)


# Reuse the real PDF production fixture: recurring six-decimal COGS must not be
# replaced with the 18.16 display EKP when returned/cancelled inventory recovers.
from test_sales_shipments_mysql import manufactured
from test_sales_shipments_mysql import sale_body as production_sale_body
from test_sales_shipments_mysql import shipment_body as production_shipment_body


def test_pdf_finished_lot_corrections_preserve_exact_cogs_and_ancestor_recall(manufactured,mysql_core):
    s=manufactured;c=s['client'];lot=s['finished_lot']
    q=post(c,'/locations',{'name':'KURGUSAL mamul geri kabul','kind':'quarantine'})['id']
    sale=post(c,'/sales',production_sale_body(s))
    post(c,'/shipments',production_shipment_body(s,sale=sale))
    before_edges=c.get('/v1/lots/'+lot+'/trace?direction=backward').json()['edges']
    def returned(quantity):
        return post(c,'/returns',{'sale_id':sale['id'],'acceptance_location_id':q,'reason':'KURGUSAL PDF mamul iadesi',
                                 'lines':[{'sale_line_id':sale['lines'][0]['id'],'quantity':quantity,'unit':'package'}]})
    first=returned('1');rest=returned('29')
    assert first['restored_cost']=='18.158824' and D(first['restored_cost'])!=D('18.16')
    assert D(first['restored_cost'])+D(rest['restored_cost'])==D(sale['lines'][0]['consumed_cost'])==D('544.764706')
    unshipped=post(c,'/sales',production_sale_body(s,'20'))
    cancelled=post(c,'/sales/'+unshipped['id']+'/cancel',{'acceptance_location_id':q,'reason':'KURGUSAL PDF iptal'},status=200)
    assert cancelled['restored_cost']==unshipped['lines'][0]['consumed_cost']=='363.176470'
    final=post(c,'/sales',production_sale_body(s,'35'))
    assert final['lines'][0]['consumed_cost']=='635.558824'
    assert counters(mysql_core,lot)==(85,D('1543.5'),85,D('1543.5'))
    assert sum(D(row['restored_cost']) for row in [first,rest,cancelled])+D(final['lines'][0]['consumed_cost'])==D('1543.5')
    assert c.get('/v1/lots/'+lot+'/trace?direction=backward').json()['edges']==before_edges
    recall=post(c,'/recalls',{'source_lot_id':s['lots'][0],'reason':'KURGUSAL kaynak ET recall'})
    held=[row for row in recall['report']['stocks'] if row['lot_id']==lot and row['location_id']==q]
    assert len(held)==1 and held[0]['quantity']=='50.000000' and held[0]['available_quantity']=='0.000000' and held[0]['blocked']
    assert_ledger(mysql_core)
