"""Opt-in CLI demo boundary; never a substitute for server authorization."""
import os
from urllib.parse import urlsplit


def require_local_demo():
    if not os.environ.get('MYSQL_DATABASE', '').endswith('_test'):
        raise SystemExit('Demo yalnız ayrı MYSQL_DATABASE=..._test ortamında çalıştırılabilir.')
    try:
        url = urlsplit(os.environ.get('AVATAR_API_BASE_URL', 'http://127.0.0.1:8000'))
        port = url.port  # Reject malformed/out-of-range ports without logging the URL.
        valid = (url.scheme == 'http' and url.hostname == '127.0.0.1'
                 and not url.username and not url.password and url.path in ('', '/')
                 and not url.query and not url.fragment and port != 0)
    except ValueError:
        valid = False
    if not valid:
        raise SystemExit('Demo API hedefi yalnız http://127.0.0.1:<port> olabilir.')
