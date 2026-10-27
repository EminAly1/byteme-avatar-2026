"""EK-05: actual MySQL sources, real parsed PDF bytes and read-only ledger proof."""
from io import BytesIO
import os
from uuid import uuid4

from pypdf import PdfReader
import pytest
from sqlalchemy import event, insert

from app import document_drafts, models as m
from test_core_mysql import post
from test_transfers_returns_mysql import snapshot

pytestmark = pytest.mark.skipif(os.getenv('AVATAR_CORE_MYSQL_TEST') != '1', reason='Separate *_test MySQL required')
BASE = '/v1/document-drafts'


@pytest.fixture
def trade(core_client):
    c = core_client
    supplier = post(c, '/parties', {'name': 'KURGUSAL tedarikçi', 'roles': ['supplier']})
    customer = post(c, '/parties', {'name': 'KURGUSAL İğde Şarküteri', 'roles': ['customer'], 'contact': 'belge@example.invalid'})
    w = post(c, '/locations', {'name': 'KURGUSAL belge deposu'})
    q = post(c, '/locations', {'name': 'KURGUSAL karantina', 'kind': 'quarantine'})
    products = [post(c, '/products', {'sku': 'DOC-' + unit, 'name': 'KURGUSAL ürün ' + unit,
                                     'type': 'raw', 'base_unit': unit,
                                     **({'package_weight_kg': '1'} if unit == 'package' else {})}) for unit in ['kg', 'package', 'unit']]
    receipt = post(c, '/receipts', {'supplier_id': supplier['id'], 'location_id': w['id'], 'lines': [
        {'product_id': p['id'], 'external_lot_code': 'KURGUSAL-DOC-' + p['base_unit'], 'quantity': '100', 'total_cost': '100'} for p in products]})
    lots = {line['product_id']: line['lot_id'] for line in receipt['lines']}
    sale = post(c, '/sales', {'customer_id': customer['id'], 'sold_at': '2026-10-27T10:00:00Z', 'lines': [
        {'lot_id': lots[p['id']], 'location_id': w['id'], 'quantity': amount, 'unit': p['base_unit'], 'unit_price': price}
        for p, amount, price in zip(products, ['2.5', '2', '3'], ['1.23', '18.16', '0.00'])]})
    return {'c': c, 'sale': sale, 'customer': customer, 'supplier': supplier, 'w': w['id'], 'q': q['id'], 'products': products}


def source(s):
    r = s['c'].get(BASE + '/sales/' + s['sale']['id'])
    assert r.status_code == 200, r.text
    return r.json()


def pdf(s, draft=None, kind='proforma', expected=None):
    return s['c'].post(BASE + '/proforma/pdf', json={'sale_id': s['sale']['id'], 'kind': kind,
        'expected_source_fingerprint': expected or source(s)['source_fingerprint'], 'draft': draft or {}})


def ship(s, lines=None):
    return post(s['c'], '/shipments', {'customer_id': s['customer']['id'], 'sale_id': s['sale']['id'],
        'shipped_at': '2026-10-27T11:00:00Z', 'lines': [
        {'sale_line_id': line['id'], **{key: line[key] for key in ['lot_id', 'location_id', 'quantity', 'unit']}}
        for line in (lines or s['sale']['lines'])]})


def customer_return(s, full=False):
    return post(s['c'], '/returns', {'sale_id': s['sale']['id'], 'acceptance_location_id': s['q'],
        'returned_at': '2026-10-27T12:00:00Z', 'reason': 'KURGUSAL belge düzeltmesi', 'lines': [
        {'sale_line_id': line['id'], 'quantity': line['quantity'] if full else '1', 'unit': line['unit']}
        for line in (s['sale']['lines'] if full else s['sale']['lines'][:1])]})


def extracted(response):
    assert response.status_code == 200, response.text if response.status_code != 200 else ''
    assert response.headers['content-type'] == 'application/pdf'
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['x-content-type-options'] == 'nosniff'
    assert response.content.startswith(b'%PDF-')
    reader = PdfReader(BytesIO(response.content), strict=True)
    assert not reader.is_encrypted
    for page in reader.pages:
        assert float(page.mediabox.width) == pytest.approx(595.2756, abs=.01)
        assert float(page.mediabox.height) == pytest.approx(841.8898, abs=.01)
    return reader, '\n'.join(page.extract_text() for page in reader.pages)


def test_real_sale_three_units_exact_totals_and_public_fields(trade):
    s = trade; data = source(s)
    assert data['customer'] == {key: s['customer'][key] for key in ['id', 'name', 'contact']}
    assert data['original_total_eur'] == s['sale']['total_amount'] == '39.40'
    for actual, original in zip(data['lines'], s['sale']['lines']):
        for new, old in [('id', 'id'), ('lot_id', 'lot_id'), ('quantity', 'quantity'), ('unit', 'unit'),
                         ('unit_price_eur', 'unit_price'), ('total_eur', 'total_amount')]:
            assert actual[new] == original[old]
    assert [l['total_eur'] for l in data['lines']] == ['3.08', '36.32', '0.00']
    assert data['shipments'] == data['corrections'] == []
    assert data['payment_status'] == data['tax_information'] == 'not_recorded'
    assert not any(word in str(data) for word in ['consumed_cost', 'recognized_cost', 'gross_profit', 'margin_percent'])


def test_only_truly_linked_multiple_shipments(trade):
    s = trade
    first = ship(s, s['sale']['lines'][:1]); second = ship(s, s['sale']['lines'][1:])
    line = s['sale']['lines'][0]
    unrelated = post(s['c'], '/shipments', {'customer_id': s['customer']['id'], 'lines': [
        {'lot_id': line['lot_id'], 'location_id': line['location_id'], 'quantity': '1', 'unit': line['unit']}]})
    data = source(s)
    assert {row['id'] for row in data['shipments']} == {first['id'], second['id']}
    assert unrelated['id'] not in str(data)
    assert {line['sale_line_id'] for row in data['shipments'] for line in row['lines']} == {line['id'] for line in s['sale']['lines']}


@pytest.mark.parametrize('state', ['active', 'partially_returned', 'returned', 'cancelled'])
def test_correction_status_original_and_net_are_distinct(trade, mysql_core, state):
    s = trade
    if state in ('partially_returned', 'returned'):
        ship(s); customer_return(s, full=state == 'returned')
    elif state == 'cancelled':
        post(s['c'], '/sales/' + s['sale']['id'] + '/cancel', {'acceptance_location_id': s['q'],
             'cancelled_at': '2026-10-27T12:00:00Z', 'reason': 'KURGUSAL belge iptali'}, status=200)
    before = snapshot(mysql_core)
    data = source(s)
    financial = s['c'].get('/v1/sales/' + s['sale']['id'] + '/profitability').json()
    assert data['state'] == state and data['original_total_eur'] == '39.40'
    assert data['net_after_adjustments_eur'] == financial['net_after_adjustments']['net_revenue_eur']
    for kind in ['proforma', 'sale_summary']:
        _, text = extracted(pdf(s, kind=kind, draft={'demo': True}))
        assert data['state_label'] in text
        assert 'PROFORMA TASLAĞI' in text if kind == 'proforma' else 'SATIŞ ÖZETİ' in text
        if state in ('cancelled', 'returned'):
            assert 'GÜNCEL ÖDEME TALEBİ DEĞİLDİR' in text
            assert data['net_after_adjustments_eur'] == '0.00'
        assert 'brüt kâr' not in text.lower() and 'tüketim maliyeti' not in text.lower()
    assert snapshot(mysql_core) == before


def test_turkish_real_pdf_safe_filename_and_escaped_markup(trade):
    malicious = '<a href="https://example.invalid">ğ ü ş ı İ ö ç</a> <script>alert(1)</script>'
    r = pdf(trade, {'title': 'İğde Şarküteri — Özel Çalışma', 'note': malicious, 'reference': '../not-a-filename', 'demo': True})
    reader, text = extracted(r)
    assert 'İğde Şarküteri — Özel Çalışma' in text and 'ğ ü ş ı İ ö ç' in text
    assert '<script>alert(1)</script>' in text and 'KURGUSAL DEMO' in text
    assert 'RESMÎ FATURA DEĞİLDİR' in text
    assert r.headers['content-disposition'] == f'attachment; filename="proforma-{trade["sale"]["id"]}.pdf"'
    assert '/JavaScript' not in str(reader.trailer) and all('/Annots' not in page for page in reader.pages)


def test_read_only_repeated_get_pdf_all_30_tables_and_no_write_sql(trade, mysql_core):
    s = trade; ship(s)
    post(s['c'], '/recalls', {'source_lot_id': s['sale']['lines'][0]['lot_id'], 'reason': 'KURGUSAL korunma kanıtı'})
    before = snapshot(mysql_core); statements = []
    def capture(conn, cursor, statement, *args): statements.append(statement.upper().strip())
    event.listen(mysql_core, 'before_cursor_execute', capture)
    try:
        first = source(s)
        assert first == source(s)
        extracted(pdf(s, {'note': 'Değiştirilen not ğ ü ş ı İ ö ç'}))
        extracted(pdf(s, {'note': 'İkinci geçici not'}))
    finally:
        event.remove(mysql_core, 'before_cursor_execute', capture)
    assert len(before) == 30 and snapshot(mysql_core) == before
    assert statements and all(row.startswith(('SELECT', 'SET')) and 'FOR UPDATE' not in row for row in statements)
    # A returned read-only connection must not prevent regular commands.
    post(s['c'], '/parties', {'name': 'KURGUSAL normal yazıcı kontrolü', 'roles': ['supplier']})


def test_accidental_write_rejected_by_real_mysql_and_rolled_back(trade, mysql_core, monkeypatch):
    before = snapshot(mysql_core); errors = []
    def capture(context): errors.append(context.original_exception.args[0])
    def bad_read(db, sale):
        db.execute(insert(m.Party).values(id=str(uuid4()), name='NEVER COMMITTED', roles=['supplier']))
    event.listen(mysql_core, 'handle_error', capture)
    try:
        with monkeypatch.context() as patch:
            patch.setattr(document_drafts.sales, 'profitability', bad_read)
            response = trade['c'].get(BASE + '/sales/' + trade['sale']['id'])
    finally:
        event.remove(mysql_core, 'handle_error', capture)
    assert response.status_code == 503 and response.json()['error']['code'] == 'DATABASE_UNAVAILABLE'
    assert errors == [1792]
    assert snapshot(mysql_core) == before
    assert source(trade)['state'] == 'active'


def test_source_changed_between_preview_and_download_returns_409(trade, mysql_core):
    s = trade; previous = source(s)['source_fingerprint']
    ship(s); customer_return(s)
    before = snapshot(mysql_core)
    stale = pdf(s, expected=previous)
    assert stale.status_code == 409 and stale.json()['error']['code'] == 'DOCUMENT_SOURCE_CHANGED'
    assert snapshot(mysql_core) == before
    _, text = extracted(pdf(s))
    assert 'Kısmi iade' in text


@pytest.mark.parametrize('draft', [{'unit_price': '0.01'}, {'total_amount': '1.00'}, {'customer_id': str(uuid4())},
    {'note': 'x' * 1501}, {'title': 'x' * 121}, {'reference': 'x' * 101},
    {'document_date': '2026-99-99'}, {'note': '\x00'}, {'note': '\u202e'}, {'note': '\n'.join(['a'] * 22)}])
def test_unknown_ledger_fields_limits_controls_and_dates_rejected(trade, mysql_core, draft):
    before = snapshot(mysql_core)
    assert pdf(trade, draft).status_code == 422
    assert snapshot(mysql_core) == before


def test_authorization_unknown_uuid_and_forged_top_level_money(trade):
    c = trade['c']; path = BASE + '/sales/'
    assert c.get(path + str(uuid4())).status_code == 404
    assert c.get(path + 'invalid').status_code == 422
    assert c.get(path + trade['sale']['id'], headers={'X-API-Key': 'invalid'}).status_code == 401
    body = {'sale_id': trade['sale']['id'], 'expected_source_fingerprint': source(trade)['source_fingerprint'], 'unit_price': '0.01'}
    assert c.post(BASE + '/proforma/pdf', json=body).status_code == 422
    assert c.post(BASE + '/proforma/pdf', json=body, headers={'X-API-Key': 'invalid'}).status_code == 401


def test_multiline_long_names_real_pdf_pagination_no_clipping(trade, mysql_core):
    s = trade; c = s['c']
    product = post(c, '/products', {'sku': 'DOC-LONG', 'name': 'KURGUSAL çok uzun Türkçe ürün adı ğ ü ş ı İ ö ç ' * 4, 'type': 'raw', 'base_unit': 'kg'})
    receipt = post(c, '/receipts', {'supplier_id': s['supplier']['id'], 'location_id': s['w'], 'lines': [
        {'product_id': product['id'], 'external_lot_code': f'KURGUSAL-DOC-LONG-{i:03}', 'quantity': '10', 'total_cost': '10'} for i in range(45)]})
    s['sale'] = post(c, '/sales', {'customer_id': s['customer']['id'], 'lines': [
        {'lot_id': line['lot_id'], 'location_id': s['w'], 'quantity': '2.5', 'unit_price': '1.23'} for line in receipt['lines']]})
    before = snapshot(mysql_core)
    reader, text = extracted(pdf(s, {'demo': True, 'note': 'Son not: ğ ü ş ı İ ö ç'}))
    assert 2 <= len(reader.pages) <= 20
    for i in range(45): assert f'KURGUSAL-DOC-LONG-{i:03}' in text
    assert '138,60 EUR' in text and 'Son not: ğ ü ş ı İ ö ç' in text
    # Inspect actual text placement, including repeated footer, within the A4 media box.
    for page in reader.pages:
        assert 'RESMÎ FATURA DEĞİLDİR' in page.extract_text()
        def position(text, cm, tm, font, size):
            if text.strip():
                x = tm[4] * cm[0] + tm[5] * cm[2] + cm[4]
                y = tm[4] * cm[1] + tm[5] * cm[3] + cm[5]
                assert 0 <= x <= 596 and 0 <= y <= 842
        page.extract_text(visitor_text=position)
    assert snapshot(mysql_core) == before
