"""Real read-only HTTP/container acceptance; credentials stay in this process."""
import argparse
import json
from pathlib import Path
import subprocess
import urllib.error
import urllib.request
from release_env import read_environment, ROOT


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--env-file',required=True);parser.add_argument('--output',required=True);args=parser.parse_args()
    env=read_environment(args.env_file)
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def call(base,path,headers=None,body=None):
        request=urllib.request.Request(base+path,headers=headers or {},data=body)
        try:response=opener.open(request,timeout=15)
        except urllib.error.HTTPError as error:response=error
        with response:return response.status,response.read()
    direct='http://127.0.0.1:8000';web='http://127.0.0.1:5173';statuses={}
    for name,base,path,headers,body,expected in [
        ('health',direct,'/health',None,None,200),('ready',direct,'/health/ready',None,None,200),
        ('frontend',web,'/',None,None,200),('models_via_proxy',web,'/api/v1/predictions/models',None,None,200),
        ('direct_requires_key',direct,'/v1/products',None,None,401),
        ('forged_key_replaced',web,'/api/v1/products',{'X-API-Key':'untrusted-client-value'},None,200),
        ('foreign_host',web,'/api/health',{'Host':'evil.example'},None,403),
        ('foreign_origin',web,'/api/v1/products',{'Origin':'https://evil.example'},b'{}',403),
        ('originless_write',web,'/api/v1/products',None,b'{}',403),
        ('cross_site',web,'/api/health',{'Sec-Fetch-Site':'cross-site'},None,403),
    ]:
        status,data=call(base,path,headers,body);assert status==expected,(name,status)
        assert all(v.encode() not in data for k,v in env.items() if k in ('AVATAR_API_KEY','MYSQL_PASSWORD','MYSQL_ROOT_PASSWORD'))
        statuses[name]=status
        if name=='models_via_proxy':assert len(json.loads(data)['models'])==2
    containers={}
    for service in ['mysql','backend','frontend']:
        cmd=['docker','compose','--env-file',str(Path(args.env_file).resolve()),'ps','-q',service]
        id=subprocess.check_output(cmd,cwd=ROOT,text=True).strip();assert id
        def inspect(expression):return subprocess.check_output(['docker','inspect','--format',expression,id],text=True).strip()
        ports=json.loads(inspect('{{json .NetworkSettings.Ports}}'));mode=inspect('{{.HostConfig.NetworkMode}}');health=inspect('{{.State.Health.Status}}')
        assert health=='healthy' and mode!='host'
        for published in ports.values():
            for binding in published or []:assert binding['HostIp']=='127.0.0.1'
        info={'health':health,'network_mode':mode,'ports':ports,'image':inspect('{{.Image}}')}
        if service!='mysql':
            uid=subprocess.check_output(['docker','exec',id,'id','-u'],text=True).strip();assert uid!='0';info['uid']=uid
        if service=='backend':
            code="import json; from app.database import get_engine; from sqlalchemy import text; from alembic.config import Config; from alembic.script import ScriptDirectory; c=get_engine().connect(); print(json.dumps({'database':c.execute(text('SELECT version_num FROM alembic_version')).scalar_one(),'source':ScriptDirectory.from_config(Config('alembic.ini')).get_current_head()}))"
            heads=json.loads(subprocess.check_output(['docker','exec',id,'python','-c',code],text=True))
            info['migration_head']=heads['database'];info['source_migration_head']=heads['source'];assert heads['database']==heads['source']
        containers[service]=info
    report={'main_sha':subprocess.check_output(['git','rev-parse','origin/main'],text=True).strip(),'statuses':statuses,'containers':containers,'model_count':2,'secrets_in_responses':False}
    Path(args.output).write_text(json.dumps(report,indent=2)+'\n');print('Üç servis, migration, iki model, yerel portlar ve proxy güvenlik kontrolleri geçti.')


if __name__=='__main__':main()
