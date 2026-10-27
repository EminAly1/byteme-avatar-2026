"""Explicit synthetic preparation, followed by a separate GET-only verifier."""
import argparse
from datetime import datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import urllib.error
import urllib.request
from uuid import NAMESPACE_URL, uuid5
from zoneinfo import ZoneInfo

from sqlalchemy import select
from app import models as m
from app.database import get_engine
from app.demo_safety import require_local_demo


def fingerprint():
    with get_engine().connect() as c:
        rows = {name: sorted(repr(tuple(row)) for row in c.execute(table.select())) for name, table in m.Base.metadata.tables.items()}
    return hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()


def main():
    require_local_demo()
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--prepare', action='store_true'); mode.add_argument('--verify', action='store_true')
    parser.add_argument('--seed-file')
    args = parser.parse_args()
    secret = os.environ.get('AVATAR_API_KEY')
    if not secret: raise SystemExit('Özel process API anahtarı gerekli; değeri gösterilmedi.')
    base = os.getenv('AVATAR_API_BASE_URL', 'http://127.0.0.1:8000').rstrip('/') + '/v1'
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def call(path, body=None, label=None):
        headers = {'X-API-Key': secret}
        if body is not None:
            headers.update({'Content-Type': 'application/json', 'Idempotency-Key': str(uuid5(NAMESPACE_URL, 'byteme-alerts-demo-v1/' + label))})
        try:
            with opener.open(urllib.request.Request(base + path, data=json.dumps(body).encode() if body is not None else None, headers=headers), timeout=20) as r:
                return json.load(r)
        except (urllib.error.URLError, OSError):
            raise SystemExit('Demo API isteği başarısız; özel veri/log gösterilmedi ve kayıtlar sıfırlanmadı.') from None
    def post(label, path, body): return call(path, body, label)
    if args.prepare:
        party = post('party', '/parties', {'name': 'KURGUSAL uyarı demo ortağı', 'roles': ['supplier', 'producer']})
        w = post('warehouse', '/locations', {'name': 'KURGUSAL uyarı deposu'})
        ext = post('external', '/locations', {'name': 'KURGUSAL uyarı dış üretici', 'kind': 'external_producer', 'party_id': party['id']})
        def product(code, unit='kg', kind='raw'):
            return post('product-' + code, '/products', {'sku': 'KURGUSAL-ALERT-' + code, 'name': 'KURGUSAL ' + code,
                'type': kind, 'base_unit': unit, **({'package_weight_kg': '1'} if unit == 'package' else {})})
        near, blocked, expired = product('YAKLASAN'), product('BLOKE', 'package', 'finished'), product('GECMIS', 'unit', 'finished')
        today = datetime.now(ZoneInfo('Europe/Istanbul')).date()
        def receipt(label, p, quantity, expiry=None):
            reference = 'KURGUSAL-ALERT-' + label
            if expiry:
                # Preserve the first immutable demo body across midnight/restarts.
                with get_engine().connect() as c:
                    saved = c.execute(select(m.Lot.expires_at).join(m.ReceiptLine, m.ReceiptLine.lot_id == m.Lot.id)
                        .join(m.Receipt, m.Receipt.id == m.ReceiptLine.receipt_id).where(m.Receipt.reference == reference)).all()
                if len(saved) > 1: raise SystemExit('Demo kaynak referansı tekil değil; kayıtlar değiştirilmedi.')
                if saved: expiry = saved[0][0]
            return post('receipt-' + label, '/receipts', {'supplier_id': party['id'], 'location_id': w['id'], 'reference': reference,
                'lines': [{'product_id': p['id'], 'external_lot_code': reference, 'quantity': quantity, 'total_cost': '20',
                           **({'expires_at': expiry.isoformat()} if expiry else {})}]})['lines'][0]['lot_id']
        near_lot = receipt('YAKLASAN', near, '2', today + timedelta(days=3))
        blocked_lot = receipt('BLOKE', blocked, '3')
        expired_lot = receipt('GECMIS', expired, '2', today - timedelta(days=1))
        recall = post('recall', '/recalls', {'source_lot_id': blocked_lot, 'reason': 'KURGUSAL uyarı demoları için açık geri çağırma'})
        raws = [product(code) for code in ['ET', 'BAHARAT', 'BAGIRSAK']]
        output = product('SUC', 'package', 'finished')
        quantities = ['100', '2', '5']
        receipt_raw = post('production-receipt', '/receipts', {'supplier_id': party['id'], 'location_id': w['id'], 'reference': 'KURGUSAL-ALERT-URETIM',
            'lines': [{'product_id': p['id'], 'external_lot_code': 'KURGUSAL-ALERT-' + str(i), 'quantity': quantities[i],
                       'total_cost': ['970', '48', '58'][i]} for i, p in enumerate(raws)]})
        lots = [next(line['lot_id'] for line in receipt_raw['lines'] if line['product_id'] == p['id']) for p in raws]
        op = post('operation', '/operations', {'code': 'KURGUSAL-ALERT-URETIM-001', 'producer_id': party['id']})
        prediction = post('forecast', '/predictions/production', {'operation_id': op['id'], 'output_product_id': output['id'],
            'meat_type': 'beef', 'meat_kg': '100', 'spice_kg': '2', 'casing_kg': '5', 'meat_cost_eur': '970', 'spice_cost_eur': '48', 'casing_cost_eur': '58',
            'planned_producer_profile': 'producer_a', 'package_weight_kg': '1', 'estimated_service_eur': '467.50'})
        post('dispatch', '/operations/' + op['id'] + '/dispatch', {'from_location_id': w['id'], 'to_location_id': ext['id'],
            'lines': [{'lot_id': lot, 'quantity': quantity} for lot, quantity in zip(lots, quantities)]})
        post('close', '/operations/' + op['id'] + '/post', {'consumed_inputs': [{'lot_id': lot, 'location_id': ext['id'], 'quantity': quantity} for lot, quantity in zip(lots, quantities)],
            'output_location_id': w['id'], 'outputs': [{'product_id': output['id'], 'lot_code': 'KURGUSAL-ALERT-SUC', 'quantity': '40', 'unit': 'package'}],
            'service_costs': [{'amount': '467.50', 'invoice_reference': 'KURGUSAL-ALERT-FIILI'}], 'loss_quantity': '67',
            'loss_reason': 'KURGUSAL stres örneği; gerçek işletme ölçümü veya kalite kararı değildir'})
        print(json.dumps({'data_origin': 'KURGUSAL / SYNTHETIC', 'database': os.environ['MYSQL_DATABASE'],
            'near_lot_id': near_lot, 'blocked_lot_id': blocked_lot, 'expired_lot_id': expired_lot, 'recall_id': recall['id'],
            'product_id': near['id'], 'operation_id': op['id'], 'prediction_id': prediction['id'],
            'stock_thresholds': {near['id']: {'quantity': '5', 'unit': 'kg', 'origin': 'demo'}}}, ensure_ascii=False, indent=2))
        return
    if not args.seed_file: parser.error('--verify requires --seed-file')
    seed = json.loads(Path(args.seed_file).read_text())
    def collect():
        rows, cursor = [], None
        while True:
            result = call('/alerts?limit=100' + ('&cursor=' + cursor if cursor else ''))
            rows.extend(result['items']); cursor = result['next_cursor']
            if not cursor: return rows
    before = fingerprint(); first = collect(); second = collect(); summary = call('/alerts/summary')
    for row in first:
        detail = call('/alerts/' + row['id']); assert detail['id'] == row['id'] and detail['source_id'] == row['source_id']
    after = fingerprint()
    assert before == after and [row['id'] for row in first] == [row['id'] for row in second]
    wanted = {'EXPIRY_SOON', 'EXPIRY_PAST', 'LOT_BLOCKED_STOCK', 'LOW_AVAILABLE_STOCK', 'PRODUCTION_EKP_DEVIATION', 'YIELD_DEVIATION'}
    assert wanted <= {row['rule_code'] for row in first}
    assert any(row['source_id'] == seed['near_lot_id'] for row in first if row['rule_code'] == 'EXPIRY_SOON')
    assert any(row['source_id'] == seed['product_id'] for row in first if row['rule_code'] == 'LOW_AVAILABLE_STOCK')
    assert all(row['evidence']['prediction_id'] == seed['prediction_id'] for row in first if row['source_id'] == seed['operation_id'])
    print(json.dumps({'data_origin': 'KURGUSAL / SYNTHETIC', 'database': os.environ['MYSQL_DATABASE'],
        'alert_count': len(first), 'rules': sorted({row['rule_code'] for row in first}), 'counts': summary['summary'],
        'stable_ids': True, 'domain_tables': len(m.Base.metadata.tables), 'before_sha256': before, 'after_sha256': after,
        'ledger_unchanged': True}, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
