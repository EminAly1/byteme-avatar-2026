"""Explicit, short-lived single-APK handoff. No application API or directory access."""
import argparse
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import BytesIO
import ipaddress
import json
from pathlib import Path
import re
import secrets
import shutil
import socket
import subprocess
import threading
import time
from urllib.parse import urlsplit
import zipfile

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'android/app/build/outputs/apk/preview'


def load_preview(apk, expected_sha, build_dir=BUILD):
    if not re.fullmatch('[a-fA-F0-9]{64}',expected_sha):raise ValueError('Beklenen SHA256 tam64 hex karakter olmalı.')
    meta=json.loads((Path(build_dir)/'output-metadata.json').read_text())
    if meta.get('applicationId')!='com.byteme.avatar.preview' or meta.get('variantName')!='preview' or len(meta.get('elements',[]))!=1:
        raise ValueError('Güncel Preview build metadata doğrulanamadı; önce assemblePreview çalıştırın.')
    item=meta['elements'][0];filename=item['outputFile']
    if Path(filename).name!=filename:raise ValueError('APK build yolu geçersiz.')
    canonical=Path(build_dir)/filename;apk=Path(apk)
    if canonical.stat().st_size>128*1024*1024:raise ValueError('Build APK boyutu sınırı aşıyor.')
    if not 0<apk.stat().st_size<=128*1024*1024:raise ValueError('APK boyutu geçersiz (en çok128MiB).')
    payload=apk.read_bytes();digest=hashlib.sha256(payload).hexdigest()
    if not hmac.compare_digest(digest,expected_sha.lower()):raise ValueError('Seçilen APK beklenen SHA256 ile eşleşmiyor.')
    if hashlib.sha256(canonical.read_bytes()).hexdigest()!=digest:
        raise ValueError('Bu APK güncel Preview build ile eşleşmiyor; eski APK paylaşılmadı.')
    with zipfile.ZipFile(BytesIO(payload)) as archive:
        if not {'AndroidManifest.xml','classes.dex'}<=set(archive.namelist()):raise ValueError('Geçerli APK yapısı bulunamadı.')
        if any(name.endswith(('.keystore','.jks','.env')) or 'demo-fixture' in name for name in archive.namelist()):
            raise ValueError('APK içinde özel dosya bulundu; paylaşım reddedildi.')
    return payload,digest,item


class ApkServer(HTTPServer):
    def __init__(self,address,payload,ttl):
        if not 0<ttl<=600:raise ValueError('Paylaşım süresi0–600 saniye arasında olmalı.')
        self.payload=payload;self.digest=hashlib.sha256(payload).hexdigest()
        self.token=secrets.token_urlsafe(32);self.deadline=time.monotonic()+ttl;self.used=False;self.denied=0
        super().__init__(address,ApkHandler)
    def get_request(self):
        connection,address=super().get_request();connection.settimeout(2);return connection,address
    def stop(self):threading.Thread(target=self.shutdown,daemon=True).start()


class ApkHandler(BaseHTTPRequestHandler):
    server_version='AVATAR-APK'
    sys_version=''
    def log_message(self,*args):pass  # Capability URLs never enter an access log.
    def ready(self):
        server=self.server
        if time.monotonic()>=server.deadline or server.used:
            self.send_error(410,'Paylasim sona erdi');server.stop();return False
        url=urlsplit(self.path)
        if url.query or url.fragment or not hmac.compare_digest(url.path.encode('utf-8'),('/download/'+server.token).encode('utf-8')):
            self.send_error(404,'Bulunamadi');server.denied+=1
            if server.denied>=32:server.stop()
            return False
        return True
    def send_apk_headers(self):
        self.send_response(200)
        self.send_header('Content-Type','application/vnd.android.package-archive')
        self.send_header('Content-Length',str(len(self.server.payload)))
        self.send_header('Content-Disposition','attachment; filename="AVATAR-Preview.apk"')
        self.send_header('X-APK-SHA256',self.server.digest)
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Connection','close');self.end_headers()
    def do_HEAD(self):
        if self.ready():self.send_apk_headers()
    def do_GET(self):
        if not self.ready():return
        self.server.used=True
        try:
            self.send_apk_headers()
            for offset in range(0,len(self.server.payload),65536):
                if time.monotonic()>=self.server.deadline:break
                self.wfile.write(self.server.payload[offset:offset+65536])
        except (OSError,TimeoutError):pass
        finally:self.server.stop()
    def do_POST(self):self.send_error(405,'Yalniz APK indirme')
    do_PUT=do_PATCH=do_DELETE=do_POST


def serve(server):
    timer=threading.Timer(max(0,server.deadline-time.monotonic()),server.stop);timer.daemon=True;timer.start()
    try:server.serve_forever(poll_interval=.1)
    finally:timer.cancel();server.server_close()


def main():
    p=argparse.ArgumentParser(description='Yalnız güncel Preview APK; varsayılan loopback, LAN açık onay ister.')
    p.add_argument('--apk',type=Path,default=BUILD/'app-preview.apk');p.add_argument('--sha256',required=True)
    p.add_argument('--bind',default='127.0.0.1');p.add_argument('--allow-lan',action='store_true')
    p.add_argument('--port',type=int,default=8765);p.add_argument('--ttl',type=int,default=180)
    a=p.parse_args()
    try:
        address=ipaddress.ip_address(a.bind)
        if address.version!=4 or address.is_unspecified or address.is_multicast or not(address.is_loopback or any(address in ipaddress.ip_network(net) for net in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16'))):
            raise ValueError('Belirli bir yerel IPv4 arabirim adresi girin; genel/0.0.0.0 bind kabul edilmez.')
        if not address.is_loopback and not a.allow_lan:raise ValueError('LAN için --allow-lan açık onayı gerekir.')
        if not 1<=a.port<=65535:raise ValueError('Geçerli port girin.')
        payload,digest,item=load_preview(a.apk,a.sha256)
        server=ApkServer((str(address),a.port),payload,a.ttl)
    except (OSError,ValueError,KeyError,zipfile.BadZipFile) as exc:p.exit(2,str(exc)+'\n')
    print(f'AVATAR Preview {item["versionName"]} · {len(payload)} byte\nSHA256: {digest}')
    print('HTTP şifrelenmez: yalnız güvenilir yerel Wi-Fi. URL gizlidir; API anahtarı paylaşılmaz.')
    url=f'http://{address}:{server.server_port}/download/{server.token}'
    print(f'Telefonda açın: {url}\nBir GET indirmesi veya en çok{a.ttl} saniye; sonra otomatik kapanır.',flush=True)
    if shutil.which('qrencode'):subprocess.run(['qrencode','-t','UTF8',url],check=False)
    try:serve(server)
    except KeyboardInterrupt:server.server_close()


if __name__=='__main__':main()
