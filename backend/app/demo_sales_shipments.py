"""Idempotent HTTP seed: existing production demo -> fictional Market A/B/C."""
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
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
    # Preserve app.demo and its original idempotency keys/output contract.
    completed = subprocess.run([sys.executable, '-m', 'app.demo'], capture_output=True, text=True)
    if completed.returncode:
        raise SystemExit('Üretim demo adımı başarısız; API ve migration durumunu kontrol edin.')
    production = json.loads(completed.stdout)

    def call(path, body=None, label=None):
        headers = {'X-API-Key': secret}
        if body is not None:
            headers['Content-Type'] = 'application/json'
            headers['Idempotency-Key'] = str(uuid5(NAMESPACE_URL, 'byteme-avatar-sales-shipments-demo-v1/'+label))
        request = urllib.request.Request(base+'/v1'+path, data=json.dumps(body).encode() if body is not None else None, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            raise SystemExit(f'Demo {path}: HTTP {error.code}; mevcut kayıtların üzerine yazılmadı.') from None

    def all_records(path):
        records, cursor, seen = [], None, set()
        while True:
            page = call(path+('&' if '?' in path else '?')+urllib.parse.urlencode({'limit':100, **({'cursor':cursor} if cursor else {})}))
            records.extend(page['items'])
            cursor = page['next_cursor']
            if cursor is None:
                return records
            if cursor in seen:
                raise SystemExit('Demo sayfalaması tamamlanamadı')
            seen.add(cursor)

    lot_id = production['output_lot_id']
    movements = all_records('/stock-movements?'+urllib.parse.urlencode({'operation_id':production['operation_id'],'lot_id':lot_id}))
    outputs = [x for x in movements if x['type']=='production_output']
    if len(outputs) != 1:
        raise SystemExit('Demo mamul kabul konumu kesin olarak belirlenemedi')
    location_id = outputs[0]['location_id']
    markets = []
    for name, quantity in [('A','30'),('B','25'),('C','30')]:
        customer = call('/parties', {'name':f'Market {name} (KURGUSAL DEMO)', 'roles':['customer'],
                                    'contact':f'KURGUSAL ORNEK — market-{name.lower()}@avatar.example.invalid'}, 'customer-'+name)
        sale = call('/sales', {'customer_id':customer['id'],'lines':[
            {'lot_id':lot_id,'location_id':location_id,'quantity':quantity,'unit':'package','unit_price':'25.00'}]}, 'sale-'+name)
        sale_line = sale['lines'][0]
        shipment = call('/shipments', {'customer_id':customer['id'],'sale_id':sale['id'],'lines':[
            {'sale_line_id':sale_line['id'],'lot_id':lot_id,'location_id':location_id,'quantity':quantity,'unit':'package'}]}, 'shipment-'+name)
        line = shipment['lines'][0]
        if line['stock_movement_id'] != sale_line['stock_movement_id']:
            raise SystemExit('Satış/sevkiyat hareketi eşleşmiyor')
        markets.append({'market':f'Market {name}','customer_id':customer['id'],'recipient_name':shipment['recipient_name'],
                        'recipient_contact':shipment['recipient_contact'],'quantity':line['quantity'],
                        'sale_id':sale['id'],'shipment_id':shipment['id'],'stock_movement_id':line['stock_movement_id']})
    total = sum((Decimal(x['quantity']) for x in markets), Decimal('0'))
    if total != Decimal('85'):
        raise SystemExit('Demo sevkiyat toplamı 85 değil')
    balances = all_records('/stocks?'+urllib.parse.urlencode({'lot_id':lot_id,'location_id':location_id}))
    if len(balances) != 1 or Decimal(balances[0]['quantity']) != 0:
        raise SystemExit('Demo işletme depo bakiyesi sıfır değil; dış değişiklikleri kontrol edin')
    print(json.dumps({'production':production,'fictional_contacts':True,'unit_price_note':'25.00 EUR demo fiyatıdır; PDF verisi değildir.',
                      'markets':markets,'shipped_quantity':format(total,'.6f'),'warehouse_remaining_quantity':balances[0]['quantity'],
                      'market_remaining_quantity':None,'final_consumer_sold_quantity':None,
                      'distribution_note':'Yalnız işletmeden markete kesin sevkiyat bilinir; market stoğu ve son tüketici satışları bilinmiyor.'},ensure_ascii=False))


if __name__ == '__main__':
    main()
