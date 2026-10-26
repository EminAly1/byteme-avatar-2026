"""ADB workaround for this cloud's read-only home; never changes the app.

Use only with a disposable SDK under /tmp. The actual unmodified SDK ADB runs
in a temporary tool container with a writable default home. Its server binds
host loopback 5037; Android/Gradle still use the real ADB protocol.
"""
import argparse
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
from uuid import uuid4

NAME = os.getenv('AVATAR_ADB_TOOL_NAME', 'avatar-release-adb-tool')


def docker(*args, **kwargs):
    return subprocess.run(['docker', *args], check=True, **kwargs)


def initialize(sdk):
    sdk = Path(sdk).resolve()
    if not sdk.is_relative_to(Path(tempfile.gettempdir()).resolve()):
        raise SystemExit('Bu workaround yalnız geçici /tmp SDK kopyasında kullanılabilir.')
    adb = sdk / 'platform-tools/adb'; backup = adb.with_name('adb.original')
    if not adb.is_file():raise SystemExit('SDK platform-tools/adb bulunamadı.')
    info = subprocess.run(['docker','inspect','--format','{{index .Config.Labels "byteme.release-tool"}}|{{.State.Running}}',NAME],capture_output=True,text=True)
    if info.returncode:
        docker('create','--name',NAME,'--label','byteme.release-tool=adb','--network','host','--entrypoint','sh','python:3.12-slim','-c','mkdir -p /root/.android && exec /tools/adb -P 5037 nodaemon server',stdout=subprocess.DEVNULL)
        docker('cp',str(adb.parent)+'/.',NAME+':/tools')
        if backup.exists():docker('cp',str(backup),NAME+':/tools/adb')
        docker('start',NAME,stdout=subprocess.DEVNULL)
    elif info.stdout.strip()!='adb|true':
        raise SystemExit('Aynı adlı araç container güvenli biçimde yeniden kullanılamıyor; mevcut container değiştirilmedi.')
    if not backup.exists():
        adb.rename(backup)
        # No HOME reassignment, host filesystem changes or shell eval.
        helper=str(Path(__file__).resolve())
        adb.write_text('#!/usr/bin/env python3\nimport runpy,sys\nsys.argv=[ '+repr(helper)+', "forward", *sys.argv[1:]]\nrunpy.run_path('+repr(helper)+',run_name="__main__")\n');adb.chmod(0o755)
    print('Geçici SDK ADB köprüsü hazır; uygulama ve kalıcı SDK değiştirilmedi.')


def forward(args):
    if args[:1]==['--']:args=args[1:]
    copied=[]
    for i,arg in enumerate(args):
        path=Path(arg)
        if path.is_file():
            destination='/tmp/adb-'+uuid4().hex+'-'+path.name
            docker('cp',str(path.resolve()),NAME+':'+destination,stdout=subprocess.DEVNULL)
            args[i]=destination;copied.append(destination)
    try:
        return subprocess.run(['docker','exec','-i',NAME,'/tools/adb',*args]).returncode
    finally:
        if copied:subprocess.run(['docker','exec',NAME,'rm','-f',*copied],stdout=subprocess.DEVNULL)


def main():
    if sys.argv[1:2]==['forward']:raise SystemExit(forward(sys.argv[2:]))
    parser=argparse.ArgumentParser();parser.add_argument('--sdk',required=True);args=parser.parse_args();initialize(args.sdk)


if __name__=='__main__':main()
