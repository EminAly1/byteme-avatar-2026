"""Read existing backend demo, select its UNSOLD value-key 6 kg leg.
Writes a PRIVATE fixture for instrumentation, never a committed credential.
Run with backend/.venv/bin/python and process AVATAR_API_KEY.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument('--fixture', required=True)
parser.add_argument('--device-base', default='http://10.0.2.2:8000/')
args = parser.parse_args()
if Path(args.fixture).resolve().is_relative_to(Path(__file__).resolve().parents[2]):
    raise SystemExit('Gizli test fixture repo dışında tutulmalıdır; örnek: /tmp/avatar-device-fixture.json')
secret = os.environ.get('AVATAR_API_KEY')
if not secret:
    raise SystemExit('AVATAR_API_KEY process ortamında gerekli; anahtarı loglamayın.')
base = os.environ.get('AVATAR_API_BASE_URL', 'http://127.0.0.1:8000').rstrip('/')
result = subprocess.run([sys.executable, '-m', 'app.demo_cutting'], capture_output=True, text=True, env=os.environ)
if result.returncode:
    raise SystemExit('Mevcut backend kesim demosu tamamlanamadı; önce migration/API bağlantısını kontrol edin.')
demo = json.loads(result.stdout)

def get(path):
    with urllib.request.urlopen(urllib.request.Request(base+'/v1'+path, headers={'X-API-Key':secret}), timeout=20) as response:
        return json.load(response)

def pages(path):
    values, cursor, seen = [], None, set()
    while True:
        page = get(path+('?cursor='+cursor if cursor else ''))
        values.extend(page['items']); cursor = page['next_cursor']
        if cursor is None:
            return values
        if cursor in seen:
            raise SystemExit('Demo pagination cycle')
        seen.add(cursor)

product = next(x for x in pages('/products') if x['sku'] == 'DEMO-LAMB-LEG')
operation = get('/cuttings/'+demo['operation_ids']['value'])
output = next(x for x in operation['outputs'] if get('/lots/'+x['lot_id'])['product_id'] == product['id'])
stock = get('/stocks?lot_id='+output['lot_id'])['items'][0]
if stock['quantity'] != '6.000000' or stock['blocked']:
    raise SystemExit('Mobil demo için satılmamış/blokesiz 6 kg value but lotu gerekli. İzole yeni demo DB kullanın; mevcut stok sıfırlanmadı.')
customer = get('/sales/'+demo['sale_id'])['customer_id']
payload = {'base':args.device_base, 'key':secret, 'productId':product['id'], 'lotId':output['lot_id'], 'locationId':stock['location_id'], 'customerId':customer, 'sourceLotId':demo['source_lot_ids']['value']}
path = Path(args.fixture)
# Exclusive private creation; a pre-existing fixture must be removed explicitly.
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd,'w') as file:
    json.dump(payload,file)
print('Kurgusal demo hazır: value but 6 kg. Özel test fixture yazıldı; anahtar gösterilmedi.')
