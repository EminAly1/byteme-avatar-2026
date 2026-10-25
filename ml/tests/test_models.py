import copy
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
import pytest
from sklearn.feature_extraction import DictVectorizer
from sklearn.preprocessing import StandardScaler

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from ml.data.generate import generate, save
from ml.training.train import train_one, records
from backend.app.ml_runtime import load_model, ModelUnavailable, PortableModel, constrain


def test_synthetic_seed_source_physics_and_nontrivial_targets(tmp_path):
    p,c=generate(); p2,c2=generate()
    assert p.equals(p2) and c.equals(c2)
    assert not p.equals(generate(seed=17)[0])
    assert set(p.data_origin)==set(c.data_origin)=={'SYNTHETIC'}
    assert p.actual_yield_ratio.nunique()>500 and p.actual_service_factor.std()>.02
    assert p.meat_kg.nunique()>500 and c.input_weight_kg.nunique()>500
    assert (c[[f'actual_{x}_kg' for x in ('leg','shoulder','back','rib','mince')]].sum(axis=1)<=c.input_weight_kg).all()
    m=save(tmp_path); assert m['real_history_rows']==0 and not m['historical_pdf_reference_used_for_training']
    assert hashlib.sha256((tmp_path/'production.csv').read_bytes()).hexdigest()==m['dataset_hashes']['production']


@pytest.mark.parametrize('kind',['production','cutting'])
def test_chronological_disjoint_split_train_only_preprocessing_baseline_and_metadata(kind):
    report=json.loads((ROOT/'ml/evaluation/metrics.json').read_text())[kind]
    sets=[set(report['splits'][k]['record_ids']) for k in ('train','validation','test')]
    assert [len(x) for x in sets]==[360,120,120]
    assert not (sets[0]&sets[1] or sets[0]&sets[2] or sets[1]&sets[2])
    assert report['splits']['train']['last_date']<report['splits']['validation']['first_date']<report['splits']['test']['first_date']
    assert report['test_used_for_selection'] is False and report['preprocessing_fit_rows']==360
    doc=json.loads((ROOT/f'ml/models/{kind}.json').read_text())
    assert all(not n.startswith('actual_') for n in doc['feature_names'])
    import pandas as pd
    frame=pd.read_csv(ROOT/f'ml/data/{kind}.csv').iloc[:360]
    vec=DictVectorizer(sparse=False); scaler=StandardScaler().fit(vec.fit_transform(records(frame,kind)))
    assert np.allclose(scaler.mean_,doc['mean'])
    assert doc['metadata']['feature_schema_version']=='preprocess-v1'
    assert doc['metadata']['metrics']['splits']=={'train':360,'validation':120,'test':120}
    assert doc['metadata']['dataset_hash']==hashlib.sha256((ROOT/f'ml/data/{kind}.csv').read_bytes()).hexdigest()
    # Weak targets are retained in the report; aggregate comparison is not a cross-unit metric.
    target='predicted_finished_quantity' if kind=='production' else 'predicted_leg_kg'
    assert report['ridge_test'][target]['rmse']<report['baseline_test'][target]['rmse']
    assert set(report['ridge_test'])==set(report['baseline_test'])


def test_retraining_reproduces_exact_coefficients_and_artifact(tmp_path):
    report=train_one(ROOT/'ml/data',tmp_path,'production','2026-10-25T00:00:00+00:00')
    before=(tmp_path/'production.json').read_bytes()
    train_one(ROOT/'ml/data',tmp_path,'production','2026-10-25T00:00:00+00:00')
    assert (tmp_path/'production.json').read_bytes()==before
    assert report['chosen_alpha'] in [.1,1.,10.]


@pytest.mark.parametrize('weight',[18.,25.,40.])
def test_cutting_prediction_physical_constraints(weight):
    model=load_model(str(ROOT/'ml/models'),'cutting')
    out=model.predict({'species':'Kuzu','recipe_shape':'five_parts_v1','input_weight_kg':weight})
    assert out['predicted_total_weight_kg']<=weight
    assert out['predicted_difference_kg']>=0
    assert out['predicted_total_weight_kg']+out['predicted_difference_kg']==pytest.approx(weight)
    assert all(v>=0 for v in out.values())


@pytest.mark.parametrize('raw',[[float('nan'),1],[float('inf'),1],[-float('inf'),1]])
def test_nonfinite_predictions_rejected(raw):
    with pytest.raises(ModelUnavailable): constrain('production',raw)


def test_negative_ratios_and_overweight_projection():
    assert constrain('cutting',[-1,2,2,0,0])==[0,.5,.5,0,0]
    assert constrain('production',[-3,-4])==[.01,.01]


@pytest.mark.parametrize('mutate',[
 lambda d:d.update(artifact_format='pickle'),
 lambda d:d['metadata'].update(feature_schema_version='future'),
 lambda d:d['metadata'].update(data_origin='REAL'),
 lambda d:d['scale'].__setitem__(0,0),
 lambda d:d['coef'][0].__setitem__(0,float('nan')),
 lambda d:d.update(intercept=[]),
])
def test_invalid_artifact_rejected(mutate):
    d=json.loads((ROOT/'ml/models/production.json').read_text());mutate(d)
    with pytest.raises(ModelUnavailable):PortableModel(d,'production')


def test_artifact_checksum_and_missing_fail_closed(tmp_path):
    with pytest.raises(ModelUnavailable): load_model(str(tmp_path),'production')
    (tmp_path/'production.json').write_text('{}'); (tmp_path/'production.sha256').write_text('0'*64)
    with pytest.raises(ModelUnavailable): load_model(str(tmp_path),'production')


def test_production_inference_uses_learned_quantity_and_cost():
    model=load_model(str(ROOT/'ml/models'),'production')
    f=dict(meat_type='beef',meat_kg=100.,spice_kg=2.,casing_kg=5.,meat_cost_eur=970.,spice_cost_eur=48.,casing_cost_eur=58.,planned_producer_profile='producer_a',package_weight_kg=1.,estimated_service_eur=450.)
    p=model.predict(f)
    assert 0<p['predicted_finished_quantity']<=107 and p['predicted_ekp_eur_per_unit']>0
    assert p['predicted_finished_quantity']!=85
    assert p['predicted_total_cost_eur']!=1076+450  # Service multiplier is learned, not an actual-cost recalculation.
    f['planned_producer_profile']='unknown'
    with pytest.raises(ValueError):model.predict(f)
