"""Cutting acceptance against real isolated MySQL 8; no business database."""
import copy
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from decimal import Decimal as D
from threading import Barrier, Event, current_thread
from uuid import uuid4

import pytest
from sqlalchemy import event, select
from sqlalchemy.orm import Session

from app import cuttings, models as m, recalls, services
from app.database import get_engine
from app.errors import DomainError
from app.schemas import CuttingPost, RecallCreate
from test_core_mysql import post, assert_ledger
from test_sales_shipments_mysql import count

pytestmark = pytest.mark.skipif(os.getenv('AVATAR_CORE_MYSQL_TEST') != '1', reason='Isolated *_test MySQL 8 required')


@pytest.fixture
def lamb(core_client):
    c = core_client
    supplier = post(c,'/parties',{'name':'KURGUSAL kuzu tedarikçisi','roles':['supplier']})
    warehouse = post(c,'/locations',{'name':'Kesim deposu'})['id']
    source = post(c,'/products',{'sku':'LAMB','name':'Bütün kuzu','species':'Kuzu','type':'raw','base_unit':'kg'})
    # PDF does not give individual weights/references. These are fictional.
    parts = [post(c,'/products',{'sku':sku,'name':name,'type':'finished','base_unit':'kg'}) for sku,name in [('LEG','But'),('SHOULDER','Omuz'),('BACK','Sırt'),('RIB','Kaburga'),('MINCE','Kıyma')]]
    receipt_body = {'supplier_id':supplier['id'],'location_id':warehouse,'received_at':'2026-10-24T08:00:00Z','lines':[
        {'product_id':source['id'],'external_lot_code':'KUZU-TEST','quantity':'25','unit_price':'11.50','total_cost':'287.50'}]}
    receipt = post(c,'/receipts',receipt_body)
    return {'client':c,'warehouse':warehouse,'supplier':supplier,'source':source,'parts':parts,'receipt':receipt,'receipt_body':receipt_body,
            'lot':receipt['lines'][0]['lot_id'],'weights':['6','4','4','5','3'],'references':['20','14','24','12','10']}


def recipe_body(s, method='quantity', version=1):
    return {'code':'LAMB-KEY','version':version,'species':'Kuzu','input_product_id':s['source']['id'],'allocation_method':method,
            'lines':[{'product_id':p['id'],'reference_eur_per_kg':r} for p,r in zip(s['parts'],s['references'])]}


def draft(s, method='quantity', version=1):
    recipe = post(s['client'],'/recipes',recipe_body(s,method,version))
    cutting = post(s['client'],'/cuttings',{'code':'CUT-'+str(uuid4()),'recipe_version_id':recipe['id']})
    return recipe, cutting


def body(s):
    return {'consumed_inputs':[{'lot_id':s['lot'],'location_id':s['warehouse'],'quantity':'25'}], 'output_location_id':s['warehouse'],
            'outputs':[{'product_id':p['id'],'lot_code':'PART-'+p['sku'],'quantity':q} for p,q in zip(s['parts'],s['weights'])],
            'differences':[{'kind':'waste','quantity':'3','reason':'KURGUSAL test: ölçülmüş normal fire'}]}


def close(s, op, payload=None, key=None, status=200):
    return post(s['client'],f"/cuttings/{op['id']}/post",payload or body(s),key,status)


def test_receipt_25kg_at_1150_is_28750_and_persists_source_facts(lamb,mysql_core):
    s=lamb; line=s['receipt']['lines'][0]
    assert s['source']['species']=='Kuzu'
    assert line['quantity']=='25.000000' and line['unit_price']=='11.500000' and line['total_cost']=='287.500000'
    lot=s['client'].get('/v1/lots/'+s['lot']).json()
    assert lot['product_id']==s['source']['id'] and lot['supplier_id']==s['supplier']['id']
    assert lot['received_at']=='2026-10-24T08:00:00+00:00' and lot['total_cost']=='287.500000'
    with Session(mysql_core) as db:
        assert db.get(m.StockBalance,(s['lot'],s['warehouse'])).quantity==25
    wrong=copy.deepcopy(s['receipt_body']); wrong['lines'][0]['total_cost']='351.00'
    assert post(s['client'],'/receipts',wrong,status=422)['error']['code']=='RECEIPT_PRICE_MISMATCH'
    with Session(mysql_core) as db:assert count(db,m.Receipt)==1
    # An explicitly verified different invoice total remains authoritative when
    # no contradictory price is supplied. Never silently rewrite it to 287.50.
    wrong['lines'][0].pop('unit_price')
    assert post(s['client'],'/receipts',wrong)['lines'][0]['total_cost']=='351.000000'
    assert_ledger(mysql_core)


@pytest.mark.parametrize('method',['quantity','value'])
def test_cutting_weights_cost_and_all_fk_links(lamb,mysql_core,method):
    s=lamb; _,op=draft(s,method); result=close(s,op)
    assert result['kind']=='cutting' and result['producer_id'] is None and result['status']=='posted'
    assert result['total_cost']=='287.500000' and result['loss_quantity']=='3.000000'
    assert len(result['outputs'])==len(result['lot_links'])==5
    assert sum(D(x['quantity']) for x in result['outputs'])==22
    assert result['differences'][0]['kind']=='waste' and result['differences'][0]['reason'].startswith('KURGUSAL')
    assert sum(D(x['allocated_cost']) for x in result['outputs'])==D('287.50')
    assert sum(D(x['attributed_input_quantity']) for x in result['lot_links'])==25
    expected_weights={p['id']:D(q)*(D(r) if method=='value' else 1) for p,q,r in zip(s['parts'],s['weights'],s['references'])}
    for out in result['outputs']:
        lot=s['client'].get('/v1/lots/'+out['lot_id']).json()
        assert D(out['allocation_weight'])==expected_weights[lot['product_id']]
        # Each allocation differs from exact ratio by at most one micro EUR;
        # independent formula checks the business rule, not implementation calls.
        exact=D('287.50')*expected_weights[lot['product_id']]/sum(expected_weights.values())
        assert abs(D(out['allocated_cost'])-exact)<=D('0.000001')
        with Session(mysql_core) as db:
            assert db.get(m.StockBalance,(lot['id'],s['warehouse'])).quantity==D(out['quantity'])
            movement=db.scalar(select(m.StockMovement).where(m.StockMovement.lot_id==lot['id']))
            assert movement.operation_id==op['id'] and movement.type=='cutting_output'
    assert s['client'].get('/v1/cuttings/'+op['id']).json()==result
    assert_ledger(mysql_core)


@pytest.mark.parametrize('differences', [[],[{'kind':'waste','quantity':'3','reason':'  '}],[{'kind':'byproduct','quantity':'3','reason':'No product recorded'}],
    [{'kind':'waste','quantity':'2','reason':'Insufficient explanation of quantity'}], [{'kind':'other_loss','quantity':'-3','reason':'Invalid'}]])
def test_unexplained_or_invalid_difference_rejected(lamb,mysql_core,differences):
    s=lamb;_,op=draft(s);payload=body(s);payload['differences']=differences
    close(s,op,payload,status=422)
    with Session(mysql_core) as db:
        assert count(db,m.OperationInput)==count(db,m.OperationOutput)==count(db,m.OperationDifference)==0
        assert db.get(m.StockBalance,(s['lot'],s['warehouse'])).quantity==25
        assert db.get(m.Operation,op['id']).status=='draft'


def test_other_loss_and_byproduct_require_explicit_records_and_cost_policy(lamb,mysql_core):
    s=lamb
    byproduct=post(s['client'],'/products',{'sku':'BY','name':'KURGUSAL yan ürün','type':'byproduct','base_unit':'kg'})
    key=recipe_body(s,'value');key['lines'].append({'product_id':byproduct['id'],'reference_eur_per_kg':'2.00'})
    recipe=post(s['client'],'/recipes',key)
    op=post(s['client'],'/cuttings',{'code':'BY-CUT','recipe_version_id':recipe['id']})
    payload=body(s);payload['outputs'].append({'product_id':byproduct['id'],'lot_code':'BY-LOT','quantity':'2'})
    payload['differences']=[{'kind':'other_loss','quantity':'1','reason':'KURGUSAL tartım farkı'}]
    assert close(s,op,payload,status=422)['error']['code']=='BYPRODUCT_EXPLANATION'
    payload['outputs'][-1]['explanation']='KURGUSAL ölçülmüş yan ürün'
    result=close(s,op,payload)
    assert result['loss_quantity']=='1.000000' and sum(D(x['quantity']) for x in result['outputs'])==24
    assert sum(D(x['allocated_cost']) for x in result['outputs'])==D('287.50')
    bylot=next(x for x in result['outputs'] if x['explanation'])
    assert D(bylot['allocated_cost'])>0 and bylot['reference_eur_per_kg']=='2.000000'
    assert result['allocation_snapshot']['policies']['byproduct_cost']=='included_with_positive_selected_allocation_weight'
    assert_ledger(mysql_core)


def test_recipe_versions_and_snapshot_never_reprice_posted_cutting(lamb):
    s=lamb;recipe,op=draft(s,'value');original=close(s,op)
    key=recipe_body(s,'value',2);key['lines'][0]['reference_eur_per_kg']='99.00'
    newer=post(s['client'],'/recipes',key)
    post(s['client'],f"/recipes/{recipe['id']}/availability",{'available':False},status=200)
    assert s['client'].get('/v1/cuttings/'+op['id']).json()==original
    assert newer['version']==2 and original['allocation_snapshot']['version']==1
    assert post(s['client'],'/cuttings',{'code':'DISABLED','recipe_version_id':recipe['id']},status=409)['error']['code']=='RECIPE_UNAVAILABLE'
    # Duplicate version is rejected instead of mutating its old key.
    post(s['client'],'/recipes',key,status=409)


@pytest.mark.parametrize('invalid', ['zero','negative','missing','duplicate','raw_output','non_kg'])
def test_invalid_recipe_keys_are_atomic(lamb,mysql_core,invalid):
    s=lamb;key=recipe_body(s,'value')
    if invalid in ('zero','negative'):key['lines'][0]['reference_eur_per_kg']='0' if invalid=='zero' else '-1'
    elif invalid=='missing':key['lines'][0].pop('reference_eur_per_kg')
    elif invalid=='duplicate':key['lines'].append(key['lines'][0])
    elif invalid=='raw_output':key['lines'][0]['product_id']=s['source']['id']
    else:
        p=post(s['client'],'/products',{'sku':'PK','name':'Paket','base_unit':'package','type':'finished','package_weight_kg':'1'})
        key['lines'][0]['product_id']=p['id']
    post(s['client'],'/recipes',key,status=422)
    with Session(mysql_core) as db:assert count(db,m.RecipeVersion)==count(db,m.RecipeLine)==0


def test_same_key_replay_and_second_cut_cannot_consume_twice(lamb,mysql_core):
    s=lamb;recipe,op=draft(s);key=str(uuid4());payload=body(s)
    result=close(s,op,payload,key)
    assert close(s,op,payload,key)==result
    changed=copy.deepcopy(payload);changed['differences'][0]['reason']='different'
    assert close(s,op,changed,key,409)['error']['code']=='IDEMPOTENCY_CONFLICT'
    assert close(s,op,status=409)['error']['code']=='OPERATION_POSTED'
    another=post(s['client'],'/cuttings',{'code':'SECOND','recipe_version_id':recipe['id']})
    assert close(s,another,status=409)['error']['code']=='INSUFFICIENT_STOCK'
    with Session(mysql_core) as db:assert count(db,m.OperationOutput)==5 and count(db,m.StockMovement)==7
    assert_ledger(mysql_core)


def test_late_output_error_rolls_back_all_stock_cost_links_differences_and_key(lamb,mysql_core,monkeypatch):
    s=lamb;_,op=draft(s);key=str(uuid4());original=services.move
    def fail(db,lot,location,quantity,kind,*args,**kwargs):
        if kind=='cutting_output':raise DomainError('TEST_FAILURE','Injected after input consumption',503)
        return original(db,lot,location,quantity,kind,*args,**kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(services,'move',fail)
        close(s,op,key=key,status=503)
    with Session(mysql_core) as db:
        assert count(db,m.OperationInput)==count(db,m.OperationOutput)==count(db,m.LotLink)==count(db,m.OperationDifference)==0
        assert count(db,m.StockMovement)==1 and count(db,m.Lot)==1
        assert db.get(m.Lot,s['lot']).consumed_cost==0 and db.get(m.StockBalance,(s['lot'],s['warehouse'])).quantity==25
        assert db.get(m.IdempotencyRequest,(f"cuttings:{op['id']}:post",key)) is None
    close(s,op,key=key)
    assert_ledger(mysql_core)


def test_piece_sale_traces_and_source_recall_reuse_core(lamb,mysql_core):
    s=lamb;_,op=draft(s);result=close(s,op);out=result['outputs'][0]
    buyer=post(s['client'],'/parties',{'name':'KURGUSAL alıcı','roles':['customer']})
    sale_body={'customer_id':buyer['id'],'lines':[{'lot_id':out['lot_id'],'location_id':s['warehouse'],'quantity':'1','unit':'kg','unit_price':'20.00'}]}
    key=str(uuid4());sale=post(s['client'],'/sales',sale_body,key)
    assert post(s['client'],'/sales',sale_body,key)==sale
    with Session(mysql_core) as db:
        balance=db.get(m.StockBalance,(out['lot_id'],s['warehouse']))
        assert balance.quantity==D(out['quantity'])-1
        assert count(db,m.StockMovement)==8
        assert db.get(m.StockMovement,sale['lines'][0]['stock_movement_id']).quantity==-1
    trace=s['client'].get(f"/v1/lots/{s['lot']}/trace").json()
    assert {x['id'] for x in trace['lots']}=={s['lot']}|{x['lot_id'] for x in result['outputs']}
    backward=s['client'].get(f"/v1/lots/{out['lot_id']}/trace?direction=backward").json()
    assert {x['id'] for x in backward['lots']}=={s['lot'],out['lot_id']}
    recall=post(s['client'],'/recalls',{'source_lot_id':s['lot'],'reason':'KURGUSAL kuzu geri çağırma'})
    assert len(recall['report']['lots'])==6 and all(x['blocked'] for x in recall['report']['lots'])
    assert recall['report']['buyers'][0]['customer_id']==buyer['id']
    assert post(s['client'],'/sales',sale_body,status=409)['error']['code']=='LOT_BLOCKED'
    assert_ledger(mysql_core)


@pytest.mark.parametrize('winner',['recall','cutting'])
def test_cutting_recall_real_lock_race_both_orders(lamb,mysql_core,winner,monkeypatch):
    s=lamb;_,op=draft(s);payload=body(s);request={'source_lot_id':s['lot'],'reason':'KURGUSAL yarış'}
    reached=Event();api_engine=get_engine();attempts=[];original=recalls.create_recall
    def observed(db,req):
        attempts.append(1);return original(db,req)
    monkeypatch.setattr(recalls,'create_recall',observed)
    def before(conn,cursor,statement,params,context,executemany):
        if current_thread().name!='MainThread' and 'FROM lots' in statement and 'FOR UPDATE' in statement:reached.set()
    with Session(mysql_core) as locker:
        if winner=='recall':recalls.create_recall(locker,RecallCreate.model_validate(request))
        else:cuttings.post_cutting(locker,op['id'],CuttingPost.model_validate(payload))
        event.listen(api_engine,'before_cursor_execute',before)
        try:
            with ThreadPoolExecutor(1) as pool:
                future=pool.submit(close,s,op,payload,None,409) if winner=='recall' else pool.submit(post,s['client'],'/recalls',request)
                try:
                    assert reached.wait(5)
                    with pytest.raises(TimeoutError):future.result(timeout=0.15)
                finally:locker.commit()
                result=future.result(timeout=5)
        finally:event.remove(api_engine,'before_cursor_execute',before)
    with Session(mysql_core) as db:
        assert count(db,m.Recall)==1
        if winner=='recall':
            assert result['error']['code']=='LOT_BLOCKED' and count(db,m.OperationOutput)==0
            assert db.get(m.StockBalance,(s['lot'],s['warehouse'])).quantity==25
        else:
            assert len(attempts)==2 and count(db,m.RecallLot)==6
            assert all(db.scalars(select(m.Lot.blocked)))
    assert_ledger(mysql_core)


def test_two_concurrent_cuts_cannot_overspend_source(lamb,mysql_core):
    s=lamb;recipe,op=draft(s);other=post(s['client'],'/cuttings',{'code':'CONCURRENT','recipe_version_id':recipe['id']});barrier=Barrier(2)
    def call(target):
        barrier.wait(timeout=5)
        return s['client'].post(f"/v1/cuttings/{target['id']}/post",json=body(s),headers={'Idempotency-Key':str(uuid4())})
    with ThreadPoolExecutor(2) as pool:results=list(pool.map(call,[op,other]))
    assert sorted(x.status_code for x in results)==[200,409]
    with Session(mysql_core) as db:assert count(db,m.OperationOutput)==5 and count(db,m.StockMovement)==7
    assert_ledger(mysql_core)


def test_cutting_lists_auth_and_kind_boundaries(lamb):
    s=lamb;_,op=draft(s)
    assert s['client'].get('/v1/cuttings?limit=1').json()['items'][0]['id']==op['id']
    assert s['client'].get('/v1/recipes').json()['items'][0]['id']==op['recipe_version_id']
    assert s['client'].get('/v1/cuttings',headers={'X-API-Key':'wrong'}).status_code==401
    assert s['client'].post('/v1/cuttings',json={'code':'NO-KEY','recipe_version_id':op['recipe_version_id']}).status_code==422
    # Existing external production endpoint cannot close an in-house cutting.
    payload={'consumed_inputs':body(s)['consumed_inputs'],'output_location_id':s['warehouse'],'outputs':body(s)['outputs'],'loss_quantity':'3','loss_reason':'Not allowed'}
    assert post(s['client'],f"/operations/{op['id']}/post",payload,status=422)['error']['code']=='OPERATION_KIND'


@pytest.mark.parametrize('state',['blocked','expired','quarantine','wrong_product'])
def test_invalid_source_gate_under_lot_lock(lamb,mysql_core,state):
    from datetime import date,timedelta
    s=lamb;_,op=draft(s)
    with Session(mysql_core) as db,db.begin():
        lot=db.get(m.Lot,s['lot'])
        if state=='blocked':lot.blocked=True
        elif state=='expired':lot.expires_at=date.today()-timedelta(days=1)
        elif state=='quarantine':db.get(m.Location,s['warehouse']).kind='quarantine'
        else:lot.product_id=s['parts'][0]['id']
    result=close(s,op,status=409 if state in ('blocked','expired') else 422)
    assert result['error']['code'] in ('LOT_BLOCKED','LOT_EXPIRED','INVALID_LOCATION','RECIPE_INPUT_MISMATCH')
    with Session(mysql_core) as db:assert count(db,m.OperationOutput)==0 and db.get(m.Lot,s['lot']).consumed_cost==0


def test_partial_cuts_preserve_full_source_cost_and_deterministic_allocation(lamb,mysql_core):
    s=lamb;recipe,op=draft(s,'value');amounts=[]
    for index in range(2):
        if index:op=post(s['client'],'/cuttings',{'code':'PARTIAL-2','recipe_version_id':recipe['id']})
        payload=body(s);payload['consumed_inputs'][0]['quantity']='12.5';payload['differences'][0]['quantity']='1.5'
        for out in payload['outputs']:out['quantity']=str(D(out['quantity'])/2);out['lot_code']+='-'+str(index)
        result=close(s,op,payload);assert result['total_cost']=='143.750000'
        costs = {}
        for output in result['outputs']:
            lot = s['client'].get('/v1/lots/'+output['lot_id']).json()
            costs[lot['product_id']] = output['allocated_cost']
        amounts.append(costs)
    assert amounts[0]==amounts[1]
    with Session(mysql_core) as db:
        assert db.get(m.Lot,s['lot']).consumed_cost==D('287.50')
        assert db.get(m.StockBalance,(s['lot'],s['warehouse'])).quantity==0
    assert_ledger(mysql_core)


def test_recipe_and_cutting_pagination_filter_and_disabled_draft(lamb):
    s=lamb;recipe,op=draft(s)
    newer=post(s['client'],'/recipes',recipe_body(s,'value',2))
    post(s['client'],'/cuttings',{'code':'SECOND-DRAFT','recipe_version_id':newer['id']})
    for path in ['/recipes','/cuttings']:
        first=s['client'].get('/v1'+path+'?limit=1').json()
        second=s['client'].get('/v1'+path,params={'limit':1,'cursor':first['next_cursor']}).json()
        assert len(first['items'])==len(second['items'])==1 and first['items'][0]['id']!=second['items'][0]['id']
        assert second['next_cursor'] is None
    post(s['client'],f"/recipes/{recipe['id']}/availability",{'available':False},status=200)
    assert close(s,op,status=409)['error']['code']=='RECIPE_UNAVAILABLE'


def test_recipe_species_must_match_recorded_animal_type(lamb):
    payload=recipe_body(lamb);payload['species']='Sığır'
    assert post(lamb['client'],'/recipes',payload,status=422)['error']['code']=='RECIPE_SPECIES_MISMATCH'
