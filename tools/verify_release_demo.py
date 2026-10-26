"""Existing demo commands, real lost POST reply, resume and full replay.

Only an explicit local *_test environment. No DB reset, stock rewriting or new
business calculations. All snapshots are read-only SQLAlchemy selects.
"""
import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
from threading import Thread
import urllib.error
import urllib.request
from urllib.parse import urlsplit

from app.demo_safety import require_local_demo
from app.database import get_engine
from app import models as m


def snapshot():
    with get_engine().connect() as connection:
        return {name:{'rows':len(rows),'sha256':hashlib.sha256('\n'.join(rows).encode()).hexdigest()}
                for name,table in m.Base.metadata.tables.items()
                for rows in [sorted(repr(tuple(row)) for row in connection.execute(table.select()))]}


def main():
    require_local_demo()
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
    upstream=os.environ.get('AVATAR_API_BASE_URL','http://127.0.0.1:8000').rstrip('/')
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    state={'dropped':False,'sales':[]};initial=snapshot()
    class Proxy(BaseHTTPRequestHandler):
        def log_message(self,*_):pass
        def do_GET(self):self.forward()
        def do_POST(self):self.forward()
        def forward(self):
            body=self.rfile.read(int(self.headers.get('Content-Length','0'))) if self.command=='POST' else None
            headers={k:v for k,v in self.headers.items() if k.lower() in ('x-api-key','idempotency-key','content-type')}
            req=urllib.request.Request(upstream+self.path,headers=headers,data=body,method=self.command)
            try:response=opener.open(req,timeout=20)
            except urllib.error.HTTPError as error:response=error
            with response:status=response.status;data=response.read()
            if self.command=='POST' and self.path=='/v1/sales':
                state['sales'].append({'key':self.headers['Idempotency-Key'],'body_sha256':hashlib.sha256(body).hexdigest(),'status':status,'sale_id':json.loads(data).get('id')})
                if status==201 and not state['dropped']:
                    state['dropped']=True;self.close_connection=True
                    self.connection.shutdown(socket.SHUT_RDWR);self.connection.close();return
            self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
    server=ThreadingHTTPServer(('127.0.0.1',0),Proxy);thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    env=os.environ|{'AVATAR_API_BASE_URL':'http://127.0.0.1:'+str(server.server_port)}
    def run(module,*extra,expected=True):
        result=subprocess.run([sys.executable,'-m',module,*extra],env=env,capture_output=True,text=True)
        if not expected:
            assert result.returncode!=0 and state['dropped'],'Fault injection did not interrupt the first sale response';return
        if result.returncode:raise RuntimeError('Demo command failed: '+module+'; secrets/output omitted')
        return json.loads(result.stdout)
    try:
        # Let the real API commit Market A, then lose its HTTP reply.
        run('app.demo_sales_shipments',expected=False)
        assert state['sales'][0]['status']==201
        def flow(directory):
            sales=run('app.demo_sales_shipments');cutting=run('app.demo_cutting');recall=run('app.demo_recall')
            path=str(Path(directory)/'ml.json');run('ml.scripts.demo_api','--output',path);ml=json.loads(Path(path).read_text())
            return {'sales':sales,'cutting':cutting,'recall':recall,'ml':ml}
        with tempfile.TemporaryDirectory(prefix='avatar-release-demo-') as directory:
            first=flow(directory);before_replay=snapshot();second=flow(directory);after_replay=snapshot()
        assert first==second and before_replay==after_replay,'Repeat changed existing demo records'
        assert state['sales'][0]==state['sales'][1],'Lost response retry used another key/body/sale'
        key=os.environ['AVATAR_API_KEY']
        def get(path):
            with opener.open(urllib.request.Request(upstream+'/v1'+path,headers={'X-API-Key':key}),timeout=15) as r:return json.load(r)
        profits=[get('/sales/'+market['sale_id']+'/profitability') for market in first['sales']['markets']]
        source=next(l['lot_id'] for l in get('/operations/'+first['sales']['production']['operation_id'])['inputs'] if get('/lots/'+l['lot_id'])['external_code']=='ET-2026-001')
        forward=get('/lots/'+source+'/trace?direction=forward');backward=get('/lots/'+first['sales']['production']['output_lot_id']+'/trace?direction=backward')
        assert forward['buyers'] and backward['operations']
        report={'data_origin':'KURGUSAL / SYNTHETIC','database':os.environ['MYSQL_DATABASE'],
                'transport':'real TCP HTTP → FastAPI → MySQL 8',
                'lost_sale_response':{'committed_sale_id':state['sales'][0]['sale_id'],'same_key_body_and_sale_on_retry':True},
                'flow_repeated_without_new_records':True,'initial_counts':{k:v['rows'] for k,v in initial.items()},
                'before_replay':before_replay,'after_replay':after_replay,
                'production':first['sales']['production'],'markets':first['recall']['markets'],
                'recall':first['recall'],'cutting':first['cutting'],
                'predictions':{k:{'id':first['ml'][k]['id'],'model_version':first['ml'][k]['model_version'],'data_origin':first['ml'][k]['data_origin'],'comparison':first['ml'][k]['comparison']} for k in ('production','cutting')},
                'profitability':profits,'forward_lots':len(forward['lots']),'backward_lots':len(backward['lots']),
                'android':'Separate instrumentation on this same demo database; not claimed by this script.'}
        Path(args.output).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('Gerçek kayıp POST cevabı, aynı anahtarla devam, iki model, trace/recall ve tam demo tekrarı doğrulandı.')
    finally:
        server.shutdown();server.server_close();thread.join(timeout=5)


if __name__=='__main__':main()
