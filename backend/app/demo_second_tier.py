"""Repeatable fictional ET -> SUC -> A/B/C -> reported X -> recall TCP demo."""
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import socket
import subprocess
import sys
from threading import Thread
import urllib.error
import urllib.request
from uuid import NAMESPACE_URL, uuid5

from app import models as m
from app.database import get_engine
from app.demo_safety import require_local_demo


def fingerprint(*, company_only=False):
    with get_engine().connect() as c:
        rows = {name: sorted(repr(tuple(row)) for row in c.execute(table.select()))
                for name,table in m.Base.metadata.tables.items()
                if not company_only or name not in ('second_tier_distributions','idempotency_requests')}
    return hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()


def main():
    require_local_demo()
    secret=os.environ.get('AVATAR_API_KEY')
    if not secret:raise SystemExit('AVATAR_API_KEY gerekli; değeri loglamayın.')
    upstream=os.getenv('AVATAR_API_BASE_URL','http://127.0.0.1:8000').rstrip('/')
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    state={'dropped':False,'posts':[]}

    class LostReply(BaseHTTPRequestHandler):
        def log_message(self,*_):pass
        def do_GET(self):self.forward()
        def do_POST(self):self.forward()
        def forward(self):
            body=self.rfile.read(int(self.headers.get('Content-Length','0'))) if self.command=='POST' else None
            headers={k:v for k,v in self.headers.items() if k.lower() in ('x-api-key','idempotency-key','content-type')}
            try:response=opener.open(urllib.request.Request(upstream+self.path,data=body,headers=headers),timeout=20)
            except urllib.error.HTTPError as error:response=error
            with response:status,data=response.status,response.read()
            if self.command=='POST' and self.path=='/v1/distributions/second-tier' and status==201:
                state['posts'].append((self.headers['Idempotency-Key'],hashlib.sha256(body).hexdigest(),json.loads(data)['id']))
                if not state['dropped']:
                    state['dropped']=True;self.close_connection=True
                    self.connection.shutdown(socket.SHUT_RDWR);self.connection.close();return
            self.send_response(status);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(data)

    proxy=ThreadingHTTPServer(('127.0.0.1',0),LostReply)
    thread=Thread(target=proxy.serve_forever,daemon=True);thread.start()
    base='http://127.0.0.1:'+str(proxy.server_port)+'/v1'
    def call(path,body=None,label=None,expected=200):
        headers={'X-API-Key':secret}
        if body is not None:
            headers.update({'Content-Type':'application/json','Idempotency-Key':str(uuid5(NAMESPACE_URL,'byteme-second-tier-demo-v1/'+label))})
        request=urllib.request.Request(base+path,data=json.dumps(body).encode() if body is not None else None,headers=headers)
        for attempt in range(2):
            try:response=opener.open(request,timeout=20)
            except urllib.error.HTTPError as error:response=error
            except OSError:
                if attempt==0:continue
                raise SystemExit('Demo cevabı alınamadı; kayıtlar sıfırlanmadı.') from None
            with response:
                if response.status!=expected:raise SystemExit(f'Demo HTTP{response.status}; beklenen{expected}; özel veri gösterilmedi.')
                return json.load(response)

    def flow():
        seeded=subprocess.run([sys.executable,'-m','app.demo_sales_shipments'],capture_output=True,text=True)
        if seeded.returncode:raise SystemExit('Mevcut üretim/market demosu başarısız; kayıtlar silinmedi.')
        seed=json.loads(seeded.stdout);production=seed['production'];market=seed['markets'][0]
        assert production['total_cost']=='1543.500000' and production['unit_cost_display']=='18.16'
        shipment=call('/shipments/'+market['shipment_id']);line=shipment['lines'][0]
        x=call('/parties',{'name':'Dağıtıcı X (KURGUSAL DEMO)','roles':['customer'],
                          'contact':'KURGUSAL — distributor-x@example.invalid'},'recipient-x',201)
        before=fingerprint(company_only=True)
        record=call('/distributions/second-tier',{'source_shipment_line_id':line['id'],'recipient_party_id':x['id'],
            'quantity':'12','unit':'package','distributed_at':shipment['shipped_at'],'reference':'KURGUSAL-SECOND-TIER-001',
            'evidence_note':'KURGUSAL sistem operatörü bildirimi; bağımsız market doğrulaması değildir.'},'distribution',201)
        assert fingerprint(company_only=True)==before
        assert call('/distributions/second-tier/'+record['id'])==record
        operation=call('/operations/'+production['operation_id'])
        roots=[call('/lots/'+row['lot_id']) for row in operation['inputs']]
        root=next(row for row in roots if row['external_code']=='ET-2026-001')
        recall=call('/recalls',{'source_lot_id':root['id'],'reason':'KURGUSAL ikinci kademe recall'},'recall',201)
        report=call('/recalls/'+recall['id'])['report']
        forward=call('/lots/'+root['id']+'/trace?direction=forward')
        backward=call('/lots/'+production['output_lot_id']+'/trace?direction=backward')
        assert record in report['second_tier_distributions'] and record in forward['second_tier_distributions'] and record in backward['second_tier_distributions']
        assert len(report['buyers'])==3 and all(lot['blocked'] for lot in report['lots'])
        assert report['total_shipped_quantities']==[{'product_id':line['product_id'],'unit':'package','quantity':'85.000000'}]
        unknown={row['customer_id']:row for row in report['unknown_distributions']}
        assert unknown[market['customer_id']]['unallocated_documented_quantities'][0]['quantity']=='18.000000'
        assert all(row['market_remaining_quantity'] is row['final_consumer_sold_quantity'] is None for row in unknown.values())
        assert all(unknown[row['customer_id']]['second_tier_recipients'] is None for row in seed['markets'][1:])
        return {'root_lot_id':root['id'],'output_lot_id':production['output_lot_id'],'distribution_id':record['id'],
            'source_shipment_line_id':line['id'],'recipient_party_id':x['id'],'recipient_name':record['recipient_name'],
            'market_shipments_packages':['30','25','30'],'second_tier_packages':'12','company_total_shipped_packages':'85',
            'unallocated_documented_packages':'18','market_physical_stock':None,'consumer_sales':None,
            'total_cost_eur':production['total_cost'],'display_ekp_eur':production['unit_cost_display'],
            'company_ledger_unchanged_by_distribution':True,'recall_id':recall['id'],'trace_both_directions':True}
    try:
        first=flow();before=fingerprint();second=flow();after=fingerprint()
        assert first==second and before==after and state['dropped'] and state['posts'][0]==state['posts'][1]
        print(json.dumps({'data_origin':'KURGUSAL / SYNTHETIC','database':os.environ['MYSQL_DATABASE'],
            'flow':first,'lost_reply_same_key_body_record':True,'repeat_without_new_records':True,
            'domain_tables':len(m.Base.metadata.tables),'before_sha256':before,'after_sha256':after},ensure_ascii=False,indent=2))
    finally:proxy.shutdown();proxy.server_close();thread.join(timeout=5)


if __name__=='__main__':main()
