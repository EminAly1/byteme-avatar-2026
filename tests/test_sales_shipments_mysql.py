"""Sales/delivery acceptance tests; real MySQL, isolated *_test schemas only."""
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from decimal import Decimal as D
from threading import Barrier, Event
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models as m
from test_core_mysql import scenario, post, dispatch_all, close_body, assert_ledger

pytestmark = pytest.mark.skipif(os.getenv('AVATAR_CORE_MYSQL_TEST') != '1', reason='Isolated MySQL tests require AVATAR_CORE_MYSQL_TEST=1')


def customer(client, name='Market (KURGUSAL TEST)', contact='test@avatar.example.invalid'):
    return post(client, '/parties', {'name':name, 'roles':['customer'], 'contact':contact})


@pytest.fixture
def manufactured(scenario):
    s = scenario
    dispatch_all(s)
    result = post(s['client'], f"/operations/{s['operation']}/post", close_body(s), status=200)
    return {**s, 'finished_lot':result['outputs'][0]['lot_id'], 'customer':customer(s['client'])}


def sale_body(s, quantity='30', lot=None, unit='package'):
    return {'customer_id':s['customer']['id'], 'lines':[{'lot_id':lot or s['finished_lot'], 'location_id':s['warehouse'], 'quantity':quantity,'unit':unit,'unit_price':'25.00'}]}


def shipment_body(s, quantity='30', sale=None):
    body = {'customer_id':s['customer']['id'], 'lines':[{'lot_id':s['finished_lot'],'location_id':s['warehouse'],'quantity':quantity,'unit':'package'}]}
    if sale:
        body['sale_id'] = sale['id']
        body['lines'][0]['sale_line_id'] = sale['lines'][0]['id']
    return body


def count(db, model):
    return db.scalar(select(func.count()).select_from(model))


def test_normal_sale_records_price_unit_movement_and_cost(manufactured, mysql_core):
    s = manufactured
    result = post(s['client'],'/sales',sale_body(s))
    assert result['customer_id'] == s['customer']['id']
    assert result['currency'] == 'EUR' and result['sold_at'].endswith('+00:00')
    line = result['lines'][0]
    assert line['quantity'] == '30.000000' and line['unit'] == 'package'
    assert line['unit_price'] == '25.00' and line['total_amount'] == result['total_amount'] == '750.00'
    with Session(mysql_core) as db:
        movement = db.get(m.StockMovement,line['stock_movement_id'])
        assert movement.lot_id == line['lot_id'] == s['finished_lot']
        assert movement.quantity == -30 and movement.type == 'sale'
        assert db.get(m.StockBalance,(s['finished_lot'],s['warehouse'])).quantity == 55
        assert db.get(m.Lot,s['finished_lot']).consumed_cost == D(line['consumed_cost'])
    assert s['client'].get('/v1/sales/'+result['id']).json() == result
    assert_ledger(mysql_core)


def test_sale_idempotency_and_changed_payload(manufactured, mysql_core):
    s = manufactured; key = str(uuid4()); body = sale_body(s)
    first = post(s['client'],'/sales',body,key)
    assert post(s['client'],'/sales',body,key) == first
    body['lines'][0]['quantity'] = '31'
    assert post(s['client'],'/sales',body,key,409)['error']['code'] == 'IDEMPOTENCY_CONFLICT'
    with Session(mysql_core) as db:
        assert count(db,m.Sale) == count(db,m.SaleLine) == 1
        assert db.get(m.StockBalance,(s['finished_lot'],s['warehouse'])).quantity == 55
    assert_ledger(mysql_core)


def test_oversell_rejected_atomically(manufactured, mysql_core):
    s = manufactured
    assert post(s['client'],'/sales',sale_body(s,'86'),status=409)['error']['code'] == 'INSUFFICIENT_STOCK'
    with Session(mysql_core) as db:
        assert count(db,m.Sale) == count(db,m.SaleLine) == 0
        assert db.get(m.StockBalance,(s['finished_lot'],s['warehouse'])).quantity == 85
        assert db.get(m.Lot,s['finished_lot']).consumed_cost == 0
    assert_ledger(mysql_core)


@pytest.mark.parametrize('second_path',['/sales','/shipments'])
def test_concurrent_sale_or_shipment_cannot_overspend(manufactured, mysql_core, second_path):
    s = manufactured; barrier = Barrier(2)
    def call(path):
        barrier.wait(timeout=10)
        body = sale_body(s,'80') if path=='/sales' else shipment_body(s,'80')
        return s['client'].post('/v1'+path,json=body,headers={'Idempotency-Key':str(uuid4())})
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(call,['/sales',second_path]))
    assert sorted(r.status_code for r in results)==[201,409], [r.text for r in results]
    with Session(mysql_core) as db:
        assert db.get(m.StockBalance,(s['finished_lot'],s['warehouse'])).quantity == 5
        assert count(db,m.SaleLine)+count(db,m.ShipmentLine) == 1
    assert_ledger(mysql_core)


def test_concurrent_same_sale_key_posts_once(manufactured, mysql_core):
    s = manufactured; barrier=Barrier(2); key=str(uuid4())
    def call(_):
        barrier.wait(timeout=10)
        return post(s['client'],'/sales',sale_body(s),key)
    with ThreadPoolExecutor(2) as pool: results=list(pool.map(call,range(2)))
    assert results[0]==results[1]
    with Session(mysql_core) as db: assert count(db,m.SaleLine)==1
    assert_ledger(mysql_core)


@pytest.mark.parametrize('state',['blocked','expired','quarantine','external_producer'])
def test_sale_source_gate(manufactured,mysql_core,state):
    s = manufactured
    with Session(mysql_core) as db, db.begin():
        lot=db.get(m.Lot,s['finished_lot'])
        if state=='blocked':lot.blocked=True
        elif state=='expired':lot.expires_at=date.today()-timedelta(days=1)
        else:db.get(m.Location,s['warehouse']).kind=state
    result=post(s['client'],'/sales',sale_body(s),status=409)
    assert result['error']['code'] in ('LOT_BLOCKED','LOT_EXPIRED','LOCATION_NOT_SALEABLE')
    with Session(mysql_core) as db: assert count(db,m.Sale)==0
    assert_ledger(mysql_core)


def test_late_sale_failure_rolls_back_everything(scenario,mysql_core):
    s=scenario; buyer=customer(s['client']); lots=sorted(s['lots'])[:2]
    body={'customer_id':buyer['id'],'lines':[{'lot_id':lot,'location_id':s['warehouse'],'quantity':q,'unit_price':'2.00'} for lot,q in zip(lots,['1','999'])]}
    key=str(uuid4())
    post(s['client'],'/sales',body,key,409)
    with Session(mysql_core) as db:
        assert count(db,m.Sale)==count(db,m.SaleLine)==0
        assert count(db,m.StockMovement)==3
        assert db.get(m.IdempotencyRequest,('sales',key)) is None
        assert all(db.get(m.Lot,x).consumed_quantity==0 for x in lots)
    body['lines'][1]['quantity']='1'
    assert len(post(s['client'],'/sales',body,key)['lines'])==2
    assert_ledger(mysql_core)


def test_independent_shipment_single_issue_and_snapshot(manufactured,mysql_core):
    s=manufactured;key=str(uuid4());body=shipment_body(s)
    shipment=post(s['client'],'/shipments',body,key)
    assert shipment['sale_id'] is None and shipment['lines'][0]['sale_line_id'] is None
    assert post(s['client'],'/shipments',body,key)==shipment
    with Session(mysql_core) as db, db.begin():
        assert db.get(m.StockMovement,shipment['lines'][0]['stock_movement_id']).type=='shipment'
        buyer=db.get(m.Party,s['customer']['id']);buyer.name='Yeni isim';buyer.contact='changed@avatar.example.invalid'
        assert db.get(m.StockBalance,(s['finished_lot'],s['warehouse'])).quantity==55
    original=s['client'].get('/v1/shipments/'+shipment['id']).json()
    assert original['recipient_name']==s['customer']['name']
    assert original['recipient_contact']==s['customer']['contact']
    assert_ledger(mysql_core)


def test_sale_linked_shipment_reuses_movement_even_at_zero_stock(manufactured,mysql_core):
    s=manufactured
    sale=post(s['client'],'/sales',sale_body(s,'85'))
    key=str(uuid4());body=shipment_body(s,'85',sale)
    result=post(s['client'],'/shipments',body,key)
    assert post(s['client'],'/shipments',body,key)==result
    assert result['lines'][0]['stock_movement_id']==sale['lines'][0]['stock_movement_id']
    assert result['lines'][0]['consumed_cost']==sale['lines'][0]['consumed_cost']=='1543.500000'
    assert post(s['client'],'/shipments',body,status=409)['error']['code']=='SALE_LINE_ALREADY_SHIPPED'
    with Session(mysql_core) as db:
        assert db.get(m.StockBalance,(s['finished_lot'],s['warehouse'])).quantity==0
        assert db.get(m.Lot,s['finished_lot']).consumed_quantity==85
        assert count(db,m.StockMovement)==14  # 13 manufacturing + one sale; shipment creates none.
    assert_ledger(mysql_core)


@pytest.mark.parametrize('mismatch',['customer','quantity','location','lot','sale_line'])
def test_linked_shipment_exact_match_required(manufactured,mysql_core,mismatch):
    s=manufactured;sale=post(s['client'],'/sales',sale_body(s))
    body=shipment_body(s,sale=sale)
    if mismatch=='customer':body['customer_id']=customer(s['client'],'Başka market')['id']
    if mismatch=='quantity':body['lines'][0]['quantity']='29'
    if mismatch=='location':body['lines'][0]['location_id']=post(s['client'],'/locations',{'name':'Başka depo'})['id']
    if mismatch=='lot':body['lines'][0].update(lot_id=s['lots'][0],unit='kg')
    if mismatch=='sale_line':body['lines'][0]['sale_line_id']=str(uuid4())
    post(s['client'],'/shipments',body,status=404 if mismatch=='sale_line' else 422)
    with Session(mysql_core) as db:assert count(db,m.Shipment)==count(db,m.ShipmentLine)==0
    assert_ledger(mysql_core)


def test_concurrent_shipment_claim_is_unique(manufactured,mysql_core):
    s=manufactured;sale=post(s['client'],'/sales',sale_body(s));barrier=Barrier(2)
    def call(_):
        barrier.wait(timeout=10)
        return s['client'].post('/v1/shipments',json=shipment_body(s,sale=sale),headers={'Idempotency-Key':str(uuid4())})
    with ThreadPoolExecutor(2) as pool:results=list(pool.map(call,range(2)))
    assert sorted(x.status_code for x in results)==[201,409]
    with Session(mysql_core) as db:assert count(db,m.Shipment)==1 and count(db,m.StockMovement)==14
    assert_ledger(mysql_core)


def test_linked_shipment_rechecks_block_after_sale(manufactured,mysql_core):
    s=manufactured;sale=post(s['client'],'/sales',sale_body(s))
    with Session(mysql_core) as db, db.begin():db.get(m.Lot,s['finished_lot']).blocked=True
    assert post(s['client'],'/shipments',shipment_body(s,sale=sale),status=409)['error']['code']=='LOT_BLOCKED'
    with Session(mysql_core) as db:assert count(db,m.Shipment)==0 and count(db,m.StockMovement)==14
    assert_ledger(mysql_core)


def test_markets_30_25_30_and_lot_cost_balance(manufactured,mysql_core):
    s=manufactured;shipments=[]
    for name,q in [('A','30'),('B','25'),('C','30')]:
        buyer=customer(s['client'],f'Market {name} (KURGUSAL TEST)',f'market-{name}@avatar.example.invalid')
        target={**s,'customer':buyer}
        sale=post(s['client'],'/sales',sale_body(target,q))
        shipment=post(s['client'],'/shipments',shipment_body(target,q,sale))
        shipments.append(shipment)
    assert [D(x['lines'][0]['quantity']) for x in shipments]==[D('30'),D('25'),D('30')]
    assert sum(D(x['lines'][0]['quantity']) for x in shipments)==85
    post(s['client'],'/sales',sale_body(s,'1'),status=409)
    post(s['client'],'/shipments',shipment_body(s,'1'),status=409)
    with Session(mysql_core) as db:
        assert count(db,m.Sale)==count(db,m.Shipment)==3
        assert count(db,m.StockMovement)==16
        assert db.get(m.StockBalance,(s['finished_lot'],s['warehouse'])).quantity==0
        assert db.scalar(select(func.sum(m.SaleLine.consumed_cost)))==D('1543.50')
        assert db.get(m.Lot,s['finished_lot']).consumed_cost==D('1543.50')
    assert_ledger(mysql_core)


def test_multi_line_sale_can_ship_distinct_whole_lines_and_roll_back_duplicate(scenario,mysql_core):
    s=scenario;buyer=customer(s['client']);lots=sorted(s['lots'])[:2]
    sale=post(s['client'],'/sales',{'customer_id':buyer['id'],'lines':[{'lot_id':lot,'location_id':s['warehouse'],'quantity':'1','unit_price':'1.00'} for lot in lots]})
    def body(lines):
        return {'customer_id':buyer['id'],'sale_id':sale['id'],'lines':[{'sale_line_id':x['id'],'lot_id':x['lot_id'],'location_id':x['location_id'],'quantity':x['quantity']} for x in lines]}
    post(s['client'],'/shipments',body([sale['lines'][1]]))
    # First line is flushed, then the already shipped second line fails. First claim must roll back.
    post(s['client'],'/shipments',body(sale['lines']),status=409)
    with Session(mysql_core) as db:assert count(db,m.Shipment)==count(db,m.ShipmentLine)==1
    post(s['client'],'/shipments',body([sale['lines'][0]]))
    with Session(mysql_core) as db:assert count(db,m.Shipment)==count(db,m.ShipmentLine)==2 and count(db,m.StockMovement)==5
    assert_ledger(mysql_core)


def test_db_uniqueness_and_foreign_keys_protect_shipment_claim(manufactured,mysql_core):
    s=manufactured;shipment=post(s['client'],'/shipments',shipment_body(s))
    original=shipment['lines'][0]
    with pytest.raises(IntegrityError),Session(mysql_core) as db,db.begin():
        other=m.Shipment(customer_id=s['customer']['id'],recipient_name='İkinci sevkiyat',recipient_contact=None,shipped_at=m.now())
        db.add(other);db.flush()
        db.add(m.ShipmentLine(shipment_id=other.id,line_no=1,product_id=original['product_id'],lot_id=original['lot_id'],location_id=original['location_id'],stock_movement_id=original['stock_movement_id'],quantity=D('1'),unit='package',consumed_cost=D('1')))
        db.flush()
    with pytest.raises(IntegrityError),Session(mysql_core) as db,db.begin():
        db.delete(db.get(m.Party,s['customer']['id']));db.flush()
    assert_ledger(mysql_core)


def test_sale_decimal_rounding_and_list_cursor(scenario,mysql_core):
    s=scenario;buyer=customer(s['client']);results=[]
    for _ in range(3):
        results.append(post(s['client'],'/sales',{'customer_id':buyer['id'],'lines':[{'lot_id':s['lots'][0],'location_id':s['warehouse'],'quantity':'0.333333','unit_price':'0.05'}]}))
    assert all(x['total_amount']=='0.02' for x in results)
    first=s['client'].get('/v1/sales?limit=2').json()
    second=s['client'].get('/v1/sales',params={'limit':2,'cursor':first['next_cursor']}).json()
    assert len(first['items'])==2 and len(second['items'])==1
    assert all(x['total_amount']=='0.02' for x in first['items']+second['items'])
    assert not {x['id'] for x in first['items']} & {x['id'] for x in second['items']}
    assert_ledger(mysql_core)


@pytest.mark.parametrize('bad',[
    {'quantity':'-1'},{'quantity':'0'},{'quantity':1.25},{'unit_price':25.0},
    {'quantity':'0.0000001'},{'quantity':'1.5'},{'unit':'kg'},{'unit_price':'1.234'},
])
def test_invalid_sale_amounts_or_unit_rejected(manufactured,bad):
    s=manufactured;body=sale_body(s);body['lines'][0].update(bad)
    post(s['client'],'/sales',body,status=422)


def test_auth_roles_idempotency_header_and_unknown_contact(manufactured):
    s=manufactured;c=s['client']
    for path,body in [('/sales',sale_body(s)),('/shipments',shipment_body(s))]:
        assert c.get('/v1'+path,headers={'X-API-Key':'wrong'}).status_code==401
        assert c.post('/v1'+path,json=body,headers={'X-API-Key':'wrong','Idempotency-Key':str(uuid4())}).status_code==401
        assert c.post('/v1'+path,json=body).status_code==422
    body=sale_body(s);body['customer_id']=s['supplier']['id']
    post(c,'/sales',body,status=422)
    unknown=customer(c,'İletişimi bilinmiyor',None)
    result=post(c,'/shipments',{**shipment_body(s,'1'),'customer_id':unknown['id']})
    assert result['recipient_contact'] is None


def test_shipment_contract_dates_and_missing_links(manufactured,mysql_core):
    s=manufactured;body=sale_body(s);body['sold_at']='2026-10-24T12:00:00Z'
    sale=post(s['client'],'/sales',body)
    linked=shipment_body(s,sale=sale);linked['shipped_at']='2026-10-24T11:59:59Z'
    assert post(s['client'],'/shipments',linked,status=422)['error']['code']=='SHIPMENT_BEFORE_SALE'
    linked.pop('shipped_at');linked['lines'][0].pop('sale_line_id')
    post(s['client'],'/shipments',linked,status=422)
    independent=shipment_body(s);independent['lines'][0]['sale_line_id']=sale['lines'][0]['id']
    post(s['client'],'/shipments',independent,status=422)
    with Session(mysql_core) as db:assert count(db,m.Shipment)==0


def test_sale_rechecks_block_after_waiting_for_lot_lock(manufactured,mysql_core):
    from sqlalchemy import event
    from threading import current_thread
    from app.database import get_engine
    # Legacy readiness tests clear the global engine cache; observe the engine
    # actually used by requests, which may differ from the session fixture.
    api_engine=get_engine()
    s=manufactured;reached=Event()
    def before_execute(connection,cursor,statement,parameters,context,executemany):
        if current_thread().name!='MainThread' and 'FROM lots' in statement and 'FOR UPDATE' in statement:reached.set()
    with Session(mysql_core) as locker:
        lot=locker.scalar(select(m.Lot).where(m.Lot.id==s['finished_lot']).with_for_update())
        event.listen(api_engine,'before_cursor_execute',before_execute)
        try:
            with ThreadPoolExecutor(1) as pool:
                future=pool.submit(s['client'].post,'/v1/sales',json=sale_body(s),headers={'Idempotency-Key':str(uuid4())})
                try:
                    assert reached.wait(5),'Sale did not lock the lot'
                    lot.blocked=True
                finally:locker.commit()
                result=future.result(timeout=5)
                assert result.status_code==409 and result.json()['error']['code']=='LOT_BLOCKED'
        finally:event.remove(api_engine,'before_cursor_execute',before_execute)
    with Session(mysql_core) as db:
        assert count(db,m.Sale)==0
        assert db.get(m.StockBalance,(s['finished_lot'],s['warehouse'])).quantity==85
    assert_ledger(mysql_core)


def test_linked_shipment_rejects_seeded_sale_reversal(manufactured,mysql_core):
    # Seed a complete cancellation only as fixture data; no returns API is implemented.
    from app import services
    s=manufactured;sale=post(s['client'],'/sales',sale_body(s));line=sale['lines'][0]
    with Session(mysql_core) as db,db.begin():
        lot=db.scalar(select(m.Lot).where(m.Lot.id==s['finished_lot']).with_for_update())
        reverse=services.move(db,lot.id,s['warehouse'],D('30'),'reversal')
        reverse.reversal_of=line['stock_movement_id']
        lot.consumed_quantity=D('0');lot.consumed_cost=D('0')
        db.flush();reverse_id=reverse.id
    try:
        result=post(s['client'],'/shipments',shipment_body(s,sale=sale),status=409)
        assert result['error']['code']=='SALE_MOVEMENT_REVERSED'
        with Session(mysql_core) as db:assert count(db,m.Shipment)==0
        assert_ledger(mysql_core)
    finally:
        # Remove the self-referencing fixture first so next test cleanup is deterministic.
        with Session(mysql_core) as db,db.begin():db.delete(db.get(m.StockMovement,reverse_id))


def test_late_sale_total_overflow_rolls_back_stock(scenario,mysql_core):
    s=scenario;buyer=customer(s['client']);lots=sorted(s['lots'])[:2]
    body={'customer_id':buyer['id'],'lines':[{'lot_id':lot,'location_id':s['warehouse'],'quantity':'1','unit_price':'600000000000.00'} for lot in lots]}
    assert post(s['client'],'/sales',body,status=422)['error']['code']=='VALUE_OVERFLOW'
    with Session(mysql_core) as db:
        assert count(db,m.Sale)==count(db,m.SaleLine)==0 and count(db,m.StockMovement)==3
        assert all(db.get(m.Lot,x).consumed_quantity==0 for x in lots)
    assert_ledger(mysql_core)
