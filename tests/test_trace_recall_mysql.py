"""Real MySQL trace/recall acceptance, including deterministic transaction races."""
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from decimal import Decimal as D
from threading import Event, current_thread
from uuid import uuid4

import pytest
from sqlalchemy import event, select
from sqlalchemy.orm import Session

from app import models as m, recalls, services
from app.database import get_engine
from app.errors import DomainError, GraphChanged
from app.schemas import RecallCreate, SaleCreate, OperationPost
from test_core_mysql import scenario, post, dispatch_all, close_body, assert_ledger
from test_sales_shipments_mysql import manufactured, customer, sale_body, shipment_body, count

pytestmark = pytest.mark.skipif(os.getenv('AVATAR_CORE_MYSQL_TEST') != '1', reason='Dedicated *_test MySQL 8 database required')


def recall_body(s):
    return {'source_lot_id': s['lots'][0], 'reason': 'KURGUSAL TEST — kalite kontrol'}


def trace(s, lot=None, direction='forward'):
    response = s['client'].get(f"/v1/lots/{lot or s['lots'][0]}/trace", params={'direction': direction})
    assert response.status_code == 200, response.text
    return response.json()


def new_stage(s, inputs, outputs=None):
    op = post(s['client'], '/operations', {'code': 'OTHER-'+str(uuid4()), 'producer_id': s['producer']['id']})['id']
    post(s['client'], f'/operations/{op}/dispatch', {'from_location_id': s['warehouse'], 'to_location_id': s['external'],
         'lines': [{'lot_id': lot, 'quantity': q} for lot, q in inputs]}, status=200)
    body = {'consumed_inputs': [{'lot_id': lot, 'quantity': q, 'location_id': s['external']} for lot, q in inputs],
            'output_location_id': s['warehouse'], 'outputs': outputs or [{'product_id': s['output']['id'], 'lot_code': 'UNRELATED-'+str(uuid4()),
             'quantity': str(sum(D(q) for _, q in inputs))}], 'loss_quantity': '0'}
    return op, body


def test_forward_trace_uses_actual_fk_and_separates_coingredients(manufactured):
    s = manufactured; result = trace(s)
    assert {x['id'] for x in result['lots']} == {s['lots'][0], s['finished_lot']}
    assert {x['id'] for x in result['context_lots']} == set(s['lots'][1:])
    assert len(result['edges']) == 3 and not result['cycle_detected']
    assert {x['operation_id'] for x in result['edges']} == {s['operation']}
    assert result['source_lot']['supplier']['id'] == s['supplier']['id']
    meat = next(x for x in result['edges'] if x['input_lot_id'] == s['lots'][0])
    assert meat['consumed_input_quantity'] == meat['attributed_input_quantity'] == '100.000000'
    assert any(x['quantity'] == '85.000000' for x in result['stocks'])


def test_backward_trace_includes_all_ingredients_and_supplier(manufactured):
    s = manufactured; result = trace(s, s['finished_lot'], 'backward')
    assert {x['id'] for x in result['lots']} == set(s['lots']) | {s['finished_lot']}
    assert len(result['operations']) == 1
    assert {x['lot_id']: x['quantity'] for x in result['operations'][0]['inputs']} == dict(zip(s['lots'], ['100.000000','2.000000','5.000000']))
    assert {x['supplier']['id'] for x in result['lots'] if x['supplier']} == {s['supplier']['id']}


def test_multistage_arbitrary_codes_and_converging_paths(manufactured, mysql_core):
    s = manufactured
    op, body = new_stage(s, [(s['finished_lot'], '40')], [
        {'product_id': s['output']['id'], 'lot_code': 'NO-SUC-X', 'quantity': '20'},
        {'product_id': s['output']['id'], 'lot_code': 'NO-SUC-Y', 'quantity': '20'}])
    branches = post(s['client'], f'/operations/{op}/post', body, status=200)['outputs']
    op2, body2 = new_stage(s, [(x['lot_id'], '10') for x in branches])
    final = post(s['client'], f'/operations/{op2}/post', body2, status=200)['outputs'][0]['lot_id']
    expected = {s['lots'][0], s['finished_lot'], final} | {x['lot_id'] for x in branches}
    assert {x['id'] for x in trace(s)['lots']} == expected
    backward = trace(s, final, 'backward')
    assert {x['id'] for x in backward['lots']} == expected | set(s['lots'])
    result = post(s['client'], '/recalls', recall_body(s))
    assert {x['id'] for x in result['report']['lots']} == expected
    assert all(x['blocked'] for x in result['report']['lots'])
    assert_ledger(mysql_core)


def test_many_to_many_and_missing_attribution_are_conservative(scenario, mysql_core):
    s = scenario; dispatch_all(s); body = close_body(s)
    body['outputs'] = [{'product_id': s['output']['id'], 'lot_code': code, 'quantity': q} for code, q in [('OTHER-X','40'),('OTHER-Y','45')]]
    output = post(s['client'], f"/operations/{s['operation']}/post", body, status=200)['outputs']
    # Incomplete historical quantity attribution must not hide shared outputs.
    with Session(mysql_core) as db, db.begin():
        link = db.scalar(select(m.LotLink).join(m.OperationInput, m.LotLink.input_id == m.OperationInput.id).where(m.OperationInput.lot_id == s['lots'][0]))
        missing = (link.input_id, link.output_id); db.delete(link)
    forward = trace(s)
    assert {x['id'] for x in forward['lots']} == {s['lots'][0]} | {x['lot_id'] for x in output}
    assert len(forward['edges']) == 6
    edge = next(x for x in forward['edges'] if (x['input_id'], x['output_id']) == missing)
    assert edge['lot_link_id'] is edge['attributed_input_quantity'] is None
    assert edge['physical_separation_verified'] is False
    assert {x['id'] for x in trace(s, output[0]['lot_id'], 'backward')['lots']} == set(s['lots']) | {output[0]['lot_id']}


def test_cycles_and_repeated_edges_terminate_and_are_flagged(manufactured, mysql_core):
    s = manufactured
    # Adversarial historical fixture, never an API-created production cycle.
    with Session(mysql_core) as db, db.begin():
        op = m.Operation(code='CYCLE-FIXTURE', kind='rework', status='posted'); db.add(op); db.flush()
        db.add(m.OperationInput(operation_id=op.id, lot_id=s['finished_lot'], location_id=s['warehouse'], quantity=D('1'), consumed_cost=D('0')))
        db.add(m.OperationOutput(operation_id=op.id, lot_id=s['lots'][0], quantity=D('1'), allocation_weight=D('1'), allocated_cost=D('0')))
    result = trace(s)
    assert result['cycle_detected'] and len(result['lots']) == 2
    recalled = post(s['client'], '/recalls', recall_body(s))
    assert recalled['report']['cycle_detected'] and all(x['blocked'] for x in recalled['report']['lots'])


def test_repeated_customer_shipments_group_without_double_count(manufactured, mysql_core):
    s = manufactured
    for q in ['10','20']:
        sale = post(s['client'], '/sales', sale_body(s, q))
        post(s['client'], '/shipments', shipment_body(s, q, sale))
    post(s['client'], '/shipments', shipment_body(s, '5'))
    # Same human-readable name is not the same customer identity.
    second = {**s, 'customer': customer(s['client'], s['customer']['name'], None)}
    post(s['client'], '/shipments', shipment_body(second, '2'))
    with Session(mysql_core) as db, db.begin():
        db.get(m.Party, s['customer']['id']).contact = 'changed@example.invalid'
    result = trace(s); assert len(result['buyers']) == 2
    buyer = next(x for x in result['buyers'] if x['customer_id'] == s['customer']['id'])
    q = buyer['quantities'][0]
    assert q['recorded_sale_quantity'] == '30.000000' and q['shipped_quantity'] == '35.000000'
    assert q['unshipped_sale_quantity'] == '0.000000' and len(q['shipment_line_ids']) == 3
    assert len(buyer['recipient_snapshots']) == 3
    assert {x['recipient_contact'] for x in buyer['recipient_snapshots']} == {s['customer']['contact']}
    assert result['total_shipped_quantities'][0]['quantity'] == '37.000000'
    assert all(x['market_remaining_quantity'] is None for x in result['unknown_distributions'])
    assert result['second_tier_distributions'] == []
    assert_ledger(mysql_core)


def test_required_abc_recall_report_and_blocked_sale(manufactured, mysql_core):
    s = manufactured; expected = {}
    for name, q in [('A','30'),('B','25'),('C','30')]:
        target = {**s, 'customer': customer(s['client'], 'Market '+name, 'fictional-'+name+'@example.invalid')}
        sale = post(s['client'], '/sales', sale_body(target, q))
        post(s['client'], '/shipments', shipment_body(target, q, sale))
        expected[target['customer']['id']] = D(q)
    result = post(s['client'], '/recalls', recall_body(s)); r = result['report']
    assert {x['customer_id']: D(x['quantities'][0]['shipped_quantity']) for x in r['buyers']} == expected
    assert r['total_shipped_quantities'] == [{'product_id': s['output']['id'], 'unit': 'package', 'quantity': '85.000000'}]
    assert r['blocked_stocks'] == []  # All finished stock shipped; never market stock.
    assert s['client'].get('/v1/recalls/'+result['id']).json() == result
    assert post(s['client'], '/sales', sale_body(s, '1'), status=409)['error']['code'] == 'LOT_BLOCKED'
    assert post(s['client'], '/shipments', shipment_body(s, '1'), status=409)['error']['code'] == 'LOT_BLOCKED'
    with Session(mysql_core) as db:
        assert db.get(m.Lot, s['lots'][0]).blocked and db.get(m.Lot, s['finished_lot']).blocked
        assert not any(db.get(m.Lot, x).blocked for x in s['lots'][1:])
        assert count(db, m.Recall) == 1 and count(db, m.RecallLot) == 2
        assert count(db, m.StockMovement) == 16
    assert_ledger(mysql_core)


def test_idempotent_recall_and_changed_reason(manufactured, mysql_core):
    s = manufactured; key = str(uuid4()); body = recall_body(s)
    first = post(s['client'], '/recalls', body, key)
    assert post(s['client'], '/recalls', body, key) == first
    assert post(s['client'], '/recalls', {**body, 'reason': 'different'}, key, 409)['error']['code'] == 'IDEMPOTENCY_CONFLICT'
    with Session(mysql_core) as db:
        assert count(db, m.Recall) == 1 and count(db, m.RecallLot) == 2
    assert first['report']['blocked_stocks'][0]['available_quantity'] == '0.000000'


@pytest.mark.parametrize('bad,status', [({'source_lot_id': str(uuid4())},404), ({'reason': '  '},422), ({'source_lot_id':'bad'},422)])
def test_invalid_recall_leaves_no_effects(manufactured, mysql_core, bad, status):
    s = manufactured; key = str(uuid4())
    post(s['client'], '/recalls', {**recall_body(s), **bad}, key, status)
    with Session(mysql_core) as db:
        assert count(db, m.Recall) == count(db, m.RecallLot) == 0
        assert db.get(m.IdempotencyRequest, ('recalls',key)) is None
        assert not any(db.scalars(select(m.Lot.blocked)))


def test_recall_auth_header_and_read_validation(manufactured):
    s = manufactured; c = s['client']
    assert c.post('/v1/recalls', json=recall_body(s)).status_code == 422
    assert c.post('/v1/recalls', json=recall_body(s), headers={'Idempotency-Key':str(uuid4()), 'X-API-Key':'wrong'}).status_code == 401
    assert c.get(f"/v1/lots/{s['lots'][0]}/trace", headers={'X-API-Key':'wrong'}).status_code == 401
    assert c.get(f"/v1/lots/{s['lots'][0]}/trace?direction=invalid").status_code == 422
    assert c.get('/v1/lots/'+str(uuid4())+'/trace').status_code == 404
    assert c.get('/v1/recalls/'+str(uuid4())).status_code == 404


def test_late_report_failure_rolls_back_blocks_header_membership_and_key(manufactured, mysql_core, monkeypatch):
    s = manufactured; key = str(uuid4())
    def fail(*args, **kwargs):
        raise DomainError('TEST_REPORT_FAILURE', 'Simulated late report failure', 503)
    with monkeypatch.context() as patch:
        patch.setattr(recalls, 'render', fail)
        post(s['client'], '/recalls', recall_body(s), key, 503)
    with Session(mysql_core) as db:
        assert count(db, m.Recall) == count(db, m.RecallLot) == 0
        assert not any(db.scalars(select(m.Lot.blocked)))
        assert db.get(m.IdempotencyRequest, ('recalls', key)) is None
    post(s['client'], '/recalls', recall_body(s), key)
    assert_ledger(mysql_core)


def test_continuously_changing_graph_returns_retry_without_partial_commit(manufactured, mysql_core, monkeypatch):
    s = manufactured; key = str(uuid4()); original = recalls.create_recall; attempts = []
    def changed(db, body):
        attempts.append(1)
        raise GraphChanged()
    with monkeypatch.context() as patch:
        patch.setattr(recalls, 'create_recall', changed)
        assert post(s['client'], '/recalls', recall_body(s), key, 503)['error']['code'] == 'TRANSACTION_RETRY'
    assert len(attempts) == 3
    with Session(mysql_core) as db:
        assert count(db, m.Recall) == 0 and db.get(m.IdempotencyRequest, ('recalls',key)) is None
    assert recalls.create_recall is original
    post(s['client'], '/recalls', recall_body(s), key)


def test_recalled_input_blocks_dispatched_production_and_dispatch(scenario, mysql_core):
    s = scenario; dispatch_all(s)
    result = post(s['client'], '/recalls', recall_body(s))
    assert result['report']['operations'][0]['status'] == 'draft'
    assert post(s['client'], f"/operations/{s['operation']}/post", close_body(s), status=409)['error']['code'] == 'LOT_BLOCKED'
    with Session(mysql_core) as db:
        assert count(db, m.OperationOutput) == 0
        assert db.get(m.StockBalance, (s['lots'][0], s['external'])).quantity == 100
    op = post(s['client'], '/operations', {'code':'NOT-ALLOWED', 'producer_id':s['producer']['id']})['id']
    assert post(s['client'], f'/operations/{op}/dispatch', {'from_location_id':s['warehouse'], 'to_location_id':s['external'], 'lines':[{'lot_id':s['lots'][0],'quantity':'1'}]}, status=409)['error']['code'] == 'LOT_BLOCKED'
    assert_ledger(mysql_core)


def await_lot_lock(api_engine, event_flag):
    def before(connection, cursor, statement, parameters, context, executemany):
        if current_thread().name != 'MainThread' and 'FROM lots' in statement and 'FOR UPDATE' in statement:
            event_flag.set()
    event.listen(api_engine, 'before_cursor_execute', before)
    return before


@pytest.mark.parametrize('competitor', ['sale','production'])
def test_recall_wins_race_waiting_writer_rechecks_block(manufactured, mysql_core, competitor):
    s = manufactured; reached = Event(); api_engine = get_engine()
    if competitor == 'production':
        op, body = new_stage(s, [(s['finished_lot'],'10')])
        path = f'/v1/operations/{op}/post'
    else:
        path, body = '/v1/sales', sale_body(s)
    # A real uncommitted recall owns lot locks while the API writer waits.
    with Session(mysql_core) as locker:
        recalls.create_recall(locker, RecallCreate.model_validate(recall_body(s)))
        listener = await_lot_lock(api_engine, reached)
        try:
            with ThreadPoolExecutor(1) as pool:
                future = pool.submit(s['client'].post, path, json=body, headers={'Idempotency-Key':str(uuid4())})
                try:
                    assert reached.wait(5), 'Writer did not reach the locked lot'
                    with pytest.raises(TimeoutError):
                        future.result(timeout=0.15)
                finally:
                    locker.commit()
                response = future.result(timeout=5)
                assert response.status_code == 409 and response.json()['error']['code'] == 'LOT_BLOCKED'
        finally:
            event.remove(api_engine, 'before_cursor_execute', listener)
    with Session(mysql_core) as db:
        assert count(db, m.Sale) == 0 and count(db, m.OperationOutput) == 1
    assert_ledger(mysql_core)


def test_sale_wins_race_recall_reports_committed_sale_only_buyer(manufactured, mysql_core):
    from app.sales import create_sale
    s = manufactured; reached = Event(); api_engine = get_engine()
    with Session(mysql_core) as locker:
        create_sale(locker, SaleCreate.model_validate(sale_body(s)))
        listener = await_lot_lock(api_engine, reached)
        try:
            with ThreadPoolExecutor(1) as pool:
                future = pool.submit(post, s['client'], '/recalls', recall_body(s))
                try:
                    assert reached.wait(5)
                    with pytest.raises(TimeoutError):
                        future.result(timeout=0.15)
                finally:
                    locker.commit()
                result = future.result(timeout=5)['report']
        finally:
            event.remove(api_engine, 'before_cursor_execute', listener)
    assert result['buyers'][0]['quantities'][0]['unshipped_sale_quantity'] == '30.000000'
    assert result['buyers'][0]['quantities'][0]['shipped_quantity'] == '0.000000'
    assert result['total_shipped_quantities'] == []
    assert result['blocked_stocks'][0]['quantity'] == '55.000000'
    assert_ledger(mysql_core)


def test_production_wins_race_new_descendant_forces_whole_recall_retry(manufactured, mysql_core, monkeypatch):
    s = manufactured; reached = Event(); api_engine = get_engine(); attempts = []
    op, body = new_stage(s, [(s['finished_lot'],'10')])
    original = recalls.create_recall
    def observed(db, request):
        attempts.append(1)
        return original(db, request)
    monkeypatch.setattr(recalls, 'create_recall', observed)
    # Uncommitted new output is invisible to the first closure read, but its
    # production holds the old input lock. Recall must discover it after waiting.
    with Session(mysql_core) as locker:
        produced = services.post_operation(locker, op, OperationPost.model_validate(body))
        new_lot = produced['outputs'][0]['lot_id']
        listener = await_lot_lock(api_engine, reached)
        try:
            with ThreadPoolExecutor(1) as pool:
                future = pool.submit(post, s['client'], '/recalls', recall_body(s))
                try:
                    assert reached.wait(5)
                    with pytest.raises(TimeoutError):
                        future.result(timeout=0.15)
                finally:
                    locker.commit()
                result = future.result(timeout=5)
        finally:
            event.remove(api_engine, 'before_cursor_execute', listener)
    assert len(attempts) == 2, 'Closure expansion must restart the entire transaction'
    assert {x['id'] for x in result['report']['lots']} == {s['lots'][0],s['finished_lot'],new_lot}
    assert all(x['blocked'] for x in result['report']['lots'])
    with Session(mysql_core) as db:
        assert count(db, m.Recall) == 1 and count(db, m.RecallLot) == 3
        assert db.get(m.StockBalance, (new_lot,s['warehouse'])).quantity == 10
    assert_ledger(mysql_core)


def test_read_snapshot_isolation_does_not_leak_to_writers(manufactured):
    s = manufactured
    trace(s)
    with get_engine().connect() as connection:
        assert connection.get_isolation_level() == 'READ COMMITTED'
    post(s['client'], '/sales', sale_body(s,'1'))


def test_same_source_in_distinct_productions_finds_every_output(scenario, mysql_core):
    s = scenario; children = []
    for code in ['FIRST-UNRELATED-CODE','SECOND-UNRELATED-CODE']:
        op, body = new_stage(s, [(s['lots'][0],'20')], [{'product_id':s['output']['id'],'lot_code':code,'quantity':'20'}])
        children.append(post(s['client'], f'/operations/{op}/post', body, status=200)['outputs'][0]['lot_id'])
    result = post(s['client'], '/recalls', recall_body(s))['report']
    assert {x['id'] for x in result['lots']} == {s['lots'][0], *children}
    assert len(result['operations']) == 2 and len(result['blocked_stocks']) == 3
    assert_ledger(mysql_core)


def test_concurrent_same_recall_key_commits_one_record(manufactured, mysql_core):
    from threading import Barrier
    s = manufactured; barrier = Barrier(2); key = str(uuid4())
    def call(_):
        barrier.wait(timeout=5)
        return post(s['client'], '/recalls', recall_body(s), key)
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(call, range(2)))
    assert results[0] == results[1]
    with Session(mysql_core) as db:
        assert count(db,m.Recall) == 1 and count(db,m.RecallLot) == 2


def test_overlapping_recalls_use_consistent_lock_order(manufactured, mysql_core):
    from threading import Barrier
    s = manufactured; barrier = Barrier(2)
    def call(source):
        barrier.wait(timeout=5)
        return post(s['client'], '/recalls', {**recall_body(s), 'source_lot_id':source})
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(call, [s['lots'][0],s['finished_lot']]))
    assert len({x['id'] for x in results}) == 2
    with Session(mysql_core) as db:
        assert count(db,m.Recall) == 2 and count(db,m.RecallLot) == 3
        assert all(db.get(m.Lot,x).blocked for x in [s['lots'][0],s['finished_lot']])
    assert_ledger(mysql_core)
