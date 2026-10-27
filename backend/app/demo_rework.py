"""Fictional, repeatable TCP demo; commits once despite a lost closing reply."""
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import socket
from threading import Thread
import urllib.error
import urllib.parse
import urllib.request
from uuid import NAMESPACE_URL, uuid5
from datetime import datetime, timezone, timedelta

from app.database import get_engine
from app import models as m
from app.demo_safety import require_local_demo


def fingerprint():
    with get_engine().connect() as connection:
        rows = {name: sorted(repr(tuple(row)) for row in connection.execute(table.select()))
                for name, table in m.Base.metadata.tables.items()}
    return hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()


def main():
    require_local_demo()
    secret = os.environ.get('AVATAR_API_KEY')
    if not secret: raise SystemExit('AVATAR_API_KEY gerekli; değeri loglamayın.')
    upstream = os.getenv('AVATAR_API_BASE_URL', 'http://127.0.0.1:8000').rstrip('/')
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    state = {'dropped': False, 'rework_posts': []}

    class LostReply(BaseHTTPRequestHandler):
        def log_message(self, *_): pass
        def do_GET(self): self.forward()
        def do_POST(self): self.forward()
        def forward(self):
            body = self.rfile.read(int(self.headers.get('Content-Length', '0'))) if self.command == 'POST' else None
            headers = {k: v for k, v in self.headers.items() if k.lower() in ('x-api-key', 'idempotency-key', 'content-type')}
            try: response = opener.open(urllib.request.Request(upstream + self.path, data=body, headers=headers), timeout=20)
            except urllib.error.HTTPError as error: response = error
            with response: status, data = response.status, response.read()
            if self.command == 'POST' and self.path.startswith('/v1/reworks/') and self.path.endswith('/post') and status == 200:
                state['rework_posts'].append((self.headers['Idempotency-Key'], hashlib.sha256(body).hexdigest(), json.loads(data)['id']))
                if not state['dropped']:
                    state['dropped'] = True; self.close_connection = True
                    self.connection.shutdown(socket.SHUT_RDWR); self.connection.close(); return
            self.send_response(status); self.send_header('Content-Type', 'application/json'); self.end_headers(); self.wfile.write(data)

    proxy = ThreadingHTTPServer(('127.0.0.1', 0), LostReply)
    thread = Thread(target=proxy.serve_forever, daemon=True); thread.start()
    base = 'http://127.0.0.1:' + str(proxy.server_port) + '/v1'

    def call(path, body=None, label=None, expected=200):
        headers = {'X-API-Key': secret}
        if body is not None:
            headers.update({'Content-Type': 'application/json',
                            'Idempotency-Key': str(uuid5(NAMESPACE_URL, 'byteme-rework-demo-v1/' + label))})
        request = urllib.request.Request(base + path, data=json.dumps(body).encode() if body is not None else None, headers=headers)
        for attempt in range(2):
            try: response = opener.open(request, timeout=20)
            except urllib.error.HTTPError as error: response = error
            except OSError:
                if attempt == 0: continue  # Same immutable key and bytes.
                raise SystemExit('Demo ağ cevabı alınamadı; kayıtlar sıfırlanmadı.') from None
            with response:
                if response.status != expected:
                    raise SystemExit(f'Demo HTTP{response.status}, beklenen{expected}; özel veri gösterilmedi.')
                return json.load(response)

    def post(label, path, body, expected=201): return call(path, body, label, expected)

    def flow():
        supplier = post('supplier', '/parties', {'name': 'KURGUSAL rework tedarikçisi', 'roles': ['supplier']})['id']
        producer = post('producer', '/parties', {'name': 'KURGUSAL rework üreticisi', 'roles': ['producer']})['id']
        customer = post('customer', '/parties', {'name': 'KURGUSAL rework marketi', 'roles': ['customer'], 'contact': 'rework-demo@example.invalid'})['id']
        w = post('warehouse', '/locations', {'name': 'KURGUSAL rework deposu'})['id']
        ext = post('external', '/locations', {'name': 'KURGUSAL rework dış üretici', 'kind': 'external_producer', 'party_id': producer})['id']
        products = [post('product-' + name, '/products', {'sku': 'KURGUSAL-RW-' + name, 'name': 'KURGUSAL ' + name, 'type': kind, 'base_unit': 'kg'})['id']
                    for name, kind in [('RAW', 'raw'), ('SOURCE', 'finished'), ('OUTPUT', 'finished')]]
        receipt = post('receipt', '/receipts', {'supplier_id': supplier, 'location_id': w, 'lines': [
            {'product_id': products[0], 'external_lot_code': 'KURGUSAL-RW-RAW', 'quantity': '20', 'total_cost': '200.00'}]})
        root = receipt['lines'][0]['lot_id']
        origin = post('origin', '/operations', {'code': 'KURGUSAL-RW-ORIGIN', 'producer_id': producer})['id']
        post('dispatch', '/operations/' + origin + '/dispatch', {'from_location_id': w, 'to_location_id': ext, 'lines': [{'lot_id': root, 'quantity': '20'}]}, 200)
        existing = call('/operations/' + origin)['outputs']
        # Freeze the first seed's date when repeated on a later day. No new date
        # is invented by rework; the already recorded source expiry is reused.
        expiry = call('/lots/' + existing[0]['lot_id'])['expires_at'] if existing else (datetime.now(timezone.utc).date() + timedelta(days=30)).isoformat()
        parent = post('origin-post', '/operations/' + origin + '/post', {
            'consumed_inputs': [{'lot_id': root, 'location_id': ext, 'quantity': '20'}], 'output_location_id': w,
            'outputs': [{'product_id': products[1], 'lot_code': 'KURGUSAL-RW-SOURCE', 'quantity': '20', 'unit': 'kg', 'expires_at': expiry}],
            'service_costs': [], 'loss_quantity': '0'}, 200)
        source = parent['outputs'][0]['lot_id']
        draft = post('draft', '/reworks', {'code': 'KURGUSAL-RW-001', 'source_lot_id': source, 'source_location_id': w,
            'input_quantity': '10', 'reason': 'KURGUSAL matematiksel rework örneği; gerçek ölçüm değildir', 'output_product_ids': [products[2]]})
        closed = post('post', '/reworks/' + draft['id'] + '/post', {'output_location_id': w,
            'outputs': [{'product_id': products[2], 'lot_code': 'KURGUSAL-RW-OUTPUT', 'quantity': '9.5', 'unit': 'kg'}],
            'differences': [{'kind': 'other_loss', 'quantity': '.5', 'reason': 'KURGUSAL ölçüm örneği'}],
            'service_costs': [{'amount': '15.00', 'invoice_reference': 'KURGUSAL-RW-SERVICE'}]}, 200)
        output = closed['outputs'][0]['lot_id']
        assert closed['total_material_cost'] == '100.000000' and closed['total_cost'] == '115.000000'
        assert closed['outputs'][0]['expires_at'] == expiry
        sale_body = {'customer_id': customer, 'lines': [{'lot_id': output, 'location_id': w, 'quantity': '1', 'unit': 'kg', 'unit_price': '25.00'}]}
        sale = post('sale', '/sales', sale_body)
        post('shipment', '/shipments', {'customer_id': customer, 'sale_id': sale['id'], 'lines': [
            {'sale_line_id': sale['lines'][0]['id'], 'lot_id': output, 'location_id': w, 'quantity': '1', 'unit': 'kg'}]})
        forward = call('/lots/' + root + '/trace')
        backward = call('/lots/' + output + '/trace?direction=backward')
        assert {root, source, output} <= {x['id'] for x in forward['lots']} and len(backward['operations']) == 2
        recall = post('recall', '/recalls', {'source_lot_id': root, 'reason': 'KURGUSAL rework ata recall'})
        assert output in {x['id'] for x in recall['report']['lots']}
        rejected = post('blocked-sale', '/sales', sale_body, 409)
        assert rejected['error']['code'] == 'LOT_BLOCKED'
        balances = {lot: call('/stocks?' + urllib.parse.urlencode({'lot_id': lot, 'location_id': w}))['items'][0] for lot in [source, output]}
        assert balances[source]['quantity'] == '10.000000' and balances[output]['quantity'] == '8.500000'
        assert all(x['blocked'] and x['available_quantity'] == '0.000000' for x in balances.values())
        return {'root_lot': root, 'source_lot': source, 'rework_id': closed['id'], 'output_lot': output,
                'source_cost_eur': closed['total_material_cost'], 'service_cost_eur': closed['total_service_cost'],
                'output_cost_eur': closed['total_cost'], 'input_kg': '10', 'output_kg': '9.5', 'loss_kg': '0.5',
                'source_remaining_kg': '10', 'output_after_sale_kg': '8.5', 'expiry': expiry,
                'sale_id': sale['id'], 'recall_id': recall['id'], 'blocked_sale_code': rejected['error']['code']}
    try:
        first = flow(); before = fingerprint(); second = flow(); after = fingerprint()
        assert first == second and before == after
        assert state['dropped'] and state['rework_posts'][0] == state['rework_posts'][1]
        print(json.dumps({'data_origin': 'KURGUSAL / SYNTHETIC', 'database': os.environ['MYSQL_DATABASE'], 'flow': first,
                          'lost_post_reply_same_key_body_operation': True, 'repeat_without_new_records': True,
                          'domain_tables': len(m.Base.metadata.tables), 'before_sha256': before, 'after_sha256': after}, ensure_ascii=False, indent=2))
    finally:
        proxy.shutdown(); proxy.server_close(); thread.join(timeout=5)


if __name__ == '__main__': main()
