"""Actual TCP timeout after commit; original command replay must be identical."""
import json
import http.client
import os
import socket
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from uuid import uuid4

import pytest
import uvicorn

from app.main import app
from test_transfers_returns_mysql import stock_case, sell, ship, transfer_body, return_body, cancel_body, snapshot

pytestmark = pytest.mark.skipif(os.getenv('AVATAR_CORE_MYSQL_TEST') != '1', reason='Dedicated *_test MySQL required')


@pytest.mark.parametrize('kind', ['transfer', 'return', 'cancel'])
def test_tcp_response_timeout_replays_same_committed_command(stock_case, mysql_core, kind):
    s = stock_case
    if kind == 'transfer':
        path, body, status = '/transfers', transfer_body(s), 201
    else:
        sale = sell(s)
        if kind == 'return':
            ship(s, sale)
            path, body, status = '/returns', return_body(s, sale), 201
        else:
            path, body, status = '/sales/' + sale['id'] + '/cancel', cancel_body(s), 200
    sock = socket.socket(); sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level='error', lifespan='off'))
    api_thread = threading.Thread(target=lambda: server.run(sockets=[sock]), daemon=True)
    api_thread.start()
    deadline = time.monotonic() + 5
    while not server.started:
        assert time.monotonic() < deadline
        time.sleep(.01)
    committed = []
    commit_seen, release_reply = threading.Event(), threading.Event()
    key = str(uuid4())
    headers = {'X-API-Key': 'test-key-only-not-a-production-credential',
               'Content-Type': 'application/json', 'Idempotency-Key': key}
    data = json.dumps(body).encode()
    upstream = 'http://127.0.0.1:' + str(port) + '/v1' + path
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    class SlowReply(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            received = self.rfile.read(int(self.headers['Content-Length']))
            assert received == data and self.headers['Idempotency-Key'] == key
            with opener.open(urllib.request.Request(upstream, data=received, headers=headers), timeout=5) as response:
                committed.append((response.status, response.read()))
            commit_seen.set()
            # The original command has already committed; only its reply is late.
            assert release_reply.wait(10)
            try:
                self.send_response(committed[0][0]); self.end_headers()
                self.wfile.write(committed[0][1])
            except (BrokenPipeError, ConnectionResetError):
                pass

    proxy = ThreadingHTTPServer(('127.0.0.1', 0), SlowReply)
    proxy_thread = threading.Thread(target=proxy.serve_forever, daemon=True); proxy_thread.start()
    connection = http.client.HTTPConnection('127.0.0.1', proxy.server_port, timeout=5)
    try:
        connection.request('POST', '/v1' + path, body=data, headers=headers)
        # Arm the read timeout only after the real server commit is observed;
        # a slow CI database must not turn this into a pre-commit timeout test.
        assert commit_seen.wait(5) and len(committed) == 1 and committed[0][0] == status
        connection.sock.settimeout(.1)
        with pytest.raises((TimeoutError, socket.timeout)):
            connection.getresponse()
        before = snapshot(mysql_core)
        with opener.open(urllib.request.Request(upstream, data=data, headers=headers), timeout=5) as response:
            assert response.status == status and json.load(response) == json.loads(committed[0][1])
        assert snapshot(mysql_core) == before
    finally:
        connection.close(); release_reply.set()
        proxy.shutdown(); proxy.server_close(); proxy_thread.join(timeout=3)
        server.should_exit = True; api_thread.join(timeout=5); sock.close()
