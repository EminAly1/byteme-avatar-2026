"""Real MySQL: wide supported domain, field errors, old snapshots and isolation."""
import copy
import os
from decimal import Decimal as D
from pathlib import Path
from uuid import uuid4
import pytest
from sqlalchemy.orm import Session
from app import models as m
from app.config import get_settings
from app.ml_runtime import load_model
from test_core_mysql import scenario, post, dispatch_all, close_body
from test_cuttings_mysql import lamb, draft
from test_predictions_mysql import production_body, cutting_body, business_snapshot
from test_transfers_returns_mysql import snapshot

pytestmark=pytest.mark.skipif(os.getenv('AVATAR_CORE_MYSQL_TEST')!='1',reason='Isolated *_test MySQL 8 required')
ROOT=Path(__file__).resolve().parents[1]


def scaled(weight):
    b=production_body()
    for k in ['meat_kg','spice_kg','casing_kg','meat_cost_eur','spice_cost_eur','casing_cost_eur','estimated_service_eur']:
        b[k]=str(D(b[k])*D(weight)/100)
    return b


@pytest.mark.parametrize('weight',['5','25','100','300'])
def test_supported_production_batches_preserve_every_operational_table(core_client,mysql_core,weight):
    before=business_snapshot(mysql_core); body=scaled(weight); key=str(uuid4())
    result=post(core_client,'/predictions/production',body,key)
    assert result['model_version'].startswith('production-ridge-v2-') and result['dataset_version']=='synthetic-v2'
    assert 0<D(result['predicted_finished_quantity'])<=sum(D(body[k]) for k in ['meat_kg','spice_kg','casing_kg'])
    assert D(result['predicted_total_cost_eur'])>0 and D(result['predicted_ekp_eur_per_unit'])>0
    assert business_snapshot(mysql_core)==before
    frozen=snapshot(mysql_core)
    assert post(core_client,'/predictions/production',body,key)==result
    assert snapshot(mysql_core)==frozen
    saved=core_client.get('/v1/predictions/'+result['id']).json()
    assert saved['model_version']==result['model_version']
    assert all(c['actual'] is None for c in saved['comparison'].values())
    assert business_snapshot(mysql_core)==before


@pytest.mark.parametrize('weight',['5','25','80'])
def test_cutting_positive_parts_exact_decimal_balance_and_no_ledger_write(lamb,mysql_core,weight):
    s=lamb; recipe,op=draft(s); body=cutting_body(s,recipe,op);body['input_weight_kg']=weight
    before=business_snapshot(mysql_core)
    result=post(s['client'],'/predictions/cutting',body)
    parts=[D(result['predicted_'+part+'_kg']) for part in body['part_products']]
    assert all(p>0 for p in parts) and sum(parts)==D(result['predicted_total_weight_kg'])<=D(weight)
    assert sum(parts)+D(result['predicted_difference_kg'])==D(weight)
    assert business_snapshot(mysql_core)==before


@pytest.mark.parametrize('field,value,low,high',[
    ('meat_kg','4.999999',5,300),('meat_kg','300.000001',5,300),
    ('spice_kg','2',.25,1.),('casing_kg','5',.5,2.),
    ('package_weight_kg','2.000001',.25,2),('estimated_service_eur','2400.000001',0,2400),
])
def test_domain_errors_explain_exact_field_and_current_allowed_bounds(core_client,mysql_core,field,value,low,high):
    body=scaled('25'); body[field]=value;before=snapshot(mysql_core)
    result=post(core_client,'/predictions/production',body,status=422)
    assert result['error']['code']=='PREDICTION_OUT_OF_DOMAIN'
    row=next(r for r in result['error']['details']['fields'] if r['field']==field)
    assert row['minimum']==low and row['maximum']==high and row['message']
    assert snapshot(mysql_core)==before


@pytest.mark.parametrize('change',[{'meat_kg':'0'},{'meat_cost_eur':'-1'},{'package_weight_kg':'0'},
    {'casing_kg':'NaN'},{'spice_kg':'Infinity'},{'meat_kg':'-Infinity'}])
def test_nonphysical_inputs_reject_without_partial_record(core_client,mysql_core,change):
    before=snapshot(mysql_core)
    post(core_client,'/predictions/production',{**scaled('25'),**change},status=422)
    assert snapshot(mysql_core)==before


def test_v1_saved_prediction_survives_v2_deployment_and_missing_artifact(core_client,mysql_core,monkeypatch,tmp_path):
    body=production_body();key=str(uuid4())
    monkeypatch.setenv('AVATAR_ML_MODEL_DIR',str(ROOT/'ml/evaluation/v1'));get_settings.cache_clear();load_model.cache_clear()
    try:
        old=post(core_client,'/predictions/production',body,key)
        assert '-ridge-v1-' in old['model_version']
        monkeypatch.setenv('AVATAR_ML_MODEL_DIR',str(ROOT/'ml/models'));get_settings.cache_clear();load_model.cache_clear()
        before=business_snapshot(mysql_core)
        new=post(core_client,'/predictions/production',body)
        assert '-ridge-v2-' in new['model_version'] and new['model_version']!=old['model_version']
        for directory in [ROOT/'ml/models',tmp_path]:
            monkeypatch.setenv('AVATAR_ML_MODEL_DIR',str(directory));get_settings.cache_clear();load_model.cache_clear()
            read=core_client.get('/v1/predictions/'+old['id']).json()
            assert read['model_version']==old['model_version'] and read['predicted_finished_quantity']==old['predicted_finished_quantity']
            assert post(core_client,'/predictions/production',body,key)==old
        assert business_snapshot(mysql_core)==before
    finally:get_settings.cache_clear();load_model.cache_clear()


def test_metadata_matches_loaded_models_and_boundaries(core_client,mysql_core):
    before=snapshot(mysql_core);response=core_client.get('/v1/predictions/models')
    assert response.status_code==200
    for info in response.json()['models']:
        loaded=load_model(str(ROOT/'ml/models'),info['kind'])
        assert info['feature_schema']==loaded.document['feature_schema']
        assert info['input_constraints']==loaded.document.get('input_constraints',[])
        assert info['example_inputs'] and info['metrics']['splits']=={'train':1800,'validation':600,'test':600}
    assert snapshot(mysql_core)==before
