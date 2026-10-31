"""Real MySQL master-data/FK safety; only the shared guarded *_core_test fixture."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from uuid import uuid4
import pytest
from sqlalchemy import event, select
from sqlalchemy.orm import Session
from app import models as m, master_data
from test_core_mysql import post, assert_ledger
from test_transfers_returns_mysql import snapshot


def create(c, kind):
    bodies = {'products': {'sku':str(uuid4()),'name':'TEST ürün','type':'raw','base_unit':'kg'},
              'parties': {'name':'TEST firma','roles':['supplier'],'contact':'test@example.invalid'},
              'locations': {'name':'TEST depo'}}
    return post(c,'/'+kind,bodies[kind])


def mutate(c, method, path, body, key=None):
    return c.request(method,'/v1'+path,json=body,headers={'Idempotency-Key':key or str(uuid4())})


@pytest.mark.parametrize('kind',['products','parties','locations'])
def test_real_detail_patch_and_free_delete_replay(core_client, mysql_core, kind):
    c=core_client; row=create(c,kind); path='/'+kind+'/'+row['id']
    before=snapshot(mysql_core); assert c.get('/v1'+path).json()==row; assert snapshot(mysql_core)==before
    key=str(uuid4()); body={'name':'TEST güncel ad'}
    if kind=='parties': body['contact']='yenilenmis@example.invalid'
    r=mutate(c,'PATCH',path,body,key); assert r.status_code==200,r.text
    assert r.json()['name']=='TEST güncel ad' and r.json()['created_at']==row['created_at']
    assert mutate(c,'PATCH',path,body,key).json()==r.json()
    assert mutate(c,'PATCH',path,{'name':'başka'},key).status_code==409
    assert c.get('/v1'+path).json()==r.json()
    key=str(uuid4()); deleted=mutate(c,'DELETE',path,{},key)
    assert deleted.status_code==200 and deleted.json()=={'id':row['id'],'deleted':True}
    before=snapshot(mysql_core)
    assert mutate(c,'DELETE',path,{},key).json()==deleted.json() and snapshot(mysql_core)==before
    assert c.get('/v1'+path).status_code==404


@pytest.mark.parametrize('kind,field,value',[('products','base_unit','unit'),('products','type','finished'),('products','package_weight_kg','2'),('products','sku','NEW'),('parties','roles',['customer']),('locations','kind','quarantine'),('locations','party_id',str(uuid4()))])
def test_structural_edits_rejected_without_writes(core_client,mysql_core,kind,field,value):
    row=create(core_client,kind); before=snapshot(mysql_core)
    assert mutate(core_client,'PATCH','/'+kind+'/'+row['id'],{'name':'TEST ad',field:value}).status_code==422
    assert snapshot(mysql_core)==before


def test_referenced_product_supplier_location_cannot_be_deleted_but_names_can_change(core_client,mysql_core):
    c=core_client; product=create(c,'products'); supplier=create(c,'parties'); location=create(c,'locations')
    receipt=post(c,'/receipts',{'supplier_id':supplier['id'],'location_id':location['id'],'lines':[{'product_id':product['id'],'external_lot_code':'TEST-MASTER','quantity':'2.5','total_cost':'10'}]})
    before=snapshot(mysql_core)
    for kind,row in [('products',product),('parties',supplier),('locations',location)]:
        key=str(uuid4());r=mutate(c,'DELETE','/'+kind+'/'+row['id'],{},key)
        assert r.status_code==409 and r.json()['error']['code']=='MASTER_IN_USE'
        assert snapshot(mysql_core)==before
    r=mutate(c,'PATCH','/products/'+product['id'],{'name':'TEST yeni ad'}); assert r.status_code==200
    before=snapshot(mysql_core)
    for _ in range(2):
        detail=c.get('/v1/receipts/'+receipt['id']).json()
        assert detail['total_cost']=='10.00' and detail['lines'][0]['product_name']=='TEST yeni ad'
        assert detail['lines'][0]['quantity']=='2.500000' and detail['lines'][0]['unit']=='kg'
    assert snapshot(mysql_core)==before; assert_ledger(mysql_core)


def test_json_draft_reference_and_location_owner_are_protected(core_client,mysql_core):
    c=core_client; product=create(c,'products')
    with Session(mysql_core) as db,db.begin():
        db.add(m.Operation(code='TEST-JSON',kind='rework',allocation_snapshot={'output_product_ids':[product['id']]}))
    assert mutate(c,'DELETE','/products/'+product['id'],{}).status_code==409
    producer=post(c,'/parties',{'name':'TEST üretici','roles':['producer']})
    post(c,'/locations',{'name':'TEST üreticide','kind':'external_producer','party_id':producer['id']})
    assert mutate(c,'DELETE','/parties/'+producer['id'],{}).status_code==409


def test_contact_only_patch_is_partial_and_auth_and_invalid_names_are_rejected(core_client,mysql_core):
    c=core_client;row=create(c,'parties');path='/parties/'+row['id']
    assert mutate(c,'PATCH',path,{'contact':None}).json()['name']==row['name']
    before=snapshot(mysql_core)
    for body in [{},{'name':None},{'name':'   '},{'name':'x'*201}]:assert mutate(c,'PATCH',path,body).status_code==422
    assert c.patch('/v1'+path,json={'name':'bad'},headers={'X-API-Key':'invalid','Idempotency-Key':str(uuid4())}).status_code==401
    assert snapshot(mysql_core)==before


def test_delete_and_concurrent_receipt_use_real_fk_lock_without_orphans(core_client,mysql_core,monkeypatch):
    c=core_client;product=create(c,'products');supplier=create(c,'parties');location=create(c,'locations')
    locked=Event();release=Event();inserting=Event();original=master_data.referenced
    def held(db,model,record_id):
        if model is m.Product and str(record_id)==product['id']:
            locked.set();assert release.wait(8)
        return original(db,model,record_id)
    monkeypatch.setattr(master_data,'referenced',held)
    def observe(conn,cursor,statement,*args):
        if statement.lstrip().upper().startswith('INSERT INTO LOTS'):inserting.set()
    event.listen(mysql_core,'before_cursor_execute',observe)
    try:
        with ThreadPoolExecutor(2) as pool:
            deletion=pool.submit(mutate,c,'DELETE','/products/'+product['id'],{})
            assert locked.wait(5)
            receipt=pool.submit(c.post,'/v1/receipts',json={'supplier_id':supplier['id'],'location_id':location['id'],'lines':[{'product_id':product['id'],'external_lot_code':'TEST-RACE','quantity':'1','total_cost':'1'}]},headers={'Idempotency-Key':str(uuid4())})
            try:assert inserting.wait(5)
            finally:release.set()
            assert deletion.result().status_code==200
            assert receipt.result().status_code==409
    finally:
        release.set();event.remove(mysql_core,'before_cursor_execute',observe)
    with Session(mysql_core) as db:
        assert db.scalar(select(m.Receipt.id)) is None and db.scalar(select(m.Lot.id)) is None
        assert db.scalar(select(m.StockMovement.id)) is None
    assert_ledger(mysql_core)


def test_json_reference_writer_lock_prevents_concurrent_master_delete(core_client,mysql_core,monkeypatch):
    from app import services
    product=create(core_client,'products');held=Event();release=Event();attempt=Event();original=master_data.locked
    def observed(db,model,record_id):
        attempt.set();return original(db,model,record_id)
    monkeypatch.setattr(master_data,'locked',observed)
    def writer():
        with Session(mysql_core) as db,db.begin():
            services.get(db,m.Product,product['id'],lock=True);held.set();assert release.wait(8)
            db.add(m.Operation(code='TEST-JSON-RACE',kind='rework',allocation_snapshot={'output_product_ids':[product['id']]}))
    with ThreadPoolExecutor(2) as pool:
        creation=pool.submit(writer);assert held.wait(5)
        deletion=pool.submit(mutate,core_client,'DELETE','/products/'+product['id'],{})
        try:assert attempt.wait(5)
        finally:release.set()
        creation.result();assert deletion.result().status_code==409
    assert core_client.get('/v1/products/'+product['id']).status_code==200
