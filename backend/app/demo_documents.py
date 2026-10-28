"""Explicit fictional preparation and separate read-only PDF acceptance CLI."""
import argparse
from io import BytesIO
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.error
import urllib.request
from uuid import NAMESPACE_URL, uuid5

from app import models as m
from app.database import get_engine
from app.demo_safety import require_local_demo


def ledger_hash():
    with get_engine().connect().execution_options(isolation_level='REPEATABLE READ') as connection:
        connection.exec_driver_sql('SET TRANSACTION READ ONLY')
        records = {name: sorted(repr(tuple(row)) for row in connection.execute(table.select()))
                   for name, table in m.Base.metadata.tables.items()}
    return hashlib.sha256(json.dumps(records, sort_keys=True).encode()).hexdigest()


def main():
    require_local_demo()
    parser = argparse.ArgumentParser(description='KURGUSAL belge demosu; yalnız ayrı *_test veritabanı')
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--prepare', action='store_true'); mode.add_argument('--verify', action='store_true')
    parser.add_argument('--seed-file'); parser.add_argument('--output-dir', default='/tmp/avatar-task18-documents')
    args = parser.parse_args()
    secret = os.environ.get('AVATAR_API_KEY')
    if not secret: raise SystemExit('Özel process API anahtarı gerekli; değeri gösterilmedi.')
    base = os.environ.get('AVATAR_API_BASE_URL', 'http://127.0.0.1:8000').rstrip('/')
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def call(path, body=None, label=None):
        headers = {'X-API-Key': secret}
        if body is not None:
            headers['Content-Type'] = 'application/json'
            if label: headers['Idempotency-Key'] = str(uuid5(NAMESPACE_URL, 'byteme-document-demo-v1/' + label))
        req = urllib.request.Request(base + '/v1' + path, data=json.dumps(body).encode() if body is not None else None, headers=headers)
        try:
            with opener.open(req, timeout=30) as response:
                raw = response.read()
                if response.headers.get_content_type() == 'application/pdf': return raw
                return json.loads(raw)
        except (urllib.error.URLError, OSError):
            raise SystemExit('Demo isteği başarısız; müşteri verisi/anahtar loglanmadı, mevcut veriler sıfırlanmadı.') from None

    if args.prepare:
        # Existing ET→URT→SUC production / 85 package sale and shipment demo is preserved.
        env = os.environ | {'AVATAR_API_BASE_URL': base}
        production = subprocess.run([sys.executable, '-m', 'app.demo_sales_shipments'], env=env, capture_output=True, text=True)
        if production.returncode: raise SystemExit('Mevcut üretim/satış demo hazırlığı başarısız; kayıtlar sıfırlanmadı.')
        original = json.loads(production.stdout)
        q = call('/locations', {'name': 'KURGUSAL belge karantinası', 'kind': 'quarantine'}, 'quarantine')
        for i, full in [(1, False), (2, True)]:
            sale = call('/sales/' + original['markets'][i]['sale_id'])
            call('/returns', {'sale_id': sale['id'], 'acceptance_location_id': q['id'], 'reason': 'KURGUSAL belge kabul iadesi',
                'lines': [{'sale_line_id': line['id'], 'quantity': line['quantity'] if full else '2', 'unit': line['unit']} for line in sale['lines']]}, 'return-' + str(i))
        supplier = call('/parties', {'name': 'KURGUSAL belge tedarikçisi', 'roles': ['supplier']}, 'supplier')
        customer = call('/parties', {'name': 'KURGUSAL İğde Şarküteri — uzun müşteri unvanı ve Türkçe ğ ü ş ı İ ö ç',
            'roles': ['customer'], 'contact': 'KURGUSAL örnek — belge@example.invalid'}, 'customer')
        w = call('/locations', {'name': 'KURGUSAL belge deposu'}, 'warehouse')
        product = call('/products', {'sku': 'KURGUSAL-DOC-LONG', 'name': 'KURGUSAL İğde Şarküteri — özel üretim, soğuk zincirde taşınan ürün ğ ü ş ı İ ö ç ' * 2,
            'type': 'raw', 'base_unit': 'kg'}, 'product')
        receipt = call('/receipts', {'supplier_id': supplier['id'], 'location_id': w['id'], 'reference': 'KURGUSAL belge uzun tablo',
            'lines': [{'product_id': product['id'], 'external_lot_code': f'KURGUSAL-DOC-LONG-{i:03}', 'quantity': '10', 'total_cost': '9.70'} for i in range(46)]}, 'receipt')
        by_lot = {row['lot_id']: row for row in receipt['lines']}
        ordered = sorted(by_lot)
        long_sale = call('/sales', {'customer_id': customer['id'], 'lines': [
            {'lot_id': lot, 'location_id': w['id'], 'quantity': '2.5', 'unit': 'kg', 'unit_price': '1.23'} for lot in ordered[:45]]}, 'long-sale')
        for i, lines in enumerate([long_sale['lines'][:22], long_sale['lines'][22:]]):
            call('/shipments', {'sale_id': long_sale['id'], 'customer_id': customer['id'], 'lines': [
                {'sale_line_id': line['id'], **{key: line[key] for key in ['lot_id', 'location_id', 'quantity', 'unit']}} for line in lines]}, 'long-shipment-' + str(i))
        cancelled = call('/sales', {'customer_id': customer['id'], 'lines': [
            {'lot_id': ordered[-1], 'location_id': w['id'], 'quantity': '2', 'unit': 'kg', 'unit_price': '7.99'}]}, 'cancel-sale')
        call('/sales/' + cancelled['id'] + '/cancel', {'acceptance_location_id': q['id'], 'reason': 'KURGUSAL belge iptali'}, 'cancel')
        recall = call('/recalls', {'source_lot_id': ordered[-1], 'reason': 'KURGUSAL belge salt-okunurluk kanıtı'}, 'recall')
        result = {'data_origin': 'KURGUSAL / SYNTHETIC', 'database': os.environ['MYSQL_DATABASE'],
            'active_sale_id': original['markets'][0]['sale_id'], 'partial_sale_id': original['markets'][1]['sale_id'],
            'returned_sale_id': original['markets'][2]['sale_id'], 'cancelled_sale_id': cancelled['id'],
            'long_sale_id': long_sale['id'], 'recall_id': recall['id'], 'production': original['production']}
        print(json.dumps(result, ensure_ascii=False))
        return

    if not args.seed_file: parser.error('--verify için --seed-file gerekli')
    seed = json.loads(Path(args.seed_file).read_text())
    if seed['database'] != os.environ['MYSQL_DATABASE']: parser.error('Seed ve seçili *_test veritabanı farklı')
    out = Path(args.output_dir).resolve()
    repo = Path(__file__).resolve().parents[2]
    if out.is_relative_to(repo): parser.error('Geçici PDF çıktısı repository dışında olmalı')
    out.mkdir(parents=True, exist_ok=True, mode=0o700)
    before = ledger_hash()
    from pypdf import PdfReader  # requirements-dev; genuine file parsing, never a mock PDF.
    reports = []
    for name, state, kind in [('active', 'active', 'proforma'), ('partial', 'partially_returned', 'sale_summary'),
                              ('returned', 'returned', 'proforma'), ('cancelled', 'cancelled', 'sale_summary'), ('long', 'active', 'proforma')]:
        sale_id = seed[name + '_sale_id']
        data = call('/document-drafts/sales/' + sale_id)
        assert data == call('/document-drafts/sales/' + sale_id) and data['state'] == state
        financial = call('/sales/' + sale_id + '/profitability')
        assert data['net_after_adjustments_eur'] == financial['net_after_adjustments']['net_revenue_eur']
        raw = call('/document-drafts/proforma/pdf', {'sale_id': sale_id, 'kind': kind,
            'expected_source_fingerprint': data['source_fingerprint'], 'draft': {'demo': True,
            'seller_name': 'KURGUSAL İğde Gıda', 'note': 'Türkçe karakterler: ğ ü ş ı İ ö ç'}})
        reader = PdfReader(BytesIO(raw), strict=True)
        text = '\n'.join(page.extract_text() for page in reader.pages)
        assert raw.startswith(b'%PDF-') and 'ğ ü ş ı İ ö ç' in text and 'KURGUSAL DEMO' in text
        for line in data['lines']: assert line['lot_code'] in text
        for page in reader.pages:
            assert abs(float(page.mediabox.width) - 595.2756) < .01 and abs(float(page.mediabox.height) - 841.8898) < .01
        path = out / (name + '.pdf')
        path.write_bytes(raw); path.chmod(0o600)
        reports.append({'case': name, 'state': state, 'pages': len(reader.pages), 'lines': len(data['lines']),
                        'original_eur': data['original_total_eur'], 'net_eur': data['net_after_adjustments_eur']})
    after = ledger_hash()
    assert before == after
    print(json.dumps({'data_origin': seed['data_origin'], 'database': seed['database'], 'documents': reports,
        'domain_tables': len(m.Base.metadata.tables), 'before_sha256': before, 'after_sha256': after, 'ledger_unchanged': True}))


if __name__ == '__main__':
    main()
