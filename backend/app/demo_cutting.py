"""Idempotent HTTP demo. Individual weights, prices and waste reasons are fictional."""
import json
import os
import urllib.error
import urllib.request
from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5


def main():
    secret = os.environ.get('AVATAR_API_KEY')
    if not secret:
        raise SystemExit('AVATAR_API_KEY process ortamında gerekli; değeri loglamayın.')
    base = os.environ.get('AVATAR_API_BASE_URL', 'http://127.0.0.1:8000').rstrip('/')

    def call(path, body=None, label=None, expected=200):
        headers = {'X-API-Key': secret}
        if body is not None:
            headers.update({'Content-Type': 'application/json', 'Idempotency-Key': str(uuid5(NAMESPACE_URL, 'byteme-lamb-cutting-demo-v1/'+label))})
        request = urllib.request.Request(base+'/v1'+path, headers=headers, data=json.dumps(body).encode() if body is not None else None)
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                if response.code != expected:
                    raise SystemExit(f'Demo {path}: beklenmeyen HTTP {response.code}')
                return json.load(response)
        except urllib.error.HTTPError as error:
            raise SystemExit(f'Demo {path}: HTTP {error.code}; mevcut kayıtların üzerine yazılmadı.') from None

    supplier = call('/parties', {'name':'KURGUSAL DEMO kuzu tedarikçisi','roles':['supplier']}, 'supplier',201)
    buyer = call('/parties', {'name':'KURGUSAL DEMO parça alıcısı','roles':['customer'],'contact':'demo-lamb@avatar.example.invalid'}, 'buyer',201)
    location = call('/locations', {'name':'KURGUSAL DEMO kesim deposu'}, 'warehouse',201)['id']
    source = call('/products', {'sku':'DEMO-LAMB','name':'Bütün kuzu (DEMO)','species':'Kuzu','type':'raw','base_unit':'kg'}, 'source-product',201)
    # The actual PDF supplies only 22 kg total, not individual part weights.
    specifications = [('LEG','But','6','20.00'),('SHOULDER','Omuz','4','14.00'),('BACK','Sırt','4','24.00'),('RIB','Kaburga','5','12.00'),('MINCE','Kıyma','3','10.00')]
    parts = []
    for sku, name, kg, reference in specifications:
        product = call('/products', {'sku':'DEMO-LAMB-'+sku,'name':name+' (DEMO)','type':'finished','base_unit':'kg'}, 'part-'+sku,201)
        parts.append({'product':product,'quantity':kg,'reference':reference})
    results, roots = {}, {}
    for version, method in enumerate(['quantity','value'],start=1):
        recipe = call('/recipes', {'code':'DEMO-LAMB-KEY','version':version,'species':'Kuzu','input_product_id':source['id'],'allocation_method':method,
            'lines':[{'product_id':x['product']['id'],'reference_eur_per_kg':x['reference']} for x in parts]}, 'recipe-'+method,201)
        receipt = call('/receipts', {'supplier_id':supplier['id'],'location_id':location,'received_at':'2026-10-24T08:00:00Z','lines':[
            {'product_id':source['id'],'external_lot_code':'DEMO-LAMB-'+method.upper(),'quantity':'25','unit_price':'11.50','total_cost':'287.50'}]}, 'receipt-'+method,201)
        root = receipt['lines'][0]['lot_id']; roots[method] = root
        cutting = call('/cuttings', {'code':'DEMO-CUT-'+method.upper(),'recipe_version_id':recipe['id']}, 'draft-'+method,201)
        result = call('/cuttings/'+cutting['id']+'/post', {
            'consumed_inputs':[{'lot_id':root,'location_id':location,'quantity':'25'}],'output_location_id':location,
            'outputs':[{'product_id':x['product']['id'],'lot_code':'DEMO-'+method.upper()+'-'+x['product']['sku'],'quantity':x['quantity']} for x in parts],
            'differences':[{'kind':'waste','quantity':'3','reason':'KURGUSAL DEMO — ölçüldüğü varsayılan normal fire; gerçek işletme onayı değildir.'}]}, 'post-'+method,200)
        if sum(Decimal(x['quantity']) for x in result['outputs']) != 22 or sum(Decimal(x['allocated_cost']) for x in result['outputs']) != Decimal('287.50'):
            raise SystemExit('Demo ağırlık/maliyet dengesi sağlanmadı')
        results[method] = {**result, 'by_product': {call('/lots/'+x['lot_id'])['product_id']:x for x in result['outputs']}}
    sold = results['quantity']['by_product'][parts[0]['product']['id']]
    sale = call('/sales', {'customer_id':buyer['id'],'lines':[{'lot_id':sold['lot_id'],'location_id':location,'quantity':'1','unit':'kg','unit_price':'25.00'}]}, 'sale',201)
    stocks = call('/stocks?lot_id='+sold['lot_id']+'&location_id='+location)['items']
    if len(stocks) != 1 or Decimal(stocks[0]['quantity']) != Decimal(sold['quantity'])-1:
        raise SystemExit('Demo parça satışı stoktan tam bir kez düşmedi')
    forward = call('/lots/'+roots['quantity']+'/trace')
    backward = call('/lots/'+sold['lot_id']+'/trace?direction=backward')
    if {x['id'] for x in forward['lots']} != {roots['quantity']} | {x['lot_id'] for x in results['quantity']['outputs']}:
        raise SystemExit('Demo ileri lot ilişkileri eksik')
    if {x['id'] for x in backward['lots']} != {roots['quantity'],sold['lot_id']}:
        raise SystemExit('Demo geriye lot ilişkileri eksik')
    comparison = [{'part':x['product']['name'],'kg':x['quantity'],'fictional_reference_eur_per_kg':x['reference'],
                   'quantity_allocated_cost':results['quantity']['by_product'][x['product']['id']]['allocated_cost'],
                   'value_allocated_cost':results['value']['by_product'][x['product']['id']]['allocated_cost']} for x in parts]
    print(json.dumps({'data_note':'PDF bireysel parça ağırlığı veya referans fiyat vermez. Parça ağırlıkları, değer referansları, fire sınıfı/açıklaması ve satış fiyatı KURGUSAL DEMO verisidir.',
                      'comparison_note':'İki yöntem iki ayrı 25 kg lot üzerinde uygulanır; aynı kuzu iki kez tüketilmez.',
                      'source_lot_ids':roots,'operation_ids':{k:v['id'] for k,v in results.items()},
                      'each_input_kg':'25.000000','each_input_cost_eur':'287.500000','each_output_kg':'22.000000','each_explained_waste_kg':'3.000000',
                      'comparison':comparison,'each_allocated_total_eur':{k:v['total_cost'] for k,v in results.items()},
                      'sale_id':sale['id'],'sold_kg':sale['lines'][0]['quantity'],'sold_lot_remaining_kg':stocks[0]['quantity'],
                      'forward_lot_count':len(forward['lots']),'backward_lot_count':len(backward['lots'])}, ensure_ascii=False))


if __name__ == '__main__':
    main()
