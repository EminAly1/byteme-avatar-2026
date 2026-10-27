"""Repeatable fictional Task13 HTTP demo on an isolated local *_test database."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request
from uuid import NAMESPACE_URL, uuid5

from app import models as m
from app.database import get_engine
from app.demo_safety import require_local_demo


def snapshot():
    with get_engine().connect() as connection:
        return {name: {'rows': len(rows), 'sha256': hashlib.sha256('\n'.join(rows).encode()).hexdigest()}
                for name, table in m.Base.metadata.tables.items()
                for rows in [sorted(repr(tuple(row)) for row in connection.execute(table.select()))]}


def main():
    require_local_demo()
    parser = argparse.ArgumentParser(); parser.add_argument('--output'); args = parser.parse_args()
    secret = os.environ.get('AVATAR_API_KEY')
    if not secret:
        raise SystemExit('AVATAR_API_KEY process ortamında gerekli; değeri loglamayın.')
    base = os.getenv('AVATAR_API_BASE_URL', 'http://127.0.0.1:8000').rstrip('/') + '/v1'
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def call(path, body=None, label=None, expected=200):
        headers = {'X-API-Key': secret}
        if body is not None:
            headers.update({'Content-Type': 'application/json',
                            'Idempotency-Key': str(uuid5(NAMESPACE_URL, 'byteme-task13-demo-v1/' + label))})
        req = urllib.request.Request(base + path, data=json.dumps(body).encode() if body is not None else None, headers=headers)
        try: response = opener.open(req, timeout=15)
        except urllib.error.HTTPError as error: response = error
        with response:
            if response.status != expected:
                raise SystemExit(f'Demo HTTP {response.status}; beklenen {expected}. Özel çıktı gösterilmedi, stok sıfırlanmadı.')
            return json.load(response)

    def post(label, path, body, status=201):
        return call(path, body, label, status)

    def flow():
        supplier = post('supplier', '/parties', {'name': 'KURGUSAL Görev13 tedarikçisi', 'roles': ['supplier']})
        customer = post('customer', '/parties', {'name': 'KURGUSAL Görev13 müşteri', 'roles': ['customer'], 'contact': 'demo-task13@example.invalid'})
        a = post('warehouse-a', '/locations', {'name': 'KURGUSAL Görev13 Depo A'})['id']
        b = post('warehouse-b', '/locations', {'name': 'KURGUSAL Görev13 Depo B'})['id']
        q = post('quarantine', '/locations', {'name': 'KURGUSAL Görev13 karantina', 'kind': 'quarantine'})['id']
        product = post('product', '/products', {'sku': 'KURGUSAL-TASK13', 'name': 'KURGUSAL Görev13 ürün', 'type': 'raw', 'base_unit': 'kg'})
        receipt = post('receipt', '/receipts', {'supplier_id': supplier['id'], 'location_id': a,
            'received_at': '2026-10-25T08:00:00Z', 'reference': 'KURGUSAL-G13-ALIS',
            'lines': [{'product_id': product['id'], 'external_lot_code': 'KURGUSAL-G13-LOT', 'quantity': '20', 'total_cost': '194.00'}]})
        lot = receipt['lines'][0]['lot_id']
        transfer = post('transfer-seven', '/transfers', {'lot_id': lot, 'from_location_id': a, 'to_location_id': b,
            'quantity': '7', 'unit': 'kg', 'reference': 'KURGUSAL-G13-TRANSFER', 'reason': 'KURGUSAL depo transferi'})
        sale_body = {'customer_id': customer['id'], 'lines': [{'lot_id': lot, 'location_id': b, 'quantity': '5', 'unit': 'kg', 'unit_price': '20.00'}]}
        sale = post('delivered-sale', '/sales', sale_body)
        shipment = post('linked-shipment', '/shipments', {'customer_id': customer['id'], 'sale_id': sale['id'],
            'lines': [{'sale_line_id': sale['lines'][0]['id'], 'lot_id': lot, 'location_id': b, 'quantity': '5', 'unit': 'kg'}]})
        returned = post('partial-return', '/returns', {'sale_id': sale['id'], 'acceptance_location_id': q,
            'reason': 'KURGUSAL kısmi müşteri iadesi', 'reference': 'KURGUSAL-G13-IADE',
            'lines': [{'sale_line_id': sale['lines'][0]['id'], 'quantity': '2', 'unit': 'kg'}]})
        unshipped = post('unshipped-sale', '/sales', {'customer_id': customer['id'],
            'lines': [{'lot_id': lot, 'location_id': a, 'quantity': '3', 'unit': 'kg', 'unit_price': '20.00'}]})
        cancelled = post('cancel-unshipped', '/sales/' + unshipped['id'] + '/cancel',
                         {'acceptance_location_id': q, 'reason': 'KURGUSAL sevk öncesi iptal'}, 200)
        recall = post('recall', '/recalls', {'source_lot_id': lot, 'reason': 'KURGUSAL Görev13 geri çağırma'})
        rejected = post('blocked-sale', '/sales', {'customer_id': customer['id'],
            'lines': [{'lot_id': lot, 'location_id': a, 'quantity': '1', 'unit': 'kg', 'unit_price': '20.00'}]}, 409)
        assert rejected['error']['code'] == 'LOT_BLOCKED'
        stocks = call('/stocks?' + urllib.parse.urlencode({'lot_id': lot}))['items']
        assert {row['location_id']: row['quantity'] for row in stocks} == {a: '10.000000', b: '2.000000', q: '5.000000'}
        assert all(row['blocked'] and row['available_quantity'] == '0.000000' for row in stocks)
        assert transfer['movements'][0]['quantity'] == '-7.000000' and transfer['movements'][1]['quantity'] == '7.000000'
        assert transfer['cost_effect'] == 'none'
        assert returned['credit_amount'] == '40.00' and returned['restored_cost'] == '19.400000'
        assert cancelled['credit_amount'] == '60.00' and cancelled['restored_cost'] == '29.100000'
        assert cancelled['lines'][0]['movement']['reversal_of'] == unshipped['lines'][0]['stock_movement_id']
        assert cancelled['lines'][0]['movement']['location_id'] == a
        assert [row['quantity'] for row in cancelled['lines'][0]['quarantine_movements']] == ['-3.000000', '3.000000']
        lot_data = call('/lots/' + lot)
        assert lot_data['consumed_quantity'] == '8.000000' and lot_data['consumed_cost'] == '77.600000'
        profit = call('/sales/' + sale['id'] + '/profitability')
        assert profit['net_revenue_eur'] == '100.00' and profit['net_after_adjustments']['net_revenue_eur'] == '60.00'
        assert profit['net_after_adjustments']['recognized_cost_eur'] == '29.100000'
        cancelled_profit = call('/sales/' + unshipped['id'] + '/profitability')
        assert cancelled_profit['net_after_adjustments']['net_revenue_eur'] == '0.00'
        forward = call('/lots/' + lot + '/trace?direction=forward')
        backward = call('/lots/' + lot + '/trace?direction=backward')
        assert forward['transfers'][0]['id'] == transfer['id']
        assert forward['customer_returns'][0]['id'] == returned['id'] and forward['sale_cancellations'][0]['id'] == cancelled['id']
        assert backward['source_lot']['id'] == lot
        return {'receipt': receipt, 'transfer': transfer,
                'transfer_phase': {'basis': 'recorded receipt20 plus paired transfer movements -7/+7, before later sale issues',
                                   'warehouse_a': '13.000000', 'warehouse_b': '7.000000', 'total': '20.000000'},
                'sale': sale, 'shipment': shipment, 'return': returned, 'cancellation': cancelled,
                'recall_id': recall['id'], 'final_stocks': stocks, 'lot': lot_data,
                'profitability': profit, 'cancelled_profitability': cancelled_profit,
                'blocked_sale_code': rejected['error']['code'], 'trace': forward}

    first = flow(); before = snapshot(); second = flow(); after = snapshot()
    assert first == second and before == after, 'Tekrar yeni kayıt veya maliyet değişikliği oluşturdu'
    result = {'data_origin': 'KURGUSAL / SYNTHETIC', 'database': os.environ['MYSQL_DATABASE'],
              'transport': 'real TCP HTTP -> FastAPI -> MySQL8', 'scenario': first,
              'second_full_run_same_responses_and_database': True, 'before_replay': before, 'after_replay': after,
              'quality_release': 'not implemented; all recovered stock remains quarantined',
              'cash_refund_status': 'not recorded; net sale credits and cost reversals only'}
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        Path(args.output).write_text(encoded)
        print('KURGUSAL transfer/iade/iptal/recall/kârlılık demosu iki kez aynı29 tabloyla tamamlandı.')
    else:
        print(encoded, end='')


if __name__ == '__main__':
    main()
