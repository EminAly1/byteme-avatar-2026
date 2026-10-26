"""Private local-demo environment and optional cloud build configuration.

Standard library only. Never prints credentials or evaluates shell input.
"""
import argparse
import json
import os
from pathlib import Path
import re
import secrets
import socket
import subprocess
import sys
from urllib.parse import urlsplit
from urllib.request import getproxies

ROOT = Path(__file__).resolve().parents[1]


def private_write(path, content):
    path = Path(path).resolve()
    if path.is_relative_to(ROOT):
        raise SystemExit('Özel ortam/build dosyası repository dışında olmalıdır.')
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'w') as out:
        out.write(content)


def read_environment(path):
    values = {}
    for line in Path(path).read_text().splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        key, value = line.split('=', 1)
        if not re.fullmatch('[A-Z][A-Z0-9_]*', key):
            raise SystemExit('Ortam dosyasında geçersiz değişken adı.')
        # Files created by init contain literal, whitespace-free values.
        # No shell, expansion, command substitution or eval is used.
        values[key] = value
    if not values.get('MYSQL_DATABASE', '').endswith('_test'):
        raise SystemExit('Release aracı yalnız ayrı *_test demo veritabanını kabul eder.')
    return values


def main():
    parser = argparse.ArgumentParser(description='İzole yerel demo araçları')
    sub = parser.add_subparsers(dest='action', required=True)
    init = sub.add_parser('init')
    init.add_argument('--env-file', required=True)
    init.add_argument('--project', default='byteme-avatar-demo')
    init.add_argument('--mysql-port', type=int, default=3306)
    run = sub.add_parser('run')
    run.add_argument('--env-file', required=True)
    run.add_argument('--database')
    run.add_argument('--tests', action='store_true')
    run.add_argument('command', nargs=argparse.REMAINDER)
    build = sub.add_parser('build-proxy')
    build.add_argument('--output', required=True)
    args = parser.parse_args()
    if args.action == 'init':
        if not re.fullmatch('[a-z0-9][a-z0-9_-]*', args.project) or not 1 <= args.mysql_port <= 65535:
            parser.error('Geçerli proje adı ve port gerekli.')
        env = {'COMPOSE_PROJECT_NAME': args.project, 'MYSQL_DATABASE': 'avatar_release_demo_test',
               'MYSQL_USER': 'avatar', 'MYSQL_PASSWORD': secrets.token_urlsafe(28),
               'MYSQL_ROOT_PASSWORD': secrets.token_urlsafe(28), 'AVATAR_API_KEY': secrets.token_urlsafe(32),
               'MYSQL_HOST': '127.0.0.1', 'MYSQL_PORT': str(args.mysql_port),
               'MYSQL_PUBLISHED_PORT': str(args.mysql_port), 'CORS_ORIGINS': 'http://127.0.0.1:5173'}
        private_write(args.env_file, '\n'.join(f'{k}={v}' for k, v in env.items()) + '\n')
        print('Özel demo ortam dosyası 0600 izinleriyle oluşturuldu; sırlar gösterilmedi.')
    elif args.action == 'build-proxy':
        proxy = getproxies().get('https')
        url = urlsplit(proxy or '')
        ca = os.getenv('SSL_CERT_FILE') or os.getenv('REQUESTS_CA_BUNDLE')
        if not url.hostname or url.username or url.password or not ca or not Path(ca).is_file():
            raise SystemExit('Kimlik bilgisi içermeyen HTTPS_PROXY ve güvenilir CA dosyası gerekli.')
        build = {'network': 'host', 'extra_hosts': [url.hostname + ':' + socket.gethostbyname(url.hostname)],
                 'args': {'HTTP_PROXY': proxy, 'HTTPS_PROXY': proxy, 'NO_PROXY': ''}, 'secrets': ['build_ca']}
        override = {'services': {s: {'build': build} for s in ('backend', 'frontend')},
                    'secrets': {'build_ca': {'file': str(Path(ca).resolve())}}}
        private_write(args.output, json.dumps(override, indent=2) + '\n')
        print('Yalnız build için proxy/CA ayarı oluşturuldu; runtime ağ sınırı değişmedi.')
    else:
        env = read_environment(args.env_file)
        if args.database:
            if not re.fullmatch('[A-Za-z0-9_]+_test', args.database):
                parser.error('Ayrı test veritabanı adı *_test ile bitmeli.')
            env['MYSQL_DATABASE'] = args.database
        if args.tests:
            original = read_environment(args.env_file)['MYSQL_DATABASE']
            if not args.database or args.database == original:
                parser.error('Yıkıcı testler demo DB üzerinde çalıştırılamaz; ayrı --database gerekli.')
            env.update(AVATAR_MYSQL_TEST='1', AVATAR_CORE_MYSQL_TEST='1')
        env['PYTHONPATH'] = str(ROOT / 'backend')
        env['AVATAR_E2E_DATABASE'] = env['MYSQL_DATABASE']
        command = args.command[1:] if args.command[:1] == ['--'] else args.command
        if not command:
            parser.error('Çalıştırılacak komut gerekli.')
        raise SystemExit(subprocess.run(command, cwd=ROOT, env=os.environ | env).returncode)


if __name__ == '__main__':
    main()
