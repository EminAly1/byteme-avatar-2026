"""Verify an existing emulator sale/outbox; never starts another sale or recall."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import tempfile
import time
import urllib.request

from app.demo_safety import require_local_demo
from app.database import get_engine
from app import models as m
from app.commands import canonical
from app.schemas import SaleCreate
from sqlalchemy.orm import Session
from sqlalchemy import select


def snapshot():
    with get_engine().connect() as connection:
        return {name:hashlib.sha256('\n'.join(sorted(repr(tuple(row)) for row in connection.execute(table.select()))).encode()).hexdigest() for name,table in m.Base.metadata.tables.items()}


def main():
    require_local_demo()
    parser=argparse.ArgumentParser();parser.add_argument('--adb',default='adb');parser.add_argument('--serial',required=True);parser.add_argument('--fixture',required=True);parser.add_argument('--output',required=True);args=parser.parse_args()
    if not re.fullmatch('emulator-[0-9]+',args.serial):raise SystemExit('Bu doğrulama yalnız ayrı test emülatörü içindir.')
    fixture=json.loads(Path(args.fixture).read_text());assert fixture['key']==os.environ['AVATAR_API_KEY']
    def adb(*command,check=True):
        result=subprocess.run([args.adb,'-s',args.serial,*command],capture_output=True)
        if check and result.returncode:raise RuntimeError('ADB doğrulaması başarısız; özel çıktı kaydedilmedi.')
        return result
    def local_rows(directory):
        for name in ['avatar-sales.db','avatar-sales.db-wal','avatar-sales.db-shm']:
            data=adb('exec-out','run-as','com.byteme.avatar','cat','databases/'+name,check=False)
            if data.returncode==0:
                p=Path(directory)/name;p.write_bytes(data.stdout);p.chmod(0o600)
        with sqlite3.connect(Path(directory)/'avatar-sales.db') as db:
            db.row_factory=sqlite3.Row
            return {table:[dict(row) for row in db.execute('SELECT * FROM '+table)] for table in ['SaleOutbox','SaleDraft','ConfirmedSaleSnapshot']}
    adb('shell','am','force-stop','com.byteme.avatar')
    with tempfile.TemporaryDirectory(prefix='avatar-android-state-') as directory:
        rows=local_rows(directory)
    confirmed=[r for r in rows['SaleOutbox'] if r['state']=='CONFIRMED'];assert len(confirmed)==1
    row=confirmed[0];cached=next(r for r in rows['ConfirmedSaleSnapshot'] if r['outboxKey']==row['key'])
    payload=SaleCreate.model_validate_json(row['body'])
    assert str(payload.lines[0].lot_id)==fixture['lotId']
    digest=hashlib.sha256(json.dumps(canonical(payload.model_dump()),sort_keys=True,separators=(',',':')).encode()).hexdigest()
    with Session(get_engine()) as db:
        # Fail closed if this is another server/schema, or the original command
        # is absent. A verification must never become a new sale.
        original=db.get(m.IdempotencyRequest,('sales',row['key']))
        assert original and original.request_hash==digest and original.response['id']==cached['id']
        lot=db.get(m.Lot,fixture['sourceLotId']);assert lot and lot.blocked
        stock=db.get(m.StockBalance,(fixture['lotId'],fixture['locationId']));assert str(stock.quantity)=='5.000000'
    before=snapshot();base=os.getenv('AVATAR_API_BASE_URL','http://127.0.0.1:8000').rstrip('/')
    req=urllib.request.Request(base+'/v1/sales',headers={'X-API-Key':fixture['key'],'Content-Type':'application/json','Idempotency-Key':row['key']},data=row['body'].encode())
    with urllib.request.urlopen(req,timeout=15) as response:
        assert response.status==201 and json.load(response)['id']==cached['id']
    assert snapshot()==before
    adb('shell','am','start','-n','com.byteme.avatar/.MainActivity');time.sleep(5)
    adb('shell','am','force-stop','com.byteme.avatar')
    with tempfile.TemporaryDirectory(prefix='avatar-android-reopen-') as directory:reopened=local_rows(directory)
    identity=lambda data:sorted((x['key'],x['body'],x['state']) for x in data['SaleOutbox'])
    assert identity(rows)==identity(reopened) and snapshot()==before
    queued={r['draftId'] for r in rows['SaleOutbox']};offline=sum(r['id'] not in queued for r in rows['SaleDraft'])
    assert offline>=1 and any(r['state']=='NEEDS_ACTION' and r['errorCode']=='LOT_BLOCKED' for r in rows['SaleOutbox'])
    report={'serial':args.serial,'sdk':adb('shell','getprop','ro.build.version.sdk').stdout.decode().strip(),'database':os.environ['MYSQL_DATABASE'],
            'real_sale_id':cached['id'],'central_stock':'5.000000','source_lot_blocked':True,
            'outbox_states':[r['state'] for r in rows['SaleOutbox']],'offline_drafts':offline,
            'original_server_command_verified_before_replay':True,'same_sale_on_replay':True,
            'outbox_key_body_state_survive_process_restart':True,'backend_unchanged_by_replay_and_restart':True,
            'physical_device':False}
    Path(args.output).write_text(json.dumps(report,indent=2)+'\n')
    print('Mevcut Kotlin satışının aynı anahtarla tekrarı, SQLite kalıcılığı ve değişmeyen merkezî kayıtlar doğrulandı.')


if __name__=='__main__':main()
