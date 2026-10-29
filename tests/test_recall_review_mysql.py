"""Task21: read-only review and stale-impact rejection on real InnoDB locks."""
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from threading import Event
from uuid import uuid4

import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session

from app import models as m, recalls, services
from app.commands import execute
from app.schemas import RecallCreate, OperationPost
from test_core_mysql import scenario, post, assert_ledger
from test_sales_shipments_mysql import manufactured, sale_body, count
from test_trace_recall_mysql import new_stage, await_lot_lock, recall_body
from test_second_tier_mysql import delivered, create as distribute
from test_transfers_returns_mysql import snapshot, concurrent

pytestmark = pytest.mark.skipif(os.getenv('AVATAR_CORE_MYSQL_TEST') != '1', reason='Dedicated *_test MySQL 8 database required')


def preview(c, lot):
    response = c.get('/v1/recalls/preview', params={'source_lot_id': lot})
    assert response.status_code == 200, response.text
    return response.json()


def reviewed(s):
    p = preview(s['client'], s['lots'][0])
    return {**recall_body(s), 'preview_fingerprint': p['preview_fingerprint'],
            'confirmation_lot_code': p['report']['source_lot']['external_code']}


def assert_no_recall(engine, key=None):
    with Session(engine) as db:
        assert count(db, m.Recall) == count(db, m.RecallLot) == 0
        assert not any(lot.blocked for lot in db.query(m.Lot))
        if key:
            assert db.get(m.IdempotencyRequest, ('recalls', key)) is None
    assert_ledger(engine)


def test_preview_is_stable_and_changes_no_table(manufactured, mysql_core):
    s = manufactured; before = snapshot(mysql_core)
    p = preview(s['client'], s['lots'][0])
    assert p == preview(s['client'], s['lots'][0])
    assert snapshot(mysql_core) == before
    assert {x['id'] for x in p['report']['lots']} == {s['lots'][0], s['finished_lot']}
    assert not any(x['blocked'] for x in p['report']['lots'])


@pytest.mark.parametrize('reason', [None, '', '   '])
def test_missing_reason_rejected_without_effects(manufactured, mysql_core, reason):
    s = manufactured; body = reviewed(s)
    if reason is None:
        body.pop('reason')
    else:
        body['reason'] = reason
    before = snapshot(mysql_core)
    post(s['client'], '/recalls', body, status=422)
    assert snapshot(mysql_core) == before


@pytest.mark.parametrize('field', ['preview_fingerprint', 'confirmation_lot_code'])
def test_review_fields_must_arrive_together(manufactured, mysql_core, field):
    s = manufactured; body = reviewed(s); body.pop(field)
    before = snapshot(mysql_core)
    post(s['client'], '/recalls', body, status=422)
    assert snapshot(mysql_core) == before


def test_wrong_source_code_or_switched_source_never_blocks(manufactured, mysql_core):
    s = manufactured; body = reviewed(s)
    for changed in [dict(confirmation_lot_code='WRONG-LOT'), dict(source_lot_id=s['finished_lot'])]:
        key = str(uuid4()); before = snapshot(mysql_core)
        result = post(s['client'], '/recalls', {**body, **changed}, key, 409)
        assert result['error']['code'] == 'RECALL_SOURCE_MISMATCH'
        assert snapshot(mysql_core) == before
        assert_no_recall(mysql_core, key)


def test_changed_stock_requires_fresh_review_same_uncommitted_key_can_be_used(manufactured, mysql_core):
    s = manufactured; body = reviewed(s); key = str(uuid4())
    post(s['client'], '/sales', sale_body(s, '1'))
    before = snapshot(mysql_core)
    assert post(s['client'], '/recalls', body, key, 409)['error']['code'] == 'RECALL_PREVIEW_STALE'
    assert snapshot(mysql_core) == before
    assert_no_recall(mysql_core, key)
    result = post(s['client'], '/recalls', reviewed(s), key)
    assert all(x['blocked'] for x in result['report']['lots'])
    assert post(s['client'], '/sales', sale_body(s, '1'), status=409)['error']['code'] == 'LOT_BLOCKED'
    assert_ledger(mysql_core)


def test_reviewed_replay_survives_changed_block_state_and_concurrent_same_key(manufactured, mysql_core):
    s = manufactured; body = reviewed(s); key = str(uuid4())
    def call():
        return s['client'].post('/v1/recalls', json=body, headers={'Idempotency-Key': key})
    responses = concurrent([call, call])
    assert [r.status_code for r in responses] == [201, 201]
    result = responses[0].json(); assert responses[1].json() == result
    before = snapshot(mysql_core)
    assert call().json() == result and snapshot(mysql_core) == before
    assert post(s['client'], '/recalls', {**body, 'reason': 'Başka neden'}, key, 409)['error']['code'] == 'IDEMPOTENCY_CONFLICT'
    with Session(mysql_core) as db:
        assert count(db, m.Recall) == 1 and count(db, m.RecallLot) == 2
        assert not any(db.get(m.Lot, x).blocked for x in s['lots'][1:])
    assert_ledger(mysql_core)


def test_existing_legacy_hash_and_response_still_replay(manufactured, mysql_core):
    s = manufactured; key = str(uuid4()); body = recall_body(s)
    old, code = execute('recalls', key, RecallCreate.model_validate(body), recalls.create_recall)
    before = snapshot(mysql_core)
    assert code == 201 and post(s['client'], '/recalls', body, key) == old
    assert post(s['client'], '/recalls', {**body, 'preview_fingerprint': None, 'confirmation_lot_code': None}, key) == old
    assert snapshot(mysql_core) == before


def test_reviewed_atomic_failure_rolls_back_every_block_and_key(manufactured, mysql_core, monkeypatch):
    s = manufactured; body = reviewed(s); key = str(uuid4()); before = snapshot(mysql_core)
    from app.errors import DomainError
    def fail(*_):
        raise DomainError('INJECTED_FAILURE', 'KURGUSAL atomiklik testi', 503)
    with monkeypatch.context() as patch:
        patch.setattr(recalls, 'render', fail)
        post(s['client'], '/recalls', body, key, 503)
    assert snapshot(mysql_core) == before
    assert_no_recall(mysql_core, key)
    post(s['client'], '/recalls', body, key)
    assert_ledger(mysql_core)


def test_concurrent_overlapping_review_rejects_changed_blocks_without_partial_state(manufactured, mysql_core):
    s = manufactured; body = reviewed(s)
    def call():
        return s['client'].post('/v1/recalls', json=body, headers={'Idempotency-Key': str(uuid4())})
    responses = concurrent([call, call])
    assert sorted(r.status_code for r in responses) == [201, 409]
    assert next(r for r in responses if r.status_code == 409).json()['error']['code'] == 'RECALL_PREVIEW_STALE'
    with Session(mysql_core) as db:
        assert count(db, m.Recall) == 1 and count(db, m.RecallLot) == 2
        assert db.get(m.Lot, s['lots'][0]).blocked and db.get(m.Lot, s['finished_lot']).blocked
    assert_ledger(mysql_core)


def test_production_winner_expands_graph_then_review_rejects_without_partial_blocks(manufactured, mysql_core, monkeypatch):
    s = manufactured; op, close = new_stage(s, [(s['finished_lot'], '10')])
    body = reviewed(s); key = str(uuid4()); reached = Event(); attempts = []
    original = recalls.create_recall
    def observed(db, request):
        attempts.append(1)
        return original(db, request)
    monkeypatch.setattr(recalls, 'create_recall', observed)
    with Session(mysql_core) as locker:
        services.post_operation(locker, op, OperationPost.model_validate(close))
        listener = await_lot_lock(mysql_core, reached)
        try:
            with ThreadPoolExecutor(1) as pool:
                future = pool.submit(s['client'].post, '/v1/recalls', json=body, headers={'Idempotency-Key': key})
                try:
                    assert reached.wait(5)
                    with pytest.raises(TimeoutError):
                        future.result(timeout=0.15)
                finally:
                    locker.commit()
                response = future.result(timeout=5)
                assert response.status_code == 409 and response.json()['error']['code'] == 'RECALL_PREVIEW_STALE'
        finally:
            event.remove(mysql_core, 'before_cursor_execute', listener)
    assert len(attempts) == 2
    assert_no_recall(mysql_core, key)
    result = post(s['client'], '/recalls', reviewed(s), key)
    assert len(result['report']['lots']) == 3 and all(x['blocked'] for x in result['report']['lots'])
    assert_ledger(mysql_core)


def test_second_tier_is_recorded_evidence_and_changes_review_not_physical_stock(delivered, mysql_core):
    s = delivered; p = preview(s['c'], s['lot']); distribute(s)
    before = snapshot(mysql_core); updated = preview(s['c'], s['lot'])
    assert snapshot(mysql_core) == before and p['preview_fingerprint'] != updated['preview_fingerprint']
    r = updated['report']; assert r['second_tier_distributions'][0]['recipient_party_id'] == s['x']
    assert r['unknown_distributions'][0]['market_remaining_quantity'] is None
    assert r['second_tier_distributions'][0]['recipient_physical_stock_quantity'] is None
    assert r['total_shipped_quantities'][0]['quantity'] == '30.000000'
    assert post(s['c'], '/recalls', {'source_lot_id':s['lot'], 'reason':'KURGUSAL',
                'preview_fingerprint':p['preview_fingerprint'], 'confirmation_lot_code':r['source_lot']['external_code']}, status=409)['error']['code'] == 'RECALL_PREVIEW_STALE'
    assert snapshot(mysql_core) == before
