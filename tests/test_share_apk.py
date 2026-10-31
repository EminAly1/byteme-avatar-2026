from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import subprocess
import sys
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request,build_opener,ProxyHandler
from zipfile import ZipFile
import pytest
from tools.share_apk import ApkServer,load_preview,serve


def fixture_apk(tmp_path):
    data=BytesIO()
    with ZipFile(data,'w') as z:z.writestr('AndroidManifest.xml','CONTROLLED FIXTURE');z.writestr('classes.dex',b'dex\nfixture')
    p=tmp_path/'app-preview.apk';p.write_bytes(data.getvalue())
    (tmp_path/'output-metadata.json').write_text(json.dumps({'applicationId':'com.byteme.avatar.preview','variantName':'preview','elements':[{'outputFile':p.name,'versionName':'test-preview'}]}))
    return p,sha256(p.read_bytes()).hexdigest()


def test_hash_current_build_identity_and_private_file_boundaries(tmp_path):
    p,digest=fixture_apk(tmp_path);payload,actual,_=load_preview(p,digest,tmp_path);assert actual==digest and payload==p.read_bytes()
    with pytest.raises(ValueError):load_preview(p,'0'*64,tmp_path)
    old=tmp_path/'old.apk';old.write_bytes(b'old')
    with pytest.raises(ValueError):load_preview(old,sha256(b'old').hexdigest(),tmp_path)
    meta=tmp_path/'output-metadata.json';s=json.loads(meta.read_text());s['applicationId']='com.byteme.avatar';meta.write_text(json.dumps(s))
    with pytest.raises(ValueError):load_preview(p,digest,tmp_path)


def test_http_shares_only_allowed_apk_then_automatically_stops(tmp_path):
    p,digest=fixture_apk(tmp_path);server=ApkServer(('127.0.0.1',0),p.read_bytes(),10)
    thread=threading.Thread(target=serve,args=(server,),daemon=True);thread.start()
    base='http://127.0.0.1:'+str(server.server_port);opener=build_opener(ProxyHandler({}))
    try:
        for path in ['/','/.env','/../README.md','/download/wrong','/download/'+server.token+'?file=.env']:
            with pytest.raises(HTTPError) as error:opener.open(base+path)
            assert error.value.code==404
        url=base+'/download/'+server.token
        with opener.open(Request(url,method='HEAD')) as r:assert r.headers['X-APK-SHA256']==digest and r.read()==b''
        assert not server.used
        with opener.open(url) as r:assert r.read()==p.read_bytes() and r.headers['Cache-Control']=='no-store'
        thread.join(3);assert not thread.is_alive() and server.used
    finally:
        if thread.is_alive():server.shutdown();thread.join(3)
        server.server_close()


def test_expired_or_used_token_never_returns_apk_bytes():
    server=ApkServer(('127.0.0.1',0),b'CONTROLLED PUBLIC APK',10)
    server.deadline=time.monotonic()-1
    thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.05},daemon=True);thread.start()
    try:
        with pytest.raises(HTTPError) as error:build_opener(ProxyHandler({})).open('http://127.0.0.1:'+str(server.server_port)+'/download/'+server.token)
        assert error.value.code==410 and b'CONTROLLED PUBLIC APK' not in error.value.read()
        thread.join(2);assert not thread.is_alive()
    finally:
        if thread.is_alive():server.shutdown()
        server.server_close()


def test_idle_service_expires_and_lan_requires_explicit_opt_in():
    server=ApkServer(('127.0.0.1',0),b'CONTROLLED PUBLIC APK',.1)
    thread=threading.Thread(target=serve,args=(server,),daemon=True);thread.start();thread.join(2);assert not thread.is_alive()
    for bind in ['192.168.1.5','0.0.0.0','8.8.8.8']:
        result=subprocess.run([sys.executable,'tools/share_apk.py','--bind',bind,'--sha256','0'*64],capture_output=True,text=True)
        assert result.returncode==2
