"""Wide-domain evidence, strict physics, immutable v1 reference and no test leakage."""
import copy
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from ml.data.generate import generate, SCHEMAS, PARTS
from ml.training.train import train_one, EXAMPLES
from backend.app.ml_runtime import load_model, PortableModel, PredictionOutOfDomain, ModelUnavailable
ROOT = Path(__file__).resolve().parents[2]


def production(weight):
    return {k: (float(v)*weight/25 if k.endswith('_eur') or k.endswith('_kg') and k != 'package_weight_kg' else float(v) if k == 'package_weight_kg' else v)
            for k,v in EXAMPLES['production'].items()}


def test_dataset_size_variety_ranges_and_independent_physics():
    p,c = generate()
    assert len(p) == len(c) == 3000
    assert p.meat_kg.min() == 5 and p.meat_kg.max() == 300
    assert c.input_weight_kg.min() == 5 and c.input_weight_kg.max() == 80
    for frame in [p.iloc[:1800],p.iloc[1800:2400],p.iloc[2400:]]:
        assert frame.meat_kg.min() == 5 and frame.meat_kg.max() == 300
        assert frame.meat_type.nunique() == 2 and frame.planned_producer_profile.nunique() == 3
        assert frame.package_weight_kg.nunique() == 5
        assert set(frame.batch_segment) == {'small','medium','large'}
    assert p.record_id.nunique() == c.record_id.nunique() == 3000
    mass = p.meat_kg+p.spice_kg+p.casing_kg
    assert np.all(p.actual_finished_quantity*p.package_weight_kg <= mass)
    parts = c[[f'actual_{x}_kg' for x in PARTS]]
    assert np.all(parts.to_numpy() > 0)
    assert np.allclose(parts.sum(axis=1)+c.actual_difference_kg, c.input_weight_kg)
    assert np.all(c.actual_difference_kg > 0)


@pytest.mark.parametrize('weight',[5.,25.,100.,300.])
def test_production_new_domain_and_former_25kg_rejection(weight):
    new = load_model(str(ROOT/'ml/models'),'production')
    f = production(weight); value = new.predict(f)
    assert 0 < value['predicted_finished_quantity']*f['package_weight_kg'] <= f['meat_kg']+f['spice_kg']+f['casing_kg']
    assert value['predicted_ekp_eur_per_unit'] > 0
    old = load_model(str(ROOT/'ml/evaluation/v1'),'production')
    if weight in [5.,25.,300.]:
        with pytest.raises(PredictionOutOfDomain): old.predict(f)


@pytest.mark.parametrize('weight',[5.,18.,25.,40.,80.])
def test_cutting_supported_edges_positive_parts_and_balance(weight):
    result = load_model(str(ROOT/'ml/models'),'cutting').predict({'species':'Kuzu','recipe_shape':'five_parts_v1','input_weight_kg':weight})
    assert all(result[f'predicted_{p}_kg'] > 0 for p in PARTS)
    assert result['predicted_total_weight_kg'] <= weight
    assert result['predicted_total_weight_kg']+result['predicted_difference_kg'] == pytest.approx(weight)


@pytest.mark.parametrize('field,value',[('meat_kg',4.999999),('meat_kg',300.000001),('package_weight_kg',0),('spice_kg',11.),('casing_kg',20.),('meat_cost_eur',6001.),('meat_kg',float('nan')),('meat_kg',float('inf'))])
def test_invalid_inputs_rejected_with_field_and_bounds_not_clipped(field,value):
    model = load_model(str(ROOT/'ml/models'),'production')
    f = production(25.); f[field] = value
    with pytest.raises(PredictionOutOfDomain) as failure: model.predict(f)
    assert any(row['field'] == field and 'minimum' in row and 'maximum' in row for row in failure.value.fields)


@pytest.mark.parametrize('kind',['production','cutting'])
def test_v2_refuses_physical_model_failure_instead_of_silent_projection(kind):
    d = json.loads((ROOT/f'ml/models/{kind}.json').read_text())
    d['intercept'][0] = -100.
    model = PortableModel(d,kind)
    f = production(25.) if kind == 'production' else dict(species='Kuzu',input_weight_kg=25.,recipe_shape='five_parts_v1')
    with pytest.raises(ModelUnavailable): model.predict(f)


def test_test_targets_cannot_change_training_or_validation_choice(tmp_path):
    data = tmp_path/'data'; data.mkdir()
    for name in ['production.csv','cutting.csv','manifest.json']:
        (data/name).write_bytes((ROOT/'ml/data'/name).read_bytes())
    original = json.loads((ROOT/'ml/models/production.json').read_text())
    frame = pd.read_csv(data/'production.csv')
    # Change only TEST outcomes. Features, train and validation are byte values
    # from the same CSV; the changed dataset hash must not alter fit/selection.
    frame.loc[2400:,'actual_yield_ratio'] *= .95
    frame.loc[2400:,'actual_finished_quantity'] *= .95
    frame.loc[2400:,'actual_ekp_eur_per_unit'] /= .95
    raw = frame.to_csv(index=False,float_format='%.10f',lineterminator='\n').encode()
    (data/'production.csv').write_bytes(raw)
    manifest = json.loads((data/'manifest.json').read_text())
    manifest['dataset_hashes']['production'] = hashlib.sha256(raw).hexdigest()
    (data/'manifest.json').write_text(json.dumps(manifest))
    report = train_one(data,tmp_path/'models','production','2026-10-29T00:00:00+00:00')
    changed = json.loads((tmp_path/'models/production.json').read_text())
    assert report['chosen_alpha'] == original['metadata']['training_configuration']['alpha']
    assert np.allclose(changed['coef'],original['coef'],rtol=1e-10,atol=1e-10)
    assert report['deployment_gate']['uses_test'] is False


def test_old_new_metrics_keep_same_population_and_report_regressions():
    reports = json.loads((ROOT/'ml/evaluation/metrics.json').read_text())
    for kind,report in reports.items():
        common = report['v2_common_domain_test']
        assert common['n'] >= 30 and common['used_for_selection'] is False
        assert all(m['n'] == common['n'] for model in ['old_model','new_model','baseline'] for m in common[model].values())
        assert all(m['n'] == 120 for model in ['old_model','new_model'] for m in report['frozen_v1_test'][model].values())
        assert report['deployment_gate']['accepted'] and not report['deployment_gate']['uses_test']
        assert report['frozen_v1_test']['new_model']['predicted_yield_ratio']['rmse'] > report['frozen_v1_test']['old_model']['predicted_yield_ratio']['rmse']


@pytest.mark.parametrize('mutation', ['categorical_denominator', 'unknown_policy', 'missing_v2_policy'])
def test_new_constraint_and_policy_metadata_fail_closed(mutation):
    document = json.loads((ROOT/'ml/models/production.json').read_text())
    if mutation == 'categorical_denominator': document['input_constraints'][0]['relative_to'] = 'meat_type'
    elif mutation == 'unknown_policy': document['metadata']['prediction_policy'] = 'silently_clip'
    else: document['metadata'].pop('prediction_policy')
    with pytest.raises(ModelUnavailable): PortableModel(document, 'production')
