"""Real local HTTP → FastAPI → isolated MySQL. All enterprise inputs are demo data."""
import argparse
from decimal import Decimal
import json
import os
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request
from uuid import NAMESPACE_URL, uuid5


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=Path('ml/reports/demo.json'));args=parser.parse_args()
    base=os.environ.get('AVATAR_API_BASE_URL','http://127.0.0.1:8009').rstrip('/')
    if not os.getenv('MYSQL_DATABASE','').endswith('_test') or urllib.parse.urlsplit(base).hostname not in ('127.0.0.1','localhost'):
        raise SystemExit('Demo yalnız yerel API ve aynı ortamla başlatılmış ayrı *_test DB içindir.')
    secret=os.environ.get('AVATAR_API_KEY')
    if not secret:raise SystemExit('AVATAR_API_KEY process ortamında gereklidir; loglamayın.')
    def call(path,body=None,label=None):
        headers={'X-API-Key':secret}
        if body is not None:headers.update({'Content-Type':'application/json','Idempotency-Key':str(uuid5(NAMESPACE_URL,'byteme-ml-task09-v1/'+label))})
        req=urllib.request.Request(base+path,headers=headers,data=json.dumps(body).encode() if body is not None else None)
        try:
            with urllib.request.urlopen(req,timeout=15) as r:return json.load(r)
        except urllib.error.HTTPError as e:raise SystemExit(f'Demo {path}: HTTP {e.code}; kayıtların üzerine yazılmadı.') from None
    def post(path,body,label):return call('/v1'+path,body,label)
    health=call('/health');ready=call('/health/ready');catalog=call('/v1/predictions/models')
    supplier=post('/parties',{'name':'SYNTHETIC ML demo tedarikçisi','roles':['supplier']},'supplier')
    producer=post('/parties',{'name':'SYNTHETIC ML demo üreticisi','roles':['producer']},'producer')
    warehouse=post('/locations',{'name':'SYNTHETIC ML demo deposu'},'warehouse')['id']
    external=post('/locations',{'name':'SYNTHETIC ML demo dış üretici','kind':'external_producer','party_id':producer['id']},'external')['id']
    raw=[post('/products',{'sku':'ML-DEMO-'+sku,'name':sku+' (demo)','type':'raw','base_unit':'kg'},sku) for sku in ['MEAT','SPICE','CASING']]
    product=post('/products',{'sku':'ML-DEMO-SUC','name':'Narin Sucuk (demo)','type':'finished','base_unit':'package','package_weight_kg':'1'},'suc')
    qty=['100','2','5'];cost=['970.00','48.00','58.00']
    receipt=post('/receipts',{'supplier_id':supplier['id'],'location_id':warehouse,'lines':[
        {'product_id':p['id'],'external_lot_code':'ML-DEMO-'+p['sku'],'quantity':q,'total_cost':c} for p,q,c in zip(raw,qty,cost)]},'receipt')
    lots={l['product_id']:l['lot_id'] for l in receipt['lines']}
    op=post('/operations',{'code':'ML-DEMO-URT-001','producer_id':producer['id']},'operation')
    production=post('/predictions/production',dict(operation_id=op['id'],output_product_id=product['id'],meat_type='beef',meat_kg='100',spice_kg='2',casing_kg='5',
        meat_cost_eur='970',spice_cost_eur='48',casing_cost_eur='58',planned_producer_profile='producer_a',package_weight_kg='1',estimated_service_eur='450'),'production-forecast')
    # The independent 450 EUR preliminary quote/profile is fictional, not derived from 85 × 5.50.
    post(f"/operations/{op['id']}/dispatch",{'from_location_id':warehouse,'to_location_id':external,'lines':[{'lot_id':lots[p['id']],'quantity':q} for p,q in zip(raw,qty)]},'dispatch')
    actual=post(f"/operations/{op['id']}/post",{'consumed_inputs':[{'lot_id':lots[p['id']],'location_id':external,'quantity':q} for p,q in zip(raw,qty)],
        'output_location_id':warehouse,'outputs':[{'product_id':product['id'],'lot_code':'ML-DEMO-SUC-001','quantity':'85'}],
        'service_costs':[{'amount':'467.50','invoice_reference':'ML-DEMO-SERVICE'}],'loss_quantity':'22','loss_reason':'PDF örnek miktar farkı; nedeni işletme onayı gerektirir'},'production-close')
    comparison_a=call('/v1/predictions/'+production['id'])
    assert comparison_a['comparison']['predicted_finished_quantity']['actual']=='85.000000' and actual['outputs'][0]['unit_cost_display']=='18.16'
    source=post('/products',{'sku':'ML-DEMO-LAMB','name':'Bütün kuzu (demo)','species':'Kuzu','type':'raw','base_unit':'kg'},'lamb')
    specs=[('leg','But','6'),('shoulder','Omuz','4'),('back','Sırt','4'),('rib','Kaburga','5'),('mince','Kıyma','3')]
    parts={k:post('/products',{'sku':'ML-DEMO-'+k.upper(),'name':name,'type':'finished','base_unit':'kg'},'part-'+k)['id'] for k,name,w in specs}
    recipe=post('/recipes',{'code':'ML-DEMO-LAMB-KEY','version':1,'species':'Kuzu','input_product_id':source['id'],'allocation_method':'quantity','lines':[{'product_id':p} for p in parts.values()]},'recipe')
    purchase=post('/receipts',{'supplier_id':supplier['id'],'location_id':warehouse,'lines':[{'product_id':source['id'],'external_lot_code':'ML-DEMO-LAMB-001','quantity':'25','unit_price':'11.50','total_cost':'287.50'}]},'lamb-receipt')
    cutting=post('/cuttings',{'code':'ML-DEMO-CUT-001','recipe_version_id':recipe['id']},'cutting')
    prediction_b=post('/predictions/cutting',{'operation_id':cutting['id'],'recipe_version_id':recipe['id'],'part_products':parts,'species':'Kuzu','input_weight_kg':'25'},'cutting-forecast')
    post('/cuttings/'+cutting['id']+'/post',{'consumed_inputs':[{'lot_id':purchase['lines'][0]['lot_id'],'location_id':warehouse,'quantity':'25'}],
        'output_location_id':warehouse,'outputs':[{'product_id':parts[k],'lot_code':'ML-DEMO-PART-'+k,'quantity':w} for k,name,w in specs],
        'differences':[{'kind':'waste','quantity':'3','reason':'KURGUSAL demo tartımı ve fark sınıfı; PDF bireysel parça ölçüsü vermez'}]},'cutting-close')
    comparison_b=call('/v1/predictions/'+prediction_b['id'])
    assert sum(Decimal(prediction_b[f'predicted_{p}_kg']) for p in parts)<=25
    assert comparison_b['comparison']['predicted_total_weight_kg']['actual']=='22.000000'
    report={'transport':'real HTTP FastAPI + MySQL 8; separate *_test database','health':health,'ready':ready,
        'data_note':'Training: SYNTHETIC, not enterprise history. Production actual: PDF reference entered into demo ledger. Cutting actual 6/4/4/5/3 and waste classification: FICTIONAL demo.',
        'forecast_features_note':'450 EUR preliminary service quote and producer_a profile are independent fictional assumptions; 85 and 18.16 were not inputs.',
        'model_versions':[m['model_version'] for m in catalog['models']], 'production':comparison_a,'cutting':comparison_b}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'output':str(args.output),'production_forecast_id':production['id'],'cutting_forecast_id':prediction_b['id'],'passed':True}))


if __name__=='__main__':main()
