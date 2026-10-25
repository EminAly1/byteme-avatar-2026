"""Real MySQL-only forecast persistence and operational isolation acceptance."""
import copy
import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal as D
from pathlib import Path
from uuid import uuid4
import pytest
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app import models as m, predictions
from app.config import get_settings
from app.ml_runtime import load_model
from test_core_mysql import scenario, post, dispatch_all, close_body
from test_cuttings_mysql import lamb, draft, close

pytestmark=pytest.mark.skipif(os.getenv('AVATAR_CORE_MYSQL_TEST')!='1',reason='Isolated *_test MySQL 8 required')


def production_body(s=None):
    body=dict(meat_type='beef',meat_kg='100',spice_kg='2',casing_kg='5',meat_cost_eur='970',spice_cost_eur='48',casing_cost_eur='58',
        planned_producer_profile='producer_a',package_weight_kg='1',estimated_service_eur='450')
    if s:body.update(operation_id=s['operation'],output_product_id=s['output']['id'])
    return body


def cutting_body(s,recipe,op=None):
    return dict(recipe_version_id=recipe['id'],operation_id=op['id'] if op else None,
        part_products={k:p['id'] for k,p in zip(('leg','shoulder','back','rib','mince'),s['parts'])},species='Kuzu',input_weight_kg='25')


def business_snapshot(engine):
    with engine.connect() as conn:
        return {name:sorted([repr(tuple(row)) for row in conn.execute(table.select())])
            for name,table in m.Base.metadata.tables.items() if name not in ('prediction_records','idempotency_requests')}


def test_production_frozen_forecast_actual_delta_and_no_operational_mutations(scenario,mysql_core,monkeypatch):
    s=scenario; before=business_snapshot(mysql_core);key=str(uuid4());body=production_body(s)
    forecast=post(s['client'],'/predictions/production',body,key)
    assert business_snapshot(mysql_core)==before
    assert forecast['data_origin']=='SYNTHETIC' and forecast['prediction_limitations']
    assert D(forecast['predicted_finished_quantity'])>0 and D(forecast['predicted_ekp_eur_per_unit'])>0
    pending=s['client'].get('/v1/predictions/'+forecast['id']).json()
    assert all(v['actual'] is None and v['absolute_deviation'] is None for v in pending['comparison'].values())
    assert post(s['client'],'/predictions/production',body,key)==forecast
    dispatch_all(s)
    closed=post(s['client'],f"/operations/{s['operation']}/post",close_body(s),status=200)
    assert closed['total_cost']=='1543.500000' and closed['outputs'][0]['unit_cost_display']=='18.16'
    final_business=business_snapshot(mysql_core)
    # Existing saved forecasts must never load or reinterpret the current model.
    monkeypatch.setattr(predictions,'model',lambda _: (_ for _ in ()).throw(AssertionError('must not load model')))
    result=s['client'].get('/v1/predictions/'+forecast['id']).json()
    assert result['predicted_at']==forecast['predicted_at'] and result['model_version']==forecast['model_version']
    qty=result['comparison']['predicted_finished_quantity']
    assert qty['actual']=='85.000000'
    assert D(qty['absolute_deviation'])==abs(D(qty['predicted'])-85)
    assert abs(D(qty['percentage_deviation'])-abs(D(qty['predicted'])-85)/85*100)<=D('.000001')
    assert result['comparison']['predicted_ekp_eur_per_unit']['actual']=='18.158824'
    assert result['comparison']['predicted_total_cost_eur']['actual']=='1543.500000'
    assert business_snapshot(mysql_core)==final_business
    assert post(s['client'],'/predictions/production',body,key)==forecast


@pytest.mark.parametrize('change',[
 {'meat_kg':'-1'}, {'meat_kg':'NaN'}, {'meat_kg':'Infinity'}, {'meat_kg':100}, {'material_unit':'lb'},
 {'quantity_unit':'kg'}, {'currency':'USD'}, {'actual_finished_quantity':'85'}, {'actual_total_cost_eur':'1543.50'},
 {'meat_kg':'0'}, {'planned_producer_profile':'real-company'}, {'operation_id':str(uuid4())},
])
def test_pydantic_rejects_invalid_or_leaked_inputs(core_client,change):
    payload=production_body();payload.update(change)
    response=core_client.post('/v1/predictions/production',json=payload,headers={'Idempotency-Key':str(uuid4())})
    assert response.status_code==422


def test_out_of_domain_and_failed_forecast_rolls_back(core_client,mysql_core):
    b=production_body();b['meat_kg']='999'
    result=post(core_client,'/predictions/production',b,status=422)
    assert result['error']['code']=='PREDICTION_OUT_OF_DOMAIN'
    with Session(mysql_core) as db:
        assert db.scalar(select(func.count()).select_from(m.PredictionRecord))==0
        assert db.scalar(select(func.count()).select_from(m.IdempotencyRequest))==0


@pytest.mark.parametrize('corrupt',[False,True])
def test_missing_or_corrupt_model_returns_safe_503(core_client,mysql_core,monkeypatch,tmp_path,corrupt):
    if corrupt:
        (tmp_path/'production.json').write_text('{}');(tmp_path/'production.sha256').write_text('0'*64)
    monkeypatch.setenv('AVATAR_ML_MODEL_DIR',str(tmp_path));get_settings.cache_clear();load_model.cache_clear()
    try:
        before=business_snapshot(mysql_core)
        response=post(core_client,'/predictions/production',production_body(),status=503)
        assert response['error']['code']=='MODEL_UNAVAILABLE'
        assert str(tmp_path) not in json.dumps(response)
        assert business_snapshot(mysql_core)==before
        assert core_client.get('/v1/predictions/models').status_code==503
    finally:get_settings.cache_clear();load_model.cache_clear()


def test_prediction_auth_and_model_metadata(core_client):
    assert core_client.get('/v1/predictions/models',headers={'X-API-Key':'wrong'}).status_code==401
    assert core_client.post('/v1/predictions/production',json=production_body(),headers={'Idempotency-Key':str(uuid4()),'X-API-Key':'wrong'}).status_code==401
    result=core_client.get('/v1/predictions/models')
    assert result.status_code==200
    models=result.json()['models']; assert len(models)==2
    assert all(x['data_origin']=='SYNTHETIC' and x['model_version'] and x['metrics'] for x in models)
    assert core_client.post('/v1/predictions/production',json=production_body()).status_code==422


def test_forecast_idempotency_and_replay_survives_model_removal(core_client,monkeypatch,tmp_path):
    b=production_body();key=str(uuid4());first=post(core_client,'/predictions/production',b,key)
    monkeypatch.setenv('AVATAR_ML_MODEL_DIR',str(tmp_path));get_settings.cache_clear()
    try:
        assert post(core_client,'/predictions/production',b,key)==first
        b['meat_kg']='101'
        assert post(core_client,'/predictions/production',b,key,status=409)['error']['code']=='IDEMPOTENCY_CONFLICT'
    finally:get_settings.cache_clear()


def test_simultaneous_identical_forecast_has_one_record(core_client,mysql_core):
    key=str(uuid4());b=production_body()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:post(core_client,'/predictions/production',b,key),range(2)))
    assert results[0]==results[1]
    with Session(mysql_core) as db: assert db.scalar(select(func.count()).select_from(m.PredictionRecord))==1


def test_forecast_after_dispatch_and_close_rejected(scenario):
    s=scenario;dispatch_all(s)
    assert post(s['client'],'/predictions/production',production_body(s),status=409)['error']['code']=='FORECAST_TOO_LATE'
    post(s['client'],f"/operations/{s['operation']}/post",close_body(s),status=200)
    assert post(s['client'],'/predictions/production',production_body(s),status=409)['error']['code']=='FORECAST_TOO_LATE'


def test_cutting_physical_totals_comparison_and_history(lamb,mysql_core,monkeypatch,tmp_path):
    s=lamb;recipe,op=draft(s);b=cutting_body(s,recipe,op);before=business_snapshot(mysql_core)
    forecast=post(s['client'],'/predictions/cutting',b)
    assert business_snapshot(mysql_core)==before
    assert sum(D(forecast[f'predicted_{p}_kg']) for p in b['part_products'])==D(forecast['predicted_total_weight_kg'])<=25
    assert D(forecast['predicted_total_weight_kg'])+D(forecast['predicted_difference_kg'])==25
    assert forecast['context']['recipe_version_id']==recipe['id']
    close(s,op)
    # A newly deployed model version cannot reprice/reinterpret earlier forecasts.
    from ml.data.generate import save
    from ml.training.train import train_one
    save(tmp_path/'data',seed=17)
    train_one(tmp_path/'data',tmp_path,'cutting','2026-10-25T00:00:00+00:00')
    monkeypatch.setenv('AVATAR_ML_MODEL_DIR',str(tmp_path));get_settings.cache_clear()
    try:
        assert predictions.model('cutting').document['metadata']['model_version']!=forecast['model_version']
        final=s['client'].get('/v1/predictions/'+forecast['id']).json()
        assert final['model_version']==forecast['model_version'] and final['predicted_leg_kg']==forecast['predicted_leg_kg']
        assert final['comparison']['predicted_leg_kg']['actual']=='6.000000'
        assert final['comparison']['predicted_total_weight_kg']['actual']=='22.000000'
        assert final['comparison']['predicted_difference_kg']['actual']=='3.000000'
    finally:get_settings.cache_clear();load_model.cache_clear()
    assert post(s['client'],'/predictions/cutting',b,status=409)['error']['code']=='FORECAST_TOO_LATE'


@pytest.mark.parametrize('case',['missing_part','duplicate','wrong_recipe_product','wrong_unit','actual_input','species','recipe_operation'])
def test_cutting_invalid_configuration_rejected(lamb,case):
    s=lamb;recipe,op=draft(s);b=cutting_body(s,recipe,op)
    if case=='missing_part':del b['part_products']['leg']
    elif case=='duplicate':b['part_products']['leg']=b['part_products']['back']
    elif case=='wrong_recipe_product':b['part_products']['leg']=s['source']['id']
    elif case=='wrong_unit':b['unit']='lb'
    elif case=='actual_input':b['actual_difference_kg']='3'
    elif case=='species':b['species']='beef'
    else:
        other,_=draft(s,'value',2);b['recipe_version_id']=other['id']
    post(s['client'],'/predictions/cutting',b,status=422)


def test_forecast_does_not_change_recall_stock_or_sale_decisions(lamb,mysql_core):
    s=lamb;recipe,op=draft(s)
    post(s['client'],'/recalls',{'source_lot_id':s['lot'],'reason':'Test kalite blokajı'})
    before=business_snapshot(mysql_core)
    post(s['client'],'/predictions/cutting',cutting_body(s,recipe,op))
    assert business_snapshot(mysql_core)==before
    assert close(s,op,status=409)['error']['code']=='LOT_BLOCKED'
    assert business_snapshot(mysql_core)==before


def test_zero_actual_percentage_is_null_and_unmatched_actual_stays_null(core_client,mysql_core):
    forecast=post(core_client,'/predictions/production',production_body())
    result=core_client.get('/v1/predictions/'+forecast['id']).json()
    assert result['actual_unavailable_reason'] and all(v['actual'] is None for v in result['comparison'].values())
    with Session(mysql_core) as db:
        row=db.get(m.PredictionRecord,forecast['id'])
        from unittest.mock import patch
        with patch('app.predictions.actual_values',return_value=({'predicted_total_cost_eur':D('0')},None)):
            response=predictions.detail(db,row)
            assert response['comparison']['predicted_total_cost_eur']['percentage_deviation'] is None
