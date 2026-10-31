"""RAM-only APK status over an owner-only Unix socket, never the LAN listener."""
import errno
import json
import os
from pathlib import Path
import socket
import socketserver
import stat
import tempfile
import threading
from http.server import BaseHTTPRequestHandler

ROOT = Path(__file__).resolve().parents[1]


def default_socket():
    return Path(tempfile.gettempdir()) / f'.avatar-apk-share-{os.getuid()}' / 'status.sock'


class StatusHandler(BaseHTTPRequestHandler):
    server_version = 'AVATAR-local-status'
    sys_version = ''

    def log_message(self, *args):
        pass  # No URLs/capabilities in access logs.

    def do_GET(self):
        if (self.path != '/status' or self.headers.get('Host') != 'localhost'
                or self.headers.get('Origin') or self.headers.get('X-Avatar-Apk-Bridge') != '1'):
            self.send_error(403, 'Local bridge only')
            return
        body = json.dumps(self.server.share.web_status()).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Connection', 'close')
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        self.send_error(405, 'Read only')

    do_PUT = do_PATCH = do_DELETE = do_POST


class StatusBridge(socketserver.UnixStreamServer):
    def __init__(self, path, share):
        requested = Path(path).absolute()
        self.path = requested.parent.resolve() / requested.name
        if self.path.is_relative_to(ROOT) or requested.parent.is_symlink():
            raise ValueError('Durum soketi kaynak deposu dışında özel bir dizinde olmalı.')
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        parent = self.path.parent.lstat()
        if not stat.S_ISDIR(parent.st_mode) or parent.st_uid != os.getuid() or stat.S_IMODE(parent.st_mode) != 0o700:
            raise ValueError('Durum dizini aynı kullanıcıya ait ve 0700 izinli olmalı.')
        try:
            existing = self.path.lstat()
        except FileNotFoundError:
            existing = None
        if existing:
            if (not stat.S_ISSOCK(existing.st_mode) or existing.st_uid != os.getuid()
                    or stat.S_IMODE(existing.st_mode) != 0o600):
                raise ValueError('Durum yolu güvenli bir yerel soket değil.')
            with socket.socket(socket.AF_UNIX) as probe:
                probe.settimeout(.3)
                result = probe.connect_ex(str(self.path))
                if result == 0:
                    raise ValueError('Önce etkin APK paylaşımını durdurun.')
                if result not in (errno.ECONNREFUSED, errno.ENOENT):
                    raise ValueError('Durum soketi güvenle açılamadı.')
            self.path.unlink()  # Reclaim only this user's dead Unix socket.
        self.share = share
        super().__init__(str(self.path), StatusHandler)
        os.chmod(self.path, 0o600)
        self.identity = self.path.stat().st_ino
        self.thread = threading.Thread(target=self.serve_forever, kwargs={'poll_interval': .1}, daemon=True)
        self.thread.start()

    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(1)
        return connection, address

    def close(self):
        self.shutdown()
        self.thread.join(2)
        self.server_close()
        try:
            if self.path.lstat().st_ino == self.identity:
                self.path.unlink()
        except FileNotFoundError:
            pass
