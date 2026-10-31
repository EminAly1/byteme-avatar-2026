"""Controlled fixtures only; no business DB, API key or Android device operations."""
import http.client
import json
import os
from pathlib import Path
import socket
import stat
import time

import pytest
from tools.apk_status_bridge import StatusBridge
from tools.share_apk import ApkServer


class UnixHTTP(http.client.HTTPConnection):
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX)
        self.sock.settimeout(2)
        self.sock.connect(self.host)


def read(path, route='/status', method='GET', headers=None):
    connection = UnixHTTP(str(path))
    connection.request(method, route, headers=headers or {'Host': 'localhost', 'X-Avatar-Apk-Bridge': '1'})
    response = connection.getresponse()
    result = response.status, response.read(), response.getheader('Cache-Control')
    connection.close()
    return result


def test_private_socket_permissions_status_and_cleanup(tmp_path):
    private = tmp_path / 'private'
    share = ApkServer(('127.0.0.1', 0), b'CONTROLLED APK', 10, 'test-preview')
    path = private / 'status.sock'
    bridge = StatusBridge(path, share)
    try:
        assert stat.S_IMODE(private.stat().st_mode) == 0o700
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        assert path.is_socket() and path.stat().st_size == 0
        code, body, cache = read(path)
        assert code == 200 and cache == 'no-store' and json.loads(body) == {'state': 'inactive'}
        share.serving = True
        assert json.loads(read(path)[1]) == {'state': 'local_only'}
        # No actual listener on this fixture address; real interface is tested separately.
        share.server_address = ('192.168.1.20', share.server_port)
        status = json.loads(read(path)[1])
        assert status['state'] == 'active' and status['url'].endswith(share.token)
        assert status['sha256'] == share.digest and status['bytes'] == len(share.payload)
        with share.state_lock:
            share.used = True
        assert json.loads(read(path)[1]) == {'state': 'used'}
        share.used = False
        share.deadline = time.monotonic() - 1
        assert json.loads(read(path)[1]) == {'state': 'expired'}
        with pytest.raises(ValueError): StatusBridge(path, share)
    finally:
        bridge.close()
        share.server_close()
    assert not path.exists()


def test_status_socket_rejects_unsafe_paths_headers_and_methods(tmp_path):
    share = ApkServer(('127.0.0.1', 0), b'CONTROLLED APK', 10, 'test-preview')
    private = tmp_path / 'private'
    path = private / 'status.sock'
    bridge = StatusBridge(path, share)
    try:
        for route in ['/.env', '/download/anything', '/status?url=anything', '/status/']:
            assert read(path, route)[0] == 403
        for headers in [{'Host': 'localhost'}, {'Host': 'foreign', 'X-Avatar-Apk-Bridge': '1'},
                        {'Host': 'localhost', 'X-Avatar-Apk-Bridge': '1', 'Origin': 'http://evil.test'}]:
            assert read(path, headers=headers)[0] == 403
        assert read(path, method='POST')[0] == 405
    finally:
        bridge.close()
    private.chmod(0o755)
    with pytest.raises(ValueError): StatusBridge(path, share)
    private.chmod(0o700)
    path.write_text('DO NOT OVERWRITE')
    with pytest.raises(ValueError): StatusBridge(path, share)
    assert path.read_text() == 'DO NOT OVERWRITE'
    path.unlink()
    path.symlink_to(tmp_path / 'other')
    with pytest.raises(ValueError): StatusBridge(path, share)
    # Source checkout must never hold a status socket, including traversal aliases.
    with pytest.raises(ValueError): StatusBridge(Path.cwd() / 'tools/../status.sock', share)
    share.server_close()
