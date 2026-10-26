"""Repeatable HTTP demo: python -m app.demo. Run against a local demo database."""
import json
import os
import urllib.error
import urllib.request
from uuid import NAMESPACE_URL, uuid5
from app.demo_safety import require_local_demo


def main():
    require_local_demo()
    secret = os.environ.get('AVATAR_API_KEY')
    if not secret:
        raise SystemExit('AVATAR_API_KEY process ortamında gerekli; değeri loglamayın.')
    base = os.environ.get('AVATAR_API_BASE_URL', 'http://127.0.0.1:8000').rstrip('/')

    def post(label, path, payload):
        request = urllib.request.Request(base+'/v1'+path, data=json.dumps(payload).encode(), headers={
            'Content-Type': 'application/json', 'X-API-Key': secret,
            'Idempotency-Key': str(uuid5(NAMESPACE_URL, 'byteme-avatar-demo-v1/'+label)),
        })
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            raise SystemExit(f'Demo {path}: HTTP {exc.code}; API yapılandırmasını ve demo verisini kontrol edin.') from None

    supplier = post('supplier', '/parties', {'name': 'Demo Tedarikçi', 'roles': ['supplier']})
    producer = post('producer', '/parties', {'name': 'Demo Dış Üretici', 'roles': ['producer']})
    warehouse = post('warehouse', '/locations', {'name': 'Demo Merkez'})
    external = post('external', '/locations', {'name': 'Demo Üretici Konumu', 'kind': 'external_producer', 'party_id': producer['id']})
    raw = [post(sku, '/products', {'sku': 'DEMO-'+sku, 'name': name, 'type': 'raw', 'base_unit': 'kg'})
           for sku, name in [('ET', 'Et'), ('BAH', 'Baharat'), ('BAG', 'Bağırsak')]]
    output = post('SUC', '/products', {'sku': 'DEMO-SUC', 'name': 'Narin Sucuk', 'type': 'finished', 'base_unit': 'package', 'package_weight_kg': '1'})
    quantities = ['100', '2', '5']
    receipt = post('receipt', '/receipts', {'supplier_id': supplier['id'], 'location_id': warehouse['id'], 'reference': 'DEMO-ALIS', 'lines': [
        {'product_id': item['id'], 'external_lot_code': code, 'quantity': quantity, 'total_cost': cost}
        for item, code, quantity, cost in zip(raw, ['ET-2026-001', 'BAH-2026-001', 'BAG-2026-001'], quantities, ['970.00', '48.00', '58.00'])]})
    by_product = {line['product_id']: line['lot_id'] for line in receipt['lines']}
    lots = [by_product[product['id']] for product in raw]
    operation = post('operation', '/operations', {'code': 'URT-2026-045', 'producer_id': producer['id']})
    post('dispatch', f"/operations/{operation['id']}/dispatch", {'from_location_id': warehouse['id'], 'to_location_id': external['id'], 'lines': [
        {'lot_id': lot, 'quantity': quantity} for lot, quantity in zip(lots, quantities)]})
    result = post('closure', f"/operations/{operation['id']}/post", {
        'consumed_inputs': [{'lot_id': lot, 'location_id': external['id'], 'quantity': quantity} for lot, quantity in zip(lots, quantities)],
        'output_location_id': warehouse['id'], 'outputs': [{'product_id': output['id'], 'lot_code': 'SUC-2026-045', 'quantity': '85', 'unit': 'package'}],
        'service_costs': [{'amount': '467.50', 'currency': 'EUR', 'invoice_reference': 'DEMO-HIZMET'}],
        'loss_quantity': '22', 'loss_reason': 'Demo miktar farkı; işletme nedeni ayrıca doğrulanmalıdır',
    })
    if result['total_cost_display'] != '1543.50' or result['outputs'][0]['unit_cost_display'] != '18.16' or len(result['lot_links']) != 3:
        raise SystemExit('Demo beklenen maliyet veya lot bağlantılarını üretmedi')
    print(json.dumps({'operation_id': result['id'], 'code': result['code'], 'total_cost': result['total_cost'],
                      'unit_cost_display': result['outputs'][0]['unit_cost_display'], 'output_lot_id': result['outputs'][0]['lot_id'],
                      'lot_link_count': len(result['lot_links'])}, ensure_ascii=False))


if __name__ == '__main__':
    main()
