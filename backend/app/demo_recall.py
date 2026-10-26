"""Repeatable fictional production -> distribution -> recall HTTP demonstration."""
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5
from app.demo_safety import require_local_demo


def main():
    require_local_demo()
    secret = os.environ.get('AVATAR_API_KEY')
    if not secret:
        raise SystemExit('AVATAR_API_KEY process ortamında gerekli; değeri loglamayın.')
    base = os.environ.get('AVATAR_API_BASE_URL', 'http://127.0.0.1:8000').rstrip('/')
    completed = subprocess.run([sys.executable, '-m', 'app.demo_sales_shipments'], capture_output=True, text=True)
    if completed.returncode:
        raise SystemExit('Üretim/satış demosu başarısız; API ve migration durumunu kontrol edin.')
    seeded = json.loads(completed.stdout)

    def call(path, body=None, label=None, expected=200):
        headers = {'X-API-Key': secret}
        if body is not None:
            headers.update({'Content-Type': 'application/json', 'Idempotency-Key': str(uuid5(NAMESPACE_URL, 'byteme-recall-demo-v1/'+label))})
        request = urllib.request.Request(base+'/v1'+path, headers=headers, data=json.dumps(body).encode() if body is not None else None)
        try:
            response = urllib.request.urlopen(request, timeout=15)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            if response.code != expected:
                raise SystemExit(f'Demo {path}: HTTP {response.code}; beklenen {expected}.')
            return json.load(response)

    production = seeded['production']
    operation = call('/operations/'+production['operation_id'])
    inputs = [call('/lots/'+row['lot_id']) for row in operation['inputs']]
    sources = [x for x in inputs if x['external_code'] == 'ET-2026-001']
    if len(sources) != 1:
        raise SystemExit('Demo kaynak lotu tekil olarak bulunamadı')
    source = sources[0]
    result = call('/recalls', {'source_lot_id': source['id'], 'reason': 'KURGUSAL DEMO — hammadde kalite kontrol problemi'}, 'recall', 201)
    current = call('/recalls/'+result['id'])
    report = current['report']
    affected = report['lots']
    product_id = call('/lots/'+production['output_lot_id'])['product_id']
    shipped = {x['customer_id']: sum((Decimal(q['shipped_quantity']) for q in x['quantities'] if q['product_id'] == product_id and q['unit'] == 'package'), Decimal(0))
               for x in report['buyers']}
    expected = {x['customer_id']: Decimal(x['quantity']) for x in seeded['markets']}
    if shipped != expected or sum(shipped.values()) != 85 or not all(x['blocked'] for x in affected):
        raise SystemExit('Demo raporu gerçek sevkiyatlar veya blokajla uyuşmuyor')
    sale = call('/sales/'+seeded['markets'][0]['sale_id'])
    line = sale['lines'][0]
    denied = call('/sales', {'customer_id': sale['customer_id'], 'lines': [
        {'lot_id': line['lot_id'], 'location_id': line['location_id'], 'quantity': '1', 'unit': line['unit'], 'unit_price': '25.00'}]}, 'blocked-sale', 409)
    if denied['error']['code'] != 'LOT_BLOCKED':
        raise SystemExit('Blokeli lot satışı beklenen nedenle reddedilmedi')
    print(json.dumps({'recall_id': result['id'], 'source_lot_code': source['external_code'],
                      'affected_lots': sorted([{'code': x['external_code'], 'blocked': x['blocked']} for x in affected], key=lambda x: x['code']),
                      'markets': sorted([{'name': x['current_customer']['name'], 'shipped_quantity': format(shipped[x['customer_id']], '.6f')} for x in report['buyers']], key=lambda x:x['name']),
                      'total_shipped_packages': format(sum(shipped.values()), '.6f'), 'blocked_sale_error': denied['error']['code'],
                      'market_remaining_quantity': None, 'final_consumer_sold_quantity': None, 'fictional_contacts': True}, ensure_ascii=False))


if __name__ == '__main__':
    main()
