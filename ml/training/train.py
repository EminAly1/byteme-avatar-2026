"""Train-only preprocessing; chronological holdouts; validation-only alpha choice.

The v1 frozen test and v2 test are reporting only, never used to choose alpha
or pass the deployment gate. All portable artifacts retain the v1 JSON format.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import numpy as np
import pandas as pd
import sklearn
from sklearn.feature_extraction import DictVectorizer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from ml.data.generate import save, PARTS, SEED, COUNT, SCHEMAS, CONSTRAINTS
from backend.app.ml_runtime import FEATURES, PortableModel, outputs

ALPHAS = [.1, 1., 10.]
EXAMPLES = {
    'production': dict(meat_type='beef', meat_kg='25', spice_kg='0.5', casing_kg='1.25',
        meat_cost_eur='242.50', spice_cost_eur='12.00', casing_cost_eur='14.50',
        planned_producer_profile='producer_a', package_weight_kg='1', estimated_service_eur='112.50'),
    'cutting': dict(species='Kuzu', input_weight_kg='25'),
}


def records(frame, kind):
    return frame[list(FEATURES[kind])].to_dict(orient='records')


def targets(frame, kind):
    if kind == 'production': return frame[['actual_yield_ratio','actual_service_factor']].to_numpy()
    return frame[[f'actual_{p}_kg' for p in PARTS]].to_numpy()/frame[['input_weight_kg']].to_numpy()


def truth(frame, kind):
    if kind == 'production':
        return dict(predicted_finished_quantity=frame.actual_finished_quantity.to_numpy(), predicted_yield_ratio=frame.actual_yield_ratio.to_numpy(),
            predicted_ekp_eur_per_unit=frame.actual_ekp_eur_per_unit.to_numpy(), predicted_total_cost_eur=frame.actual_total_cost_eur.to_numpy())
    parts = frame[[f'actual_{p}_kg' for p in PARTS]].to_numpy(); weight = frame.input_weight_kg.to_numpy()
    return {f'predicted_{p}_kg': parts[:,i] for i,p in enumerate(PARTS)} | dict(predicted_total_weight_kg=parts.sum(axis=1),
        predicted_difference_kg=weight-parts.sum(axis=1), predicted_yield_ratio=parts.sum(axis=1)/weight)


def metrics(frame, kind, predicted):
    result = {}
    for key, actual in truth(frame, kind).items():
        values = [p[key] for p in predicted]
        unit = 'ratio' if 'ratio' in key else ('EUR/package' if 'ekp' in key else ('EUR' if 'cost' in key else ('package' if 'quantity' in key else 'kg')))
        result[key] = {'mae': float(mean_absolute_error(actual, values)), 'rmse': float(np.sqrt(mean_squared_error(actual, values))), 'unit': unit, 'n': len(frame)}
    return result


def evaluate(frame, kind, raw):
    return metrics(frame, kind, [outputs(kind, f, list(r)) for f,r in zip(records(frame, kind), raw)])


def score(values, scales):
    return sum(values[k]['rmse']/scale for k,scale in scales.items())/len(scales)


def split(frame):
    n = len(frame); a, b = int(n*.6), int(n*.8)
    return frame[:a], frame[a:b], frame[b:]


def train_one(data: Path, destination: Path, kind, trained_at):
    raw = (data/f'{kind}.csv').read_bytes(); dataset_hash = hashlib.sha256(raw).hexdigest()
    manifest = json.loads((data/'manifest.json').read_text())
    if manifest['data_origin'] != 'SYNTHETIC' or manifest['dataset_hashes'][kind] != dataset_hash:
        raise ValueError('Dataset provenance/hash mismatch')
    frame = pd.read_csv(data/f'{kind}.csv').sort_values('occurred_at').reset_index(drop=True)
    if set(frame.data_origin) != {'SYNTHETIC'} or set(frame.dataset_version) != {'synthetic-v2'}:
        raise ValueError('v2 trains versioned SYNTHETIC only')
    train, validation, test = split(frame)
    vectorizer = DictVectorizer(sparse=False); x = vectorizer.fit_transform(records(train, kind))
    scaler = StandardScaler().fit(x); x = scaler.transform(x)
    y = targets(train, kind); baseline = y.mean(axis=0)
    keys = ['predicted_finished_quantity','predicted_ekp_eur_per_unit'] if kind == 'production' else [f'predicted_{p}_kg' for p in PARTS]
    scales = {k: max(float(np.std(truth(train, kind)[k])), 1e-9) for k in keys}
    candidates = []
    for alpha in ALPHAS:
        learner = Ridge(alpha=alpha).fit(x, y)
        val = evaluate(validation, kind, learner.predict(scaler.transform(vectorizer.transform(records(validation, kind)))))
        candidates.append((score(val, scales), alpha, learner, val))
    _, alpha, learner, val = min(candidates, key=lambda t: t[0])
    val_baseline = evaluate(validation, kind, np.tile(baseline, (len(validation),1)))
    # Predeclared gate: validation beats train-only mean baseline. Test is read
    # only AFTER this decision and cannot determine alpha/model acceptance.
    accepted = score(val, scales) < score(val_baseline, scales)
    if not accepted:
        raise ValueError('Validation gate failed; do not deploy the candidate')
    baseline_metrics = evaluate(test, kind, np.tile(baseline, (len(test),1)))
    test_raw = learner.predict(scaler.transform(vectorizer.transform(records(test, kind))))
    test_metrics = evaluate(test, kind, test_raw)
    splits = {name: {'n': len(part), 'first_date': part.occurred_at.iloc[0], 'last_date': part.occurred_at.iloc[-1],
        'record_ids': part.record_id.tolist()} for name,part in [('train',train),('validation',validation),('test',test)]}
    report = {'kind': kind, 'data_origin': 'SYNTHETIC', 'splits': splits,
        'baseline': 'Training-only mean yield ratios / mean service factor',
        'baseline_test': baseline_metrics, 'ridge_test': test_metrics,
        'validation_candidates': [{'alpha': a, 'score': s, 'metrics': v} for s,a,_,v in candidates],
        'chosen_alpha': alpha, 'selected_validation': val, 'baseline_validation': val_baseline,
        'selection_scales_train_only': scales,
        'deployment_gate': {'accepted': accepted, 'rule': 'validation normalized RMSE < training-mean baseline validation RMSE', 'uses_test': False},
        'test_used_for_selection': False, 'preprocessing_fit_rows': len(train), 'trained_on_real_history': False}
    document = {'artifact_format': 'avatar-linear-json-v1', 'kind': kind, 'feature_names': vectorizer.get_feature_names_out().tolist(),
        'feature_schema': manifest['feature_schema'][kind], 'input_constraints': manifest['input_constraints'][kind],
        'mean': scaler.mean_.tolist(), 'scale': scaler.scale_.tolist(), 'coef': learner.coef_.tolist(), 'intercept': learner.intercept_.tolist(),
        'metadata': {'model_version': f'{kind}-ridge-v2-{dataset_hash[:12]}', 'trained_at': trained_at,
            'feature_schema_version': 'preprocess-v1', 'dataset_version': manifest['dataset_version'],
            'dataset_hash': dataset_hash, 'data_origin': 'SYNTHETIC', 'example_inputs': EXAMPLES[kind],
            'prediction_policy': 'reject_invalid_physics_v2',
            'training_configuration': {'seed': manifest['seed'], 'algorithm': 'Ridge', 'alpha': alpha, 'alpha_grid': ALPHAS,
                'split': 'chronological 60/20/20; independent synthetic records; no shared process across splits',
                'fit': 'train only; no refit after selection', 'python': platform.python_version(), 'sklearn': sklearn.__version__,
                'numpy': np.__version__, 'pandas': pd.__version__,
                'targets': ['yield_ratio','service_factor'] if kind == 'production' else [f'{p}_ratio' for p in PARTS],
                'projection': 'v2 inference rejects physically invalid raw outputs; no silent clipping'},
            'metrics': {'baseline_test': baseline_metrics, 'ridge_test': test_metrics, 'splits': {k:v['n'] for k,v in splits.items()}}}}
    portable = PortableModel(document, kind)
    for f,r in zip(records(test, kind), test_raw):
        for key,value in outputs(kind, f, list(r)).items():
            assert np.isclose(portable.predict(f)[key], value, rtol=1e-12, atol=1e-12)
    # Same frozen historical test, reporting only. New and old target process
    # distributions differ: historical and v2-wide errors are NOT comparable.
    history = Path(__file__).resolve().parents[1]/'evaluation/v1'
    old_doc = json.loads((history/f'{kind}.json').read_text()); old = PortableModel(old_doc, kind)
    historical = pd.read_csv(history/f'{kind}-test.csv')
    report['frozen_v1_test'] = {
        'old_model': metrics(historical, kind, [old.predict(f) for f in records(historical, kind)]),
        'new_model': metrics(historical, kind, [portable.predict(f) for f in records(historical, kind)]),
        'used_for_selection': False}
    common_indices = []
    for i,f in enumerate(records(test,kind)):
        try: old.predict(f)
        except ValueError: continue
        common_indices.append(i)
    common = test.iloc[common_indices]
    report['v2_common_domain_test'] = {'n': len(common), 'used_for_selection': False,
        'old_model': metrics(common, kind, [old.predict(f) for f in records(common,kind)]),
        'new_model': metrics(common, kind, [portable.predict(f) for f in records(common,kind)]),
        'baseline': evaluate(common, kind, np.tile(baseline,(len(common),1)))}
    destination.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(document, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()
    (destination/f'{kind}.json').write_bytes(encoded)
    (destination/f'{kind}.sha256').write_text(hashlib.sha256(encoded).hexdigest()+'\n')
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=Path, default=Path('ml/data'))
    parser.add_argument('--models', type=Path, default=Path('ml/models'))
    parser.add_argument('--evaluation', type=Path, default=Path('ml/evaluation'))
    parser.add_argument('--seed', type=int, default=SEED)
    parser.add_argument('--count', type=int, default=COUNT)
    parser.add_argument('--trained-at', default=datetime.now(timezone.utc).isoformat())
    args = parser.parse_args(); save(args.data, args.seed, args.count)
    report = {kind: train_one(args.data,args.models,kind,args.trained_at) for kind in ('production','cutting')}
    args.evaluation.mkdir(parents=True,exist_ok=True)
    (args.evaluation/'metrics.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k: {'alpha': v['chosen_alpha'], 'gate': v['deployment_gate'], 'common_n': v['v2_common_domain_test']['n'],
        'baseline': v['baseline_test'], 'ridge': v['ridge_test']} for k,v in report.items()}, indent=2))


if __name__ == '__main__': main()
