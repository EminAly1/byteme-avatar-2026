"""Opt-in destructive tests in a dedicated *_test MySQL 8 database."""
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from decimal import Decimal as D
from threading import Barrier, Event
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app import models as m
from app.config import get_settings

pytestmark = pytest.mark.skipif(os.getenv('AVATAR_CORE_MYSQL_TEST') != '1', reason='AVATAR_CORE_MYSQL_TEST=1 and isolated *_test database required')


def post(client, path, body, key=None, status=201):
    response = client.post('/v1'+path, json=body, headers={'Idempotency-Key': key or str(uuid4())})
    assert response.status_code == status, response.text
    return response.json()


@pytest.fixture
def scenario(core_client):
    c = core_client
    supplier = post(c, '/parties', {'name': 'Tedarikçi', 'roles': ['supplier']})
    producer = post(c, '/parties', {'name': 'Dış üretici', 'roles': ['producer']})
    warehouse = post(c, '/locations', {'name': 'Merkez'})
    external = post(c, '/locations', {'name': 'Üretici deposu', 'kind': 'external_producer', 'party_id': producer['id']})
    products = [post(c, '/products', {'sku': sku, 'name': name, 'type': 'raw', 'base_unit': 'kg'}) for sku, name in [('ET','Et'),('BAH','Baharat'),('BAG','Bağırsak')]]
    output = post(c, '/products', {'sku': 'SUC', 'name': 'Narin Sucuk', 'type': 'finished', 'base_unit': 'package', 'package_weight_kg': '1'})
    quantities, costs = ['100','2','5'], ['970.00','48.00','58.00']
    receipt = post(c, '/receipts', {'supplier_id': supplier['id'], 'location_id': warehouse['id'], 'lines': [
        {'product_id': p['id'], 'external_lot_code': code, 'quantity': q, 'total_cost': cost}
        for p, code, q, cost in zip(products, ['ET-2026-001','BAH-001','BAG-001'], quantities, costs)]})
    lines_by_product = {x['product_id']: x for x in receipt['lines']}
    lots = [lines_by_product[p['id']]['lot_id'] for p in products]
    operation = post(c, '/operations', {'code': 'URT-2026-045', 'producer_id': producer['id']})
    return {'client': c, 'supplier': supplier, 'producer': producer, 'warehouse': warehouse['id'], 'external': external['id'], 'products': products, 'output': output, 'lots': lots, 'operation': operation['id'], 'quantities': quantities, 'receipt': receipt}


def dispatch_body(s, quantities=None):
    return {'from_location_id': s['warehouse'], 'to_location_id': s['external'], 'lines': [
        {'lot_id': lot, 'quantity': q} for lot, q in zip(s['lots'], quantities or s['quantities'])]}


def close_body(s):
    return {'consumed_inputs': [{'lot_id': lot, 'location_id': s['external'], 'quantity': q} for lot, q in zip(s['lots'], s['quantities'])],
            'output_location_id': s['warehouse'], 'outputs': [{'product_id': s['output']['id'], 'lot_code': 'SUC-2026-045', 'quantity': '85', 'unit': 'package'}],
            'service_costs': [{'amount': '467.50', 'currency': 'EUR', 'invoice_reference': 'HIZ-001'}], 'loss_quantity': '22', 'loss_reason': 'Kaydedilmiş üretim miktar farkı'}


def dispatch_all(s):
    return post(s['client'], f"/operations/{s['operation']}/dispatch", dispatch_body(s), status=200)


def assert_ledger(engine):
    with Session(engine) as db:
        for balance in db.scalars(select(m.StockBalance)):
            total = db.scalar(select(func.sum(m.StockMovement.quantity)).where(m.StockMovement.lot_id == balance.lot_id, m.StockMovement.location_id == balance.location_id))
            assert total == balance.quantity >= 0


def test_full_required_cost_stock_and_exact_lot_links(scenario, mysql_core):
    s = scenario
    dispatch_all(s)
    key = str(uuid4())
    result = post(s['client'], f"/operations/{s['operation']}/post", close_body(s), key, 200)
    assert result['total_material_cost'] == '1076.000000'
    assert result['total_service_cost'] == '467.500000'
    assert result['total_cost'] == '1543.500000'
    assert result['total_cost_display'] == '1543.50'
    assert result['outputs'][0]['unit_cost_display'] == '18.16'
    assert result['outputs'][0]['unit_cost'] == '18.158824'
    assert {x['input_lot_id'] for x in result['lot_links']} == set(s['lots'])
    assert {x['output_lot_id'] for x in result['lot_links']} == {result['outputs'][0]['lot_id']}
    assert post(s['client'], f"/operations/{s['operation']}/post", close_body(s), key, 200) == result
    post(s['client'], f"/operations/{s['operation']}/post", close_body(s), status=409)
    with Session(mysql_core) as db:
        assert db.scalar(select(func.count()).select_from(m.OperationOutput)) == 1
        for lot_id in s['lots']:
            assert db.get(m.StockBalance, (lot_id, s['warehouse'])).quantity == 0
            assert db.get(m.StockBalance, (lot_id, s['external'])).quantity == 0
        assert db.get(m.StockBalance, (result['outputs'][0]['lot_id'], s['warehouse'])).quantity == 85
        assert db.get(m.Lot, s['lots'][0]).external_code == 'ET-2026-001'
        assert db.get(m.Operation, s['operation']).code == 'URT-2026-045'
        assert db.get(m.Lot, result['outputs'][0]['lot_id']).external_code == 'SUC-2026-045'
    assert_ledger(mysql_core)


def test_receipt_replay_missing_timestamp_and_changed_body(core_client, mysql_core):
    c = core_client
    supplier = post(c, '/parties', {'name':'S', 'roles':['supplier']})
    location = post(c, '/locations', {'name':'L'})
    product = post(c, '/products', {'sku':'TEST', 'name':'Et', 'type':'raw', 'base_unit':'kg'})
    body = {'supplier_id':supplier['id'], 'location_id':location['id'], 'lines':[{'product_id':product['id'], 'external_lot_code':'LOT', 'quantity':'3','total_cost':'1.00'}]}
    key = str(uuid4())
    first = post(c, '/receipts', body, key)
    assert post(c, '/receipts', body, key) == first
    body['lines'][0]['quantity'] = '4'
    assert post(c, '/receipts', body, key, 409)['error']['code'] == 'IDEMPOTENCY_CONFLICT'
    with Session(mysql_core) as db:
        assert db.scalar(select(func.count()).select_from(m.Lot)) == 1
        assert db.scalar(select(func.count()).select_from(m.StockMovement)) == 1


def test_dispatch_replay_preserves_ownership_and_cost(scenario, mysql_core):
    s = scenario; key = str(uuid4())
    first = post(s['client'], f"/operations/{s['operation']}/dispatch", dispatch_body(s), key, 200)
    assert post(s['client'], f"/operations/{s['operation']}/dispatch", dispatch_body(s), key, 200) == first
    with Session(mysql_core) as db:
        assert db.scalar(select(func.count()).select_from(m.StockMovement)) == 9
        assert db.get(m.Lot, s['lots'][0]).consumed_cost == 0
    assert_ledger(mysql_core)


def test_invalid_mass_balance_rejects_without_writes(scenario, mysql_core):
    s = scenario; dispatch_all(s)
    body = close_body(s); body['loss_quantity'] = '21'
    assert post(s['client'], f"/operations/{s['operation']}/post", body, status=422)['error']['code'] == 'MASS_BALANCE'
    with Session(mysql_core) as db:
        assert db.get(m.Lot, s['lots'][0]).consumed_quantity == 0
        assert db.scalar(select(func.count()).select_from(m.OperationOutput)) == 0
    assert_ledger(mysql_core)


def test_late_return_failure_rolls_back_consumption_and_idempotency(scenario, mysql_core):
    s = scenario; dispatch_all(s)
    body = close_body(s); body['consumed_inputs'][0]['quantity'] = '90'; body['loss_quantity'] = '12'
    body['returned_inputs'] = [{'lot_id':s['lots'][0], 'from_location_id':s['external'], 'to_location_id':s['external'], 'quantity':'10'}]
    key = str(uuid4())
    assert post(s['client'], f"/operations/{s['operation']}/post", body, key, 422)['error']['code'] == 'INVALID_LOCATION'
    with Session(mysql_core) as db:
        assert db.get(m.Lot,s['lots'][0]).consumed_cost == 0
        assert db.get(m.StockBalance,(s['lots'][0],s['external'])).quantity == 100
        assert db.scalar(select(func.count()).select_from(m.OperationInput)) == 0
    body['returned_inputs'][0]['to_location_id'] = s['warehouse']
    result = post(s['client'], f"/operations/{s['operation']}/post", body, key, 200)
    assert D(result['total_material_cost']) == D('979')
    with Session(mysql_core) as db:
        assert db.get(m.StockBalance,(s['lots'][0],s['warehouse'])).quantity == 10
    assert_ledger(mysql_core)


def test_dispatch_must_be_fully_accounted(scenario):
    s = scenario; dispatch_all(s)
    body = close_body(s); body['consumed_inputs'][0]['quantity'] = '99'
    assert post(s['client'], f"/operations/{s['operation']}/post", body, status=422)['error']['code'] == 'DISPATCH_MISMATCH'


@pytest.mark.parametrize('state', ['blocked','expired'])
def test_blocked_or_expired_lot_cannot_dispatch(scenario, mysql_core, state):
    s = scenario
    with Session(mysql_core) as db, db.begin():
        lot = db.get(m.Lot,s['lots'][0])
        if state == 'blocked': lot.blocked = True
        else: lot.expires_at = date.today()-timedelta(days=1)
    assert post(s['client'], f"/operations/{s['operation']}/dispatch", dispatch_body(s), status=409)['error']['code'] in ('LOT_BLOCKED','LOT_EXPIRED')
    assert_ledger(mysql_core)


def test_concurrent_dispatches_cannot_overspend_stock(scenario, mysql_core):
    s = scenario
    second = post(s['client'], '/operations', {'code':'URT-SECOND','producer_id':s['producer']['id']})
    barrier = Barrier(2)
    def call(op):
        barrier.wait(timeout=10)
        return s['client'].post(f'/v1/operations/{op}/dispatch', json={**dispatch_body(s), 'lines':[{'lot_id':s['lots'][0],'quantity':'80'}]}, headers={'Idempotency-Key':str(uuid4())})
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(call,[s['operation'],second['id']]))
    assert sorted(x.status_code for x in results) == [200,409], [x.text for x in results]
    with Session(mysql_core) as db:
        assert db.get(m.StockBalance,(s['lots'][0],s['warehouse'])).quantity == 20
        assert db.get(m.StockBalance,(s['lots'][0],s['external'])).quantity == 80
    assert_ledger(mysql_core)


def test_concurrent_same_key_posts_once(scenario, mysql_core):
    s = scenario; dispatch_all(s); key = str(uuid4()); barrier = Barrier(2)
    def call(_):
        barrier.wait(timeout=10)
        return post(s['client'],f"/operations/{s['operation']}/post",close_body(s),key,200)
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(call,range(2)))
    assert results[0] == results[1]
    with Session(mysql_core) as db:
        assert db.scalar(select(func.count()).select_from(m.OperationOutput)) == 1
    assert_ledger(mysql_core)


def test_db_check_rejects_negative_balance(scenario, mysql_core):
    s = scenario
    with pytest.raises(DBAPIError) as error, mysql_core.begin() as connection:
        connection.execute(text('UPDATE stock_balances SET quantity=-1 WHERE lot_id=:lot'), {'lot':s['lots'][0]})
    assert error.value.orig.args[0] == 3819  # MySQL CHECK violation; PyMySQL maps it to OperationalError.
    assert_ledger(mysql_core)


def test_auth_validation_and_pagination(core_client, monkeypatch):
    c = core_client
    assert c.get('/v1/products',headers={'X-API-Key':'wrong'}).status_code == 401
    monkeypatch.delenv('AVATAR_API_KEY'); get_settings.cache_clear()
    assert c.get('/v1/products').status_code == 503
    monkeypatch.setenv('AVATAR_API_KEY','test-key-only-not-a-production-credential'); get_settings.cache_clear()
    for i in range(3):
        post(c,'/products',{'sku':f'P{i}', 'name':'P','type':'raw','base_unit':'kg'})
    first = c.get('/v1/products?limit=2').json()
    second = c.get('/v1/products', params={'limit':2,'cursor':first['next_cursor']}).json()
    assert len(first['items']) == 2 and len(second['items']) == 1
    assert not {x['id'] for x in first['items']} & {x['id'] for x in second['items']}
    assert c.get('/v1/stocks?cursor=bad').status_code == 422
    assert c.get('/v1/products?limit=101').status_code == 422
    assert c.post('/v1/products',json={'sku':'X','name':'X','type':'raw','base_unit':'kg'}).status_code == 422


@pytest.mark.parametrize('quantity',['-1','0','0.0000001',1.25])
def test_invalid_quantities_rejected(scenario, quantity):
    body = dispatch_body(scenario); body['lines'][0]['quantity'] = quantity
    post(scenario['client'],f"/operations/{scenario['operation']}/dispatch",body,status=422)


def test_multiple_outputs_preserve_cost_and_each_input_link_quantity(scenario, mysql_core):
    s = scenario; dispatch_all(s); body = close_body(s)
    body['outputs'] = [{'product_id':s['output']['id'],'lot_code':f'SUC-{i}','quantity':q} for i,q in enumerate(['30','25','30'])]
    result = post(s['client'],f"/operations/{s['operation']}/post",body,status=200)
    assert sum(D(x['allocated_cost']) for x in result['outputs']) == D('1543.50')
    assert len(result['lot_links']) == 9
    for lot_id,quantity in zip(s['lots'],s['quantities']):
        assert sum(D(x['attributed_input_quantity']) for x in result['lot_links'] if x['input_lot_id']==lot_id) == D(quantity)
    assert_ledger(mysql_core)


def test_partial_lot_across_operations_preserves_actual_cost(core_client, mysql_core):
    c = core_client
    supplier = post(c,'/parties',{'name':'T','roles':['supplier']})
    producer = post(c,'/parties',{'name':'U','roles':['producer']})
    warehouse = post(c,'/locations',{'name':'D'})['id']
    external = post(c,'/locations',{'name':'E','kind':'external_producer','party_id':producer['id']})['id']
    raw = post(c,'/products',{'sku':'R','name':'R','type':'raw','base_unit':'kg'})
    product = post(c,'/products',{'sku':'F','name':'F','type':'finished','base_unit':'kg'})
    receipt = post(c,'/receipts',{'supplier_id':supplier['id'],'location_id':warehouse,'lines':[{'product_id':raw['id'],'external_lot_code':'PARTIAL','quantity':'3','total_cost':'1.00'}]})
    lot = receipt['lines'][0]['lot_id']; costs = []
    for i in range(3):
        operation = post(c,'/operations',{'code':f'PARTIAL-{i}','producer_id':producer['id']})['id']
        post(c,f'/operations/{operation}/dispatch',{'from_location_id':warehouse,'to_location_id':external,'lines':[{'lot_id':lot,'quantity':'1'}]},status=200)
        result = post(c,f'/operations/{operation}/post',{'consumed_inputs':[{'lot_id':lot,'location_id':external,'quantity':'1'}],'outputs':[{'product_id':product['id'],'lot_code':f'F-{i}','quantity':'1'}],'output_location_id':warehouse,'loss_quantity':'0'},status=200)
        costs.append(D(result['total_cost']))
    assert costs == [D('0.333333'),D('0.333334'),D('0.333333')]
    assert sum(costs) == D('1')
    with Session(mysql_core) as db:
        assert db.get(m.Lot,lot).consumed_cost == D('1')
    assert_ledger(mysql_core)


def test_lot_select_for_update_blocks_a_concurrent_dispatch(scenario, mysql_core):
    from concurrent.futures import TimeoutError
    from sqlalchemy import event
    from threading import current_thread
    s = scenario; reached_lock = Event()
    def before_execute(connection, cursor, statement, parameters, context, executemany):
        if current_thread().name != 'MainThread' and 'FROM lots' in statement and 'FOR UPDATE' in statement:
            reached_lock.set()
    with Session(mysql_core) as locker:
        locker.begin()
        locker.scalar(select(m.Lot).where(m.Lot.id==s['lots'][0]).with_for_update())
        event.listen(mysql_core,'before_cursor_execute',before_execute)
        try:
            with ThreadPoolExecutor(1) as pool:
                future = pool.submit(dispatch_all,s)
                try:
                    assert reached_lock.wait(5), 'Dispatch did not execute a lot SELECT FOR UPDATE'
                    with pytest.raises(TimeoutError):
                        future.result(timeout=0.15)
                finally:
                    locker.rollback()
                assert future.result(timeout=5)['operation_id'] == s['operation']
        finally:
            event.remove(mysql_core,'before_cursor_execute',before_execute)
    assert_ledger(mysql_core)


def test_closure_sees_dispatch_committed_while_waiting_for_operation_lock(scenario, mysql_core):
    from sqlalchemy import event
    from threading import current_thread
    from app.schemas import DispatchCreate
    from app.services import dispatch
    s = scenario; reached_operation_lock = Event()
    def before_execute(connection, cursor, statement, parameters, context, executemany):
        if current_thread().name != 'MainThread' and 'FROM operations' in statement and 'FOR UPDATE' in statement:
            reached_operation_lock.set()
    # This dispatch is not committed when the closing command starts its
    # idempotency lookup. A stale REPEATABLE READ snapshot would miss it later.
    with Session(mysql_core) as locker:
        dispatch(locker,s['operation'],DispatchCreate.model_validate(dispatch_body(s)))
        event.listen(mysql_core,'before_cursor_execute',before_execute)
        try:
            with ThreadPoolExecutor(1) as pool:
                future = pool.submit(post,s['client'],f"/operations/{s['operation']}/post",close_body(s),None,200)
                try:
                    assert reached_operation_lock.wait(5)
                finally:
                    locker.commit()
                assert future.result(timeout=5)['total_cost_display'] == '1543.50'
        finally:
            event.remove(mysql_core,'before_cursor_execute',before_execute)
    assert_ledger(mysql_core)
