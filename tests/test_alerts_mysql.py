"""Current alerts over real isolated MySQL, controlled clock and ledger hashes."""
import copy
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
import json
import os
from uuid import uuid4

import pytest
from sqlalchemy import event, insert, select, text
from sqlalchemy.orm import Session

from app import alerts, models as m
from app.config import get_settings
from app.database import get_engine
from test_core_mysql import scenario, post, dispatch_all, close_body
from test_cuttings_mysql import lamb, draft, close
from test_predictions_mysql import production_body, cutting_body
from test_transfers_returns_mysql import snapshot

pytestmark = pytest.mark.skipif(os.getenv('AVATAR_CORE_MYSQL_TEST') != '1', reason='Isolated *_test MySQL required')
NOW = datetime(2026, 10, 28, 12, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def policy_clock(monkeypatch):
    monkeypatch.setattr(alerts, 'clock', lambda: NOW)
    monkeypatch.setenv('AVATAR_ALERT_STOCK_THRESHOLDS', '{}')
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def stock_case(core_client):
    c = core_client
    supplier = post(c, '/parties', {'name': 'KURGUSAL uyarı tedarikçisi', 'roles': ['supplier']})
    w = post(c, '/locations', {'name': 'KURGUSAL uyarı deposu'})['id']
    q = post(c, '/locations', {'name': 'KURGUSAL karantina', 'kind': 'quarantine'})['id']
    product = post(c, '/products', {'sku': 'ALERT-KG', 'name': 'KURGUSAL kg ürün', 'type': 'raw', 'base_unit': 'kg'})
    return {'c': c, 'supplier': supplier['id'], 'w': w, 'q': q, 'product': product}


def receive(s, expiry=None, quantity='10', product=None, location=None):
    return post(s['c'], '/receipts', {'supplier_id': s['supplier'], 'location_id': location or s['w'], 'lines': [
        {'product_id': (product or s['product'])['id'], 'external_lot_code': 'KURGUSAL-ALERT-' + str(uuid4()),
         'quantity': quantity, 'total_cost': '100', **({'expires_at': expiry.isoformat()} if expiry else {})}]})['lines'][0]['lot_id']


def listed(c, **params):
    response = c.get('/v1/alerts', params=params)
    assert response.status_code == 200, response.text
    return response.json()


def configure(monkeypatch, products):
    monkeypatch.setenv('AVATAR_ALERT_STOCK_THRESHOLDS', json.dumps(products))
    get_settings.cache_clear()


@pytest.mark.parametrize('days,rule,severity', [(-1, 'EXPIRY_PAST', 'critical'), (0, 'EXPIRY_SOON', 'warning'),
    (7, 'EXPIRY_SOON', 'warning'), (8, None, None), (None, None, None)])
def test_expiry_boundary_true_physical_stock_and_no_mutation(stock_case, mysql_core, days, rule, severity):
    s = stock_case
    lot = receive(s, NOW.date() + timedelta(days=days) if days is not None else None)
    before = snapshot(mysql_core)
    first = listed(s['c'], lot_id=lot)
    assert snapshot(mysql_core) == before
    assert first['summary']['total'] == int(rule is not None)
    if rule:
        row = first['items'][0]
        assert row['rule_code'] == rule and row['severity'] == severity and row['source_id'] == lot
        assert row['evidence']['days_remaining'] == days and row['evidence']['physical_quantity'] == '10.000000'
        assert row['evidence']['available_quantity'] == ('0.000000' if days < 0 else '10.000000')
        assert row['related_links'][0]['href'].endswith(lot)
        assert s['c'].get('/v1/alerts/' + row['id']).json() == row
        assert first == listed(s['c'], lot_id=lot)


def test_istanbul_midnight_and_zero_physical_stock(stock_case, mysql_core, monkeypatch):
    s = stock_case
    lot = receive(s, datetime(2026, 10, 27).date())
    monkeypatch.setattr(alerts, 'clock', lambda: datetime(2026, 10, 27, 21, 1, tzinfo=timezone.utc))
    row = listed(s['c'], lot_id=lot)['items'][0]
    assert row['rule_code'] == 'EXPIRY_PAST' and row['evaluated_at'].startswith('2026-10-28T00:01')
    # Only a synthetic fixture adjustment: keep the ledger consistent at zero.
    with Session(mysql_core) as db, db.begin():
        db.get(m.StockBalance, (lot, s['w'])).quantity = 0
        db.add(m.StockMovement(lot_id=lot, location_id=s['w'], quantity=-10, type='test_issue'))
    assert listed(s['c'], lot_id=lot)['items'] == []


def test_blocked_quarantine_and_exact_recall_fk_never_available(stock_case, mysql_core, monkeypatch):
    s = stock_case
    lot = receive(s)
    post(s['c'], '/transfers', {'lot_id': lot, 'from_location_id': s['w'], 'to_location_id': s['q'], 'quantity': '4', 'unit': 'kg', 'reason': 'KURGUSAL kalite'})
    recall = post(s['c'], '/recalls', {'source_lot_id': lot, 'reason': 'KURGUSAL geri çağırma'})
    configure(monkeypatch, {s['product']['id']: {'quantity': '3', 'unit': 'kg', 'origin': 'demo'}})
    before = snapshot(mysql_core); result = listed(s['c'])
    rows = [row for row in result['items'] if row['rule_code'] == 'LOT_BLOCKED_STOCK']
    assert len(rows) == 2 and {row['evidence']['location_kind'] for row in rows} == {'warehouse', 'quarantine'}
    assert all(row['evidence']['available_quantity'] == '0.000000' for row in rows)
    assert all(row['evidence']['related_recalls'] == [{'recall_id': recall['id'], 'source_lot_id': lot}] for row in rows)
    low = next(row for row in result['items'] if row['rule_code'] == 'LOW_AVAILABLE_STOCK')
    assert low['observed_value'] == '0.000000' and low['threshold_origin'] == 'demo'
    assert snapshot(mysql_core) == before


@pytest.mark.parametrize('threshold,expected', [('9', False), ('10', False), ('10.000001', True)])
def test_low_stock_explicit_strict_boundary(stock_case, monkeypatch, threshold, expected):
    s = stock_case; receive(s)
    configure(monkeypatch, {s['product']['id']: {'quantity': threshold, 'unit': 'kg'}})
    rows = listed(s['c'], rule_code='LOW_AVAILABLE_STOCK')['items']
    assert bool(rows) == expected
    if expected:
        assert rows[0]['observed_value'] == '10.000000' and rows[0]['threshold_value'] == '10.000001'


def test_no_threshold_and_unit_mismatch_never_invents_low_stock(stock_case, monkeypatch):
    s = stock_case; receive(s)
    assert listed(s['c'])['items'] == []
    configure(monkeypatch, {s['product']['id']: {'quantity': '20', 'unit': 'package'}})
    result = listed(s['c']); assert result['items'] == [] and result['diagnostics']['threshold_unit_mismatch'] == 1


def test_kg_package_unit_are_separate_and_quarantine_expired_excluded(stock_case, monkeypatch):
    s = stock_case
    for unit in ['kg', 'package', 'unit']:
        product = s['product'] if unit == 'kg' else post(s['c'], '/products', {'sku': 'ALERT-' + unit, 'name': 'KURGUSAL ' + unit,
            'type': 'finished', 'base_unit': unit, **({'package_weight_kg': '1'} if unit == 'package' else {})})
        receive(s, quantity='2', product=product)
        receive(s, quantity='100', product=product, location=s['q'])
        receive(s, quantity='100', product=product, expiry=NOW.date() - timedelta(days=1))
        existing = json.loads(os.environ['AVATAR_ALERT_STOCK_THRESHOLDS'])
        existing[product['id']] = {'quantity': '3', 'unit': unit}
        configure(monkeypatch, existing)
    rows = listed(s['c'], rule_code='LOW_AVAILABLE_STOCK')['items']
    assert len(rows) == 3 and {row['unit'] for row in rows} == {'kg', 'package', 'unit'}
    assert all(row['observed_value'] == '2.000000' for row in rows)


def closed_production(s, quantity='40', forecast=True):
    prediction = post(s['client'], '/predictions/production', production_body(s)) if forecast else None
    dispatch_all(s); body = close_body(s)
    body['outputs'][0]['quantity'] = quantity; body['loss_quantity'] = str(107 - int(quantity))
    result = post(s['client'], '/operations/' + s['operation'] + '/post', body, status=200)
    return prediction, result


def test_recorded_prestart_posted_comparison_exact_decimal_and_no_inference(scenario, mysql_core, monkeypatch):
    s = scenario; prediction, closed = closed_production(s)
    monkeypatch.setattr('app.ml_runtime.PortableModel.predict', lambda *_: (_ for _ in ()).throw(AssertionError('No new inference')))
    before = snapshot(mysql_core); result = listed(s['client'], operation_id=s['operation'])
    assert result['summary']['total'] == 2 and snapshot(mysql_core) == before
    cost = next(row for row in result['items'] if row['rule_code'] == 'PRODUCTION_EKP_DEVIATION')
    assert cost['observed_value'] == '38.587500' and cost['evidence']['prediction_id'] == prediction['id']
    actual = D(closed['total_cost']) / 40; predicted = D(prediction['predicted_ekp_eur_per_unit'])
    assert abs(D(cost['deviation_percent']) - abs(actual - predicted) / actual * 100) <= D('.000001')
    assert cost['evidence']['data_origin'] == 'SYNTHETIC' and cost['evidence']['prediction_limitations']
    assert cost['evidence']['explained_difference_kg'] == '67.000000' and cost['evidence']['new_prediction_created'] is False
    assert 'anomaly' not in cost.get('classifier', '')


@pytest.mark.parametrize('state', ['no_forecast', 'draft', 'unlinked', 'late', 'wrong_unit', 'missing_model', 'corrupt_model', 'wrong_version', 'bad_numeric'])
def test_no_or_invalid_comparable_evidence_never_fabricates_warning(scenario, mysql_core, monkeypatch, tmp_path, state):
    s = scenario
    if state == 'no_forecast':
        closed_production(s, forecast=False)
    elif state == 'draft':
        post(s['client'], '/predictions/production', production_body(s))
    else:
        prediction, _ = closed_production(s)
        if state in ('missing_model', 'corrupt_model'):
            if state == 'corrupt_model':
                (tmp_path / 'production.json').write_text('{}'); (tmp_path / 'production.sha256').write_text('0' * 64)
            monkeypatch.setenv('AVATAR_ML_MODEL_DIR', str(tmp_path)); get_settings.cache_clear()
        else:
            with Session(mysql_core) as db, db.begin():
                row = db.get(m.PredictionRecord, prediction['id'])
                if state == 'unlinked': row.operation_id = None
                elif state == 'late': row.created_at = db.get(m.Operation, s['operation']).posted_at + timedelta(seconds=1)
                else:
                    value = copy.deepcopy(row.prediction)
                    if state == 'wrong_unit': value['quantity_unit'] = 'kg'
                    elif state == 'wrong_version': value['model_version'] = 'other'
                    else: value['predicted_yield_ratio'] = 'NaN'
                    row.prediction = value
    assert listed(s['client'], operation_id=s['operation'])['items'] == []


def test_latest_eligible_prediction_selected_not_cherry_picked(scenario, mysql_core):
    s = scenario
    first = post(s['client'], '/predictions/production', production_body(s))
    second = post(s['client'], '/predictions/production', production_body(s))
    dispatch_all(s); body = close_body(s); body['outputs'][0]['quantity'] = '40'; body['loss_quantity'] = '67'
    post(s['client'], '/operations/' + s['operation'] + '/post', body, status=200)
    result = listed(s['client'], operation_id=s['operation'])
    assert result['diagnostics']['inspected_predictions'] == 1
    assert all(row['evidence']['prediction_id'] == second['id'] for row in result['items'])
    assert first['id'] != second['id']


def test_explained_25_to_22_plus_3_cutting_is_not_automatic_waste_alarm(lamb, mysql_core):
    s = lamb; recipe, op = draft(s)
    forecast = post(s['client'], '/predictions/cutting', cutting_body(s, recipe, op))
    close(s, op)
    before = snapshot(mysql_core); result = listed(s['client'], operation_id=op['id'])
    assert result['items'] == [] and result['diagnostics']['inspected_predictions'] == 1
    assert snapshot(mysql_core) == before
    assert (s['client'].get('/v1/predictions/' + forecast['id']).json()['comparison']['predicted_difference_kg']['actual']) == '3.000000'


def test_api_auth_empty_filters_limits_stable_ids_and_cursor_policy(stock_case, mysql_core, monkeypatch):
    s = stock_case
    assert s['c'].get('/v1/alerts', headers={'X-API-Key': 'wrong'}).status_code == 401
    assert s['c'].get('/v1/alerts/summary', headers={'X-API-Key': 'wrong'}).status_code == 401
    assert listed(s['c'])['summary']['total'] == 0
    for params in [{'limit': 0}, {'limit': 101}, {'severity': 'danger'}, {'rule_code': 'FAKE'}, {'cursor': 'malformed'}]:
        assert s['c'].get('/v1/alerts', params=params).status_code == 422
    for _ in range(3): receive(s, expiry=NOW.date() + timedelta(days=2))
    before = snapshot(mysql_core); first = listed(s['c'], limit=1)
    second = listed(s['c'], limit=1, cursor=first['next_cursor'])
    assert first['items'][0]['id'] != second['items'][0]['id'] and first['summary']['total'] == 3
    assert listed(s['c'], severity='critical')['items'] == []
    assert s['c'].get('/v1/alerts/' + str(uuid4())).status_code == 404
    assert s['c'].get('/v1/alerts/summary').json()['summary'] == first['summary']
    assert snapshot(mysql_core) == before
    monkeypatch.setenv('AVATAR_ALERT_EXPIRY_DAYS', '6'); get_settings.cache_clear()
    assert s['c'].get('/v1/alerts', params={'cursor': first['next_cursor']}).status_code == 409
    changed = listed(s['c'], limit=1); assert first['items'][0]['id'] != changed['items'][0]['id']


def test_db_read_only_transaction_rejects_accidental_write_and_pool_remains_writable(stock_case, mysql_core, monkeypatch):
    s = stock_case; before = snapshot(mysql_core)
    def attempted(db, *_args, **_kwargs):
        db.add(m.Location(name='must not persist', kind='warehouse')); db.flush()
        yield None
    monkeypatch.setattr(alerts, 'alert_stream', attempted)
    errors = []
    def capture(context):
        errors.append(getattr(context.original_exception, 'args', (None,))[0])
    observed = get_engine(); event.listen(observed, 'handle_error', capture)
    try:
        assert s['c'].get('/v1/alerts').status_code == 503
    finally:
        event.remove(observed, 'handle_error', capture)
    assert errors == [1792]  # Actual MySQL read-only transaction rejection.
    assert snapshot(mysql_core) == before
    # SET TRANSACTION READ ONLY must not leak into pooled application writes.
    post(s['c'], '/locations', {'name': 'KURGUSAL sonraki normal yazıcı'})


def test_1001_real_stock_rows_are_batched_and_only_requested_page_returned(stock_case, mysql_core):
    s = stock_case
    ids = [str(uuid4()) for _ in range(1001)]
    with mysql_core.begin() as c:
        c.execute(insert(m.Lot), [{'id': identifier, 'created_at': m.now(), 'received_at': m.now(),
            'product_id': s['product']['id'], 'external_code': 'KURGUSAL-BATCH', 'original_quantity': 1,
            'total_cost': 1, 'consumed_quantity': 0, 'consumed_cost': 0, 'blocked': True} for identifier in ids])
        c.execute(insert(m.StockBalance), [{'lot_id': identifier, 'location_id': s['w'], 'quantity': 1} for identifier in ids])
        c.execute(insert(m.StockMovement), [{'id': str(uuid4()), 'created_at': m.now(), 'lot_id': identifier,
            'location_id': s['w'], 'quantity': 1, 'type': 'test_seed'} for identifier in ids])
    observed = get_engine(); statements = []
    def capture(conn, cursor, statement, parameters, context, executemany): statements.append(statement)
    event.listen(observed, 'before_cursor_execute', capture)
    try: result = listed(s['c'], limit=10)
    finally: event.remove(observed, 'before_cursor_execute', capture)
    assert len(result['items']) == 10 and result['summary']['total'] == 1001 and result['next_cursor']
    assert len(statements) <= 16
    assert all(statement.lstrip().split()[0].upper() in ('SELECT', 'SET') for statement in statements)
    assert not any('FOR UPDATE' in statement for statement in statements)
    after = listed(s['c'], limit=10, cursor=result['next_cursor'])
    assert not {row['id'] for row in result['items']} & {row['id'] for row in after['items']}


def test_normal_recorded_production_below_review_threshold_is_quiet(scenario):
    s = scenario; closed_production(s, quantity='85')
    result = listed(s['client'], operation_id=s['operation'])
    assert result['items'] == [] and result['diagnostics']['inspected_predictions'] == 1
