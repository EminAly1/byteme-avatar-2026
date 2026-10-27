"""Rework acceptance over real MySQL, existing production lineage and cost pools."""
import copy
import os
from datetime import datetime, timezone, timedelta
from decimal import Decimal as D
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from threading import Event

import pytest
from sqlalchemy import select, func, event
from sqlalchemy.orm import Session

from app import models as m, services
from app.errors import DomainError
from app.commands import get_engine as command_engine
from test_core_mysql import post, assert_ledger
from test_transfers_returns_mysql import snapshot, ordered_race, concurrent

pytestmark=pytest.mark.skipif(os.getenv('AVATAR_CORE_MYSQL_TEST')!='1',reason='Isolated *_test MySQL required')


@pytest.fixture
def produced(core_client, request):
    c=core_client
    options=getattr(request,'param',{})
    source_quantity=options.get('quantity','20');source_cost=options.get('cost','200.00')
    supplier=post(c,'/parties',{'name':'KURGUSAL rework tedarikçi','roles':['supplier']})
    producer=post(c,'/parties',{'name':'KURGUSAL üretici','roles':['producer']})
    customer=post(c,'/parties',{'name':'KURGUSAL müşteri','roles':['customer'],'contact':'rework@example.invalid'})
    w=post(c,'/locations',{'name':'KURGUSAL rework deposu'})['id']
    q=post(c,'/locations',{'name':'KURGUSAL rework karantina','kind':'quarantine'})['id']
    ext=post(c,'/locations',{'name':'KURGUSAL dış üretici','kind':'external_producer','party_id':producer['id']})['id']
    raw=post(c,'/products',{'sku':'RW-RAW','name':'KURGUSAL hammadde','type':'raw','base_unit':'kg'})['id']
    products=[post(c,'/products',{'sku':'RW-'+str(i),'name':'KURGUSAL mamul '+str(i),'type':options.get('source_type','finished') if i==0 else 'finished','base_unit':'kg'})['id'] for i in range(3)]
    receipt=post(c,'/receipts',{'supplier_id':supplier['id'],'location_id':w,'lines':[
        {'product_id':raw,'external_lot_code':'KURGUSAL-RW-RAW','quantity':source_quantity,'total_cost':source_cost}]})
    origin=receipt['lines'][0]['lot_id'];op=post(c,'/operations',{'code':'KURGUSAL-RW-PRODUCTION','producer_id':producer['id']})
    post(c,'/operations/'+op['id']+'/dispatch',{'from_location_id':w,'to_location_id':ext,'lines':[{'lot_id':origin,'quantity':source_quantity}]},status=200)
    expiry=(datetime.now(timezone.utc).date()+timedelta(days=30)).isoformat()
    result=post(c,'/operations/'+op['id']+'/post',{'consumed_inputs':[{'lot_id':origin,'location_id':ext,'quantity':source_quantity}],
        'output_location_id':w,'outputs':[{'product_id':products[0],'lot_code':'KURGUSAL-RW-SOURCE','quantity':source_quantity,'unit':'kg','expires_at':expiry}],
        'service_costs':[],'loss_quantity':'0'},status=200)
    return {'client':c,'w':w,'q':q,'ext':ext,'supplier':supplier['id'],'customer':customer['id'],
            'raw':raw,'products':products,'lot':result['outputs'][0]['lot_id'],'origin':origin,'expiry':expiry,'production_operation':op['id']}


def plan(s,quantity='10',products=None):
    return {'code':'KURGUSAL-RW-'+str(uuid4()),'source_lot_id':s['lot'],'source_location_id':s['w'],
            'input_quantity':quantity,'reason':'KURGUSAL yeniden işleme','output_product_ids':products or [s['products'][1]],
            'service_costs':[{'amount':'999.00'}]}


def closing(s,quantity='9.5',service='15.00'):
    return {'output_location_id':s['w'],'outputs':[{'product_id':s['products'][1],'lot_code':'KURGUSAL-RW-OUTPUT','quantity':quantity,'unit':'kg'}],
            'differences':[{'kind':'other_loss','quantity':'0.5','reason':'KURGUSAL ölçülen işleme kaybı'}],
            'service_costs':[{'amount':service,'invoice_reference':'KURGUSAL-RW-SERVICE'}]}


def make(s,body=None):return post(s['client'],'/reworks',body or plan(s))
def finish(s,op,body=None,key=None,status=200):return post(s['client'],'/reworks/'+op['id']+'/post',body or closing(s),key,status)
def quantity(s,lot,location=None):
    rows=s['client'].get('/v1/stocks',params={'lot_id':lot,'location_id':location or s['w']}).json()['items']
    return D(rows[0]['quantity']) if rows else D(0)

def call(s,path,body,key=None):return s['client'].post('/v1'+path,json=body,headers={'Idempotency-Key':key or str(uuid4())})


def test_draft_has_no_inventory_or_financial_effect_and_uses_existing_tables(produced,mysql_core):
    s=produced;before=snapshot(mysql_core);body=plan(s);key=str(uuid4());op=post(s['client'],'/reworks',body,key)
    after=snapshot(mysql_core)
    assert all(after[name]==before[name] for name in before if name not in ['operations','idempotency_requests'])
    assert op['kind']=='rework' and op['status']=='draft' and op['inputs']==op['outputs']==[]
    assert op['total_cost']=='0.000000' and op['allocation_snapshot']['plan']['reason']==body['reason']
    assert post(s['client'],'/reworks',body,key)==op
    assert s['client'].get('/v1/reworks/'+op['id']).json()==op
    assert s['client'].get('/v1/reworks').json()['items'][0]['id']==op['id']
    body['input_quantity']='9';assert post(s['client'],'/reworks',body,key,409)['error']['code']=='IDEMPOTENCY_CONFLICT'


def test_10_to_9_point_5_plus_point_5_with_exact_100_plus_15_and_real_fk(produced,mysql_core):
    s=produced;op=make(s);result=finish(s,op);out=result['outputs'][0];out_id=out['lot_id']
    assert result['total_material_cost']=='100.000000' and result['total_service_cost']=='15.000000'
    assert result['total_cost']=='115.000000' and out['allocated_cost']=='115.000000'
    assert result['loss_quantity']=='0.500000' and result['differences'][0]['reason'].startswith('KURGUSAL')
    assert out['expires_at']==s['expiry'] and quantity(s,s['lot'])==10 and quantity(s,out_id)==D('9.5')
    with Session(mysql_core) as db:
        source=db.get(m.Lot,s['lot']);assert (source.original_quantity,source.total_cost,source.consumed_quantity,source.consumed_cost)==(20,200,10,100)
        assert db.get(m.Lot,out_id).total_cost==115
        link=db.scalar(select(m.LotLink).where(m.LotLink.input_id==result['inputs'][0]['id']))
        assert link.output_id==out['id'] and link.attributed_input_quantity==10
        assert db.scalar(select(func.sum(m.StockMovement.quantity)).where(m.StockMovement.operation_id==op['id']))==D('-.5')
    backward=s['client'].get('/v1/lots/'+out_id+'/trace?direction=backward').json()
    forward=s['client'].get('/v1/lots/'+s['origin']+'/trace').json()
    assert {s['origin'],s['lot'],out_id}<={row['id'] for row in backward['lots']}
    assert {s['lot'],out_id}<={row['id'] for row in forward['lots']}
    assert len(backward['edges'])==2 and not backward['cycle_detected']
    assert_ledger(mysql_core)


@pytest.mark.parametrize('value',['0','-1',10.0])
def test_invalid_draft_quantities(produced,mysql_core,value):
    s=produced;body=plan(s);body['input_quantity']=value;before=snapshot(mysql_core)
    post(s['client'],'/reworks',body,status=422);assert snapshot(mysql_core)==before


@pytest.mark.parametrize('case',['no_reason','duplicate_product','unknown_product','too_much','raw','purchased_finished','quarantine','external','blocked','expired','package','ledger_mismatch'])
def test_draft_source_and_plan_gates(produced,mysql_core,case):
    s=produced;body=plan(s);status=422
    if case=='no_reason':body['reason']=''
    if case=='duplicate_product':body['output_product_ids']*=2
    if case=='unknown_product':body['output_product_ids']=[str(uuid4())];status=404
    if case=='too_much':body['input_quantity']='21';status=409
    if case=='raw':body['source_lot_id']=s['origin']
    if case=='quarantine':body['source_location_id']=s['q'];status=409
    if case=='external':body['source_location_id']=s['ext']
    if case in ['blocked','expired','package','ledger_mismatch']:
        with Session(mysql_core) as db,db.begin():
            lot=db.get(m.Lot,s['lot'])
            if case=='blocked':lot.blocked=True;status=409
            elif case=='expired':lot.expires_at=datetime.now(timezone.utc).date()-timedelta(days=1);status=409
            elif case=='ledger_mismatch':lot.total_cost=D('201');status=409
            else:
                product=db.get(m.Product,lot.product_id);product.base_unit='package';product.package_weight_kg=D(1)
    if case=='purchased_finished':
        receipt=post(s['client'],'/receipts',{'supplier_id':s['supplier'],'location_id':s['w'],'lines':[
            {'product_id':s['products'][0],'external_lot_code':'KURGUSAL-NOT-PRODUCED','quantity':'20','total_cost':'200'}]})
        body['source_lot_id']=receipt['lines'][0]['lot_id'];status=409
    before=snapshot(mysql_core);post(s['client'],'/reworks',body,status=status);assert snapshot(mysql_core)==before


@pytest.mark.parametrize('case',['unexplained','empty_reason','zero','negative','wrong_product','wrong_destination','service_missing','service_reference','extended_expiry','past_expiry','source_override'])
def test_bad_post_has_no_side_effect(produced,mysql_core,case):
    s=produced;op=make(s);body=closing(s)
    if case=='unexplained':body['differences']=[]
    if case=='empty_reason':body['differences'][0]['reason']=''
    if case=='zero':body['outputs'][0]['quantity']='0'
    if case=='negative':body['outputs'][0]['quantity']='-1'
    if case=='wrong_product':body['outputs'][0]['product_id']=s['products'][2]
    if case=='wrong_destination':body['output_location_id']=s['q']
    if case=='service_missing':del body['service_costs']
    if case=='service_reference':body['service_costs']=[{'amount':'15'}]
    if case=='extended_expiry':body['outputs'][0]['expires_at']=(datetime.fromisoformat(s['expiry']).date()+timedelta(days=1)).isoformat()
    if case=='past_expiry':body['outputs'][0]['expires_at']='2020-01-01'
    if case=='source_override':body['source_lot_id']=s['origin']
    before=snapshot(mysql_core);finish(s,op,body,status=422);assert snapshot(mysql_core)==before


@pytest.mark.parametrize('gate',['blocked','expired','insufficient','quarantine'])
def test_post_rechecks_source_after_draft(produced,mysql_core,gate):
    s=produced;body=plan(s)
    if gate=='quarantine':
        # A valid stored proposal cannot become an approval to consume recovery stock.
        op=make(s)
        with Session(mysql_core) as db,db.begin():
            row=db.get(m.Operation,op['id']);value=copy.deepcopy(row.allocation_snapshot)
            value['plan']['source_location_id']=s['q'];row.allocation_snapshot=value
    else:
        op=make(s)
        if gate=='insufficient':
            post(s['client'],'/sales',{'customer_id':s['customer'],'lines':[{'lot_id':s['lot'],'location_id':s['w'],'quantity':'15','unit_price':'20'}]})
        else:
            with Session(mysql_core) as db,db.begin():
                lot=db.get(m.Lot,s['lot'])
                if gate=='blocked':lot.blocked=True
                else:lot.expires_at=datetime.now(timezone.utc).date()-timedelta(days=1)
    before=snapshot(mysql_core);error=finish(s,op,status=409)['error']['code']
    assert error=={'blocked':'LOT_BLOCKED','expired':'LOT_EXPIRED','insufficient':'INSUFFICIENT_STOCK','quarantine':'REWORK_QUALITY_RELEASE_REQUIRED'}[gate]
    assert snapshot(mysql_core)==before


def test_expiry_unknown_is_not_invented_and_known_may_only_shorten(produced,mysql_core):
    s=produced
    with Session(mysql_core) as db,db.begin():db.get(m.Lot,s['lot']).expires_at=None
    op=make(s);body=closing(s);body['outputs'][0]['expires_at']=s['expiry']
    assert finish(s,op,body,status=422)['error']['code']=='REWORK_EXPIRY_EVIDENCE_REQUIRED'
    del body['outputs'][0]['expires_at'];result=finish(s,op,body);assert result['outputs'][0]['expires_at'] is None
    with Session(mysql_core) as db,db.begin():db.get(m.Lot,s['lot']).expires_at=datetime.fromisoformat(s['expiry']).date()
    op=make(s,plan(s,'5'));body=closing(s,'4.5');body['outputs'][0]['expires_at']=(datetime.now(timezone.utc).date()+timedelta(days=1)).isoformat()
    assert finish(s,op,body)['outputs'][0]['expires_at']==body['outputs'][0]['expires_at']


def test_multiple_outputs_deterministic_total_and_link_precision(produced,mysql_core):
    s=produced;op=make(s,plan(s,products=s['products'][1:]));body=closing(s)
    body['outputs']=[{'product_id':product,'lot_code':'KURGUSAL-MULTI-'+str(i),'quantity':amount} for i,(product,amount) in enumerate(zip(s['products'][1:],['3.1','6.4']))]
    result=finish(s,op,body)
    assert sum(D(row['allocated_cost']) for row in result['outputs'])==115
    assert sum(D(row['attributed_input_quantity']) for row in result['lot_links'])==10
    assert len({row['lot_id'] for row in result['outputs']})==2
    ordered=sorted(body['outputs'],key=lambda x:(x['product_id'],x['lot_code']))
    first_expected=(D(115)*D(ordered[0]['quantity'])/D('9.5')).quantize(D('.000001'))
    assert D(result['outputs'][0]['allocated_cost'])==first_expected
    assert_ledger(mysql_core)


def test_post_idempotency_same_operation_and_key_conflict(produced,mysql_core):
    s=produced;op=make(s);key=str(uuid4());body=closing(s);first=finish(s,op,body,key);before=snapshot(mysql_core)
    assert finish(s,op,body,key)==first and snapshot(mysql_core)==before
    changed=copy.deepcopy(body);changed['service_costs'][0]['amount']='16'
    assert finish(s,op,changed,key,409)['error']['code']=='IDEMPOTENCY_CONFLICT'
    assert finish(s,op,body,status=409)['error']['code']=='OPERATION_POSTED'


def test_late_output_error_rolls_back_consumption_and_links(produced,mysql_core,monkeypatch):
    s=produced;op=make(s);before=snapshot(mysql_core);real=services.move
    def fail_output(*args,**kwargs):
        result=real(*args,**kwargs)
        if result.type=='rework_output':raise DomainError('CONTROLLED_REWORK_FAILURE','KURGUSAL rollback')
        return result
    monkeypatch.setattr(services,'move',fail_output)
    assert finish(s,op,status=409)['error']['code']=='CONTROLLED_REWORK_FAILURE'
    assert snapshot(mysql_core)==before


@pytest.mark.parametrize('other',['rework','sale','transfer'])
def test_rework_race_cannot_overspend_source(produced,mysql_core,other):
    s=produced;one=make(s,plan(s,'15'));body=closing(s,'14.5')
    first=lambda:call(s,'/reworks/'+one['id']+'/post',body)
    if other=='rework':
        two=make(s,plan(s,'15'));second=lambda:call(s,'/reworks/'+two['id']+'/post',body)
    elif other=='sale':second=lambda:call(s,'/sales',{'customer_id':s['customer'],'lines':[{'lot_id':s['lot'],'location_id':s['w'],'quantity':'15','unit_price':'20'}]})
    else:
        other_w=post(s['client'],'/locations',{'name':'KURGUSAL diğer depo'})['id']
        second=lambda:call(s,'/transfers',{'from_location_id':s['w'],'to_location_id':other_w,'lot_id':s['lot'],'quantity':'15','unit':'kg','reason':'KURGUSAL yarış'})
    results=concurrent([first,second]);assert sum(r.status_code in (200,201) for r in results)==1 and sum(r.status_code==409 for r in results)==1
    assert quantity(s,s['lot'])==5;assert_ledger(mysql_core)


@pytest.mark.parametrize('first',['rework','recall'])
def test_ancestor_recall_rework_both_lock_orders(produced,mysql_core,monkeypatch,first):
    s=produced;op=make(s)
    actions={'rework':lambda:call(s,'/reworks/'+op['id']+'/post',closing(s)),
             'recall':lambda:call(s,'/recalls',{'source_lot_id':s['origin'],'reason':'KURGUSAL ata recall'})}
    a,b=ordered_race(monkeypatch,actions[first],actions['recall' if first=='rework' else 'rework'])
    assert a.status_code==(200 if first=='rework' else 201) and b.status_code==(201 if first=='rework' else 409)
    report=(b if first=='rework' else a).json()['report']
    if first=='rework':
        out=a.json()['outputs'][0]['lot_id'];assert out in {row['id'] for row in report['lots']}
        assert all(row['blocked'] and row['available_quantity']=='0.000000' for row in report['stocks'])
    else:assert b.json()['error']['code']=='LOT_BLOCKED'
    assert_ledger(mysql_core)


def test_rework_of_rework_multistage_trace_and_output_sale(produced,mysql_core):
    s=produced;one=finish(s,make(s));child=one['outputs'][0]['lot_id']
    p=plan(s,'5');p['source_lot_id']=child
    two=finish(s,make(s,p),closing(s,'4.5'))
    out=two['outputs'][0]['lot_id']
    back=s['client'].get('/v1/lots/'+out+'/trace?direction=backward').json()
    assert {s['origin'],s['lot'],child,out}<={x['id'] for x in back['lots']} and len(back['operations'])==3
    sale=post(s['client'],'/sales',{'customer_id':s['customer'],'lines':[{'lot_id':out,'location_id':s['w'],'quantity':'1','unit_price':'25'}]})
    post(s['client'],'/recalls',{'source_lot_id':s['origin'],'reason':'KURGUSAL zincir recall'})
    assert post(s['client'],'/sales',{'customer_id':s['customer'],'lines':[{'lot_id':out,'location_id':s['w'],'quantity':'1','unit_price':'25'}]},status=409)['error']['code']=='LOT_BLOCKED'
    assert sale['lines'][0]['lot_id']==out


def test_sale_return_cancel_history_is_immutable_after_regular_warehouse_rework(produced,mysql_core):
    s=produced;c=s['client'];sale=post(c,'/sales',{'customer_id':s['customer'],'lines':[{'lot_id':s['lot'],'location_id':s['w'],'quantity':'2','unit_price':'25'}]})
    post(c,'/shipments',{'customer_id':s['customer'],'sale_id':sale['id'],'lines':[{'sale_line_id':sale['lines'][0]['id'],'lot_id':s['lot'],'location_id':s['w'],'quantity':'2','unit':'kg'}]})
    returned=post(c,'/returns',{'sale_id':sale['id'],'acceptance_location_id':s['q'],'reason':'KURGUSAL iade','lines':[{'sale_line_id':sale['lines'][0]['id'],'quantity':'1','unit':'kg'}]})
    unshipped=post(c,'/sales',{'customer_id':s['customer'],'lines':[{'lot_id':s['lot'],'location_id':s['w'],'quantity':'1','unit_price':'25'}]})
    cancelled=post(c,'/sales/'+unshipped['id']+'/cancel',{'acceptance_location_id':s['q'],'reason':'KURGUSAL iptal'},status=200)
    profit=c.get('/v1/sales/'+sale['id']+'/profitability').json();before=snapshot(mysql_core)
    result=finish(s,make(s));after=snapshot(mysql_core)
    for table in ['sales','sale_lines','shipments','shipment_lines','customer_returns','customer_return_lines','sale_cancellations','sale_cancellation_lines']:
        assert before[table]==after[table],table
    assert result['total_material_cost']=='100.000000' and quantity(s,s['lot'],s['q'])==2
    assert c.get('/v1/sales/'+sale['id']+'/profitability').json()==profit
    bad=plan(s,'1');bad['source_location_id']=s['q']
    assert post(c,'/reworks',bad,status=409)['error']['code']=='REWORK_QUALITY_RELEASE_REQUIRED'


def test_auth_endpoint_kind_pagination_and_explicit_actual_zero_cost(produced):
    s=produced;c=s['client'];op=make(s);body=closing(s);body['service_costs']=[]
    result=finish(s,op,body);assert result['total_service_cost']=='0.000000' and result['total_cost']=='100.000000'
    for path in ['/reworks','/reworks/'+op['id']]:assert c.get('/v1'+path,headers={'X-API-Key':'invalid'}).status_code==401
    assert c.post('/v1/reworks',json=plan(s)).status_code==422
    assert c.get('/v1/reworks/'+str(uuid4())).status_code==404
    another=make(s,plan(s,'1'));page=c.get('/v1/reworks?limit=1').json();assert page['next_cursor']
    assert c.get('/v1/reworks',params={'cursor':page['next_cursor'],'limit':1}).json()['next_cursor'] is None
    assert c.get('/v1/reworks/'+s['production_operation']).status_code==404
    production_body={'consumed_inputs':[{'lot_id':s['lot'],'location_id':s['w'],'quantity':'1'}],
                     'output_location_id':s['w'],'outputs':[{'product_id':s['products'][1],'lot_code':'BYPASS','quantity':'1','unit':'kg'}], 'loss_quantity':'0'}
    assert post(c,'/operations/'+another['id']+'/post',production_body,status=422)['error']['code']=='OPERATION_KIND'
    dispatch={'from_location_id':s['w'],'to_location_id':s['ext'],'lines':[{'lot_id':s['lot'],'quantity':'1'}]}
    assert post(c,'/operations/'+another['id']+'/dispatch',dispatch,status=422)['error']['code']=='OPERATION_KIND'


@pytest.mark.parametrize('produced',[{'source_type':'byproduct'}],indirect=True)
def test_produced_byproduct_is_eligible(produced):
    assert finish(produced,make(produced))['total_material_cost']=='100.000000'


def test_byproduct_output_requires_explanation_and_keeps_cost(produced):
    s=produced;p=post(s['client'],'/products',{'sku':'RW-BYP','name':'KURGUSAL yan ürün','type':'byproduct','base_unit':'kg'})['id']
    op=make(s,plan(s,products=[p]));body=closing(s);body['outputs'][0]['product_id']=p
    assert finish(s,op,body,status=422)['error']['code']=='BYPRODUCT_EXPLANATION'
    body['outputs'][0]['explanation']='KURGUSAL kayıtlı yan ürün';assert finish(s,op,body)['total_cost']=='115.000000'


@pytest.mark.parametrize('produced',[{'quantity':'3','cost':'100.00'}],indirect=True)
def test_prior_partial_consumption_remainder_is_preserved(produced,mysql_core):
    s=produced;sale={'customer_id':s['customer'],'lines':[{'lot_id':s['lot'],'location_id':s['w'],'quantity':'1','unit_price':'20'}]}
    prior=post(s['client'],'/sales',sale);assert prior['lines'][0]['consumed_cost']=='33.333333'
    op=make(s,plan(s,'1'));body=closing(s,'0.9');body['differences'][0]['quantity']='0.1'
    result=finish(s,op,body);assert result['total_material_cost']=='33.333334' and result['total_cost']=='48.333334'
    final=post(s['client'],'/sales',sale);assert final['lines'][0]['consumed_cost']=='33.333333'
    assert s['client'].get('/v1/sales/'+prior['id']).json()==prior
    assert D(prior['lines'][0]['consumed_cost'])+D(final['lines'][0]['consumed_cost'])+D(result['total_cost'])==115
    with Session(mysql_core) as db:assert db.get(m.Lot,s['lot']).consumed_cost==100
    assert_ledger(mysql_core)


@pytest.mark.parametrize('bad_snapshot',[None,[],{'type':'other'}, {'type':'rework_plan','schema_version':1,'plan':{}}])
def test_invalid_stored_plan_fails_closed(produced,mysql_core,bad_snapshot):
    s=produced;op=make(s)
    with Session(mysql_core) as db,db.begin():db.get(m.Operation,op['id']).allocation_snapshot=bad_snapshot
    before=snapshot(mysql_core)
    assert finish(s,op,status=409)['error']['code']=='REWORK_PLAN_INVALID'
    assert snapshot(mysql_core)==before


def test_real_1213_retries_rework_without_double_consumption(produced,mysql_core,monkeypatch):
    s=produced;op=make(s);destination=post(s['client'],'/locations',{'name':'KURGUSAL deadlock hedefi'})['id']
    body=closing(s);body['output_location_id']=destination
    held,source_held=Event(),Event();calls=[];errors=[];real=services.lock_lots
    with Session(mysql_core) as db,db.begin():
        padding=[m.Location(name='KURGUSAL bakım kilidi',kind='warehouse') for _ in range(60)]
        db.add_all(padding);db.flush();ids=[row.id for row in padding]+[destination]
    def locked(db,ids):
        result=real(db,ids);calls.append(1);source_held.set();return result
    monkeypatch.setattr(services,'lock_lots',locked)
    def maintenance():
        with Session(mysql_core) as db,db.begin():
            rows=db.scalars(select(m.Location).where(m.Location.id.in_(ids)).order_by(m.Location.id).with_for_update()).all()
            for row in rows:row.name+=' held'
            db.flush();held.set();assert source_held.wait(5)
            db.scalar(select(m.Lot).where(m.Lot.id==s['lot']).with_for_update())
    observed=command_engine()
    def capture(context):
        if getattr(context.original_exception,'args',(None,))[0]==1213:errors.append(1213)
    event.listen(observed,'handle_error',capture)
    try:
        with ThreadPoolExecutor(2) as pool:
            blocker=pool.submit(maintenance);assert held.wait(5)
            writer=pool.submit(finish,s,op,body);result=writer.result(timeout=15);blocker.result(timeout=10)
        assert errors and len(calls)==2 and result['total_cost']=='115.000000'
        assert quantity(s,s['lot'])==10 and quantity(s,result['outputs'][0]['lot_id'],destination)==D('9.5')
        with Session(mysql_core) as db:
            assert db.scalar(select(func.count()).select_from(m.OperationInput).where(m.OperationInput.operation_id==op['id']))==1
            assert db.scalar(select(func.count()).select_from(m.OperationOutput).where(m.OperationOutput.operation_id==op['id']))==1
            assert db.get(m.Lot,s['lot']).consumed_cost==100
        assert_ledger(mysql_core)
    finally:event.remove(observed,'handle_error',capture)
