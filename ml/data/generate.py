"""Versioned fictional process; balanced batch sizes and independent noise.

No business history/PDF output is training data. One row is one independent
synthetic process, never fragments of the same process across data splits.
"""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np
import pandas as pd

SEED = 20261029
VERSION = 'synthetic-v2'
COUNT = 3000
PARTS = ['leg', 'shoulder', 'back', 'rib', 'mince']
SCHEMAS = {
    'production': {
        'meat_type': {'categories': ['beef', 'lamb']},
        'planned_producer_profile': {'categories': ['producer_a', 'producer_b', 'producer_c']},
        **{k: {'minimum': lo, 'maximum': hi, 'unit': unit} for k, lo, hi, unit in [
            ('meat_kg', 5, 300, 'kg'), ('spice_kg', .05, 12, 'kg'), ('casing_kg', .1, 24, 'kg'),
            ('meat_cost_eur', 0, 6000, 'EUR'), ('spice_cost_eur', 0, 480, 'EUR'),
            ('casing_cost_eur', 0, 720, 'EUR'), ('package_weight_kg', .25, 2, 'kg/package'),
            ('estimated_service_eur', 0, 2400, 'EUR')]},
    },
    'cutting': {'species': {'categories': ['Kuzu']}, 'recipe_shape': {'categories': ['five_parts_v1']},
                'input_weight_kg': {'minimum': 5, 'maximum': 80, 'unit': 'kg'}},
}
CONSTRAINTS = [
    {'type': 'ratio', 'field': 'spice_kg', 'relative_to': 'meat_kg', 'minimum': .01, 'maximum': .04},
    {'type': 'ratio', 'field': 'casing_kg', 'relative_to': 'meat_kg', 'minimum': .02, 'maximum': .08},
]


def generate(seed=SEED, count=COUNT):
    if count < 30:
        raise ValueError('At least 30 independent synthetic rows are required')
    rng = np.random.default_rng(seed)
    production, cutting = [], []
    batches = [(5, 30), (30, 120), (120, 300)]
    cuts = [(5, 18), (18, 40), (40, 80)]
    for i in range(count):
        common = {'record_id': f'SYNTHETIC-V2-{i:05d}',
                  'occurred_at': str(pd.Timestamp('2024-01-01') + pd.Timedelta(hours=i)),
                  'data_origin': 'SYNTHETIC', 'dataset_version': VERSION}
        segment = i % 3
        meat = rng.uniform(*batches[segment])
        spice_ratio, casing_ratio = rng.uniform(.01, .04), rng.uniform(.02, .08)
        # Boundary processes occur independently in every temporal partition.
        # Their outcomes still have independent noise; no record is duplicated.
        if i % 500 == 0: meat, spice_ratio, casing_ratio = 5., .01, .02
        if i % 500 == 1: meat, spice_ratio, casing_ratio = 300., .04, .08
        spice, casing = meat * spice_ratio, meat * casing_ratio
        producer = str(rng.choice(['producer_a', 'producer_b', 'producer_c']))
        meat_type = str(rng.choice(['beef', 'lamb']))
        pack = float(rng.choice([.25, .5, 1, 1.5, 2]))
        costs = [meat*rng.uniform(6, 20), spice*rng.uniform(12, 40), casing*rng.uniform(6, 30)]
        estimate = meat*rng.uniform(2, 8)  # Independent pre-process quote.
        yield_ratio = (.785 + {'producer_a': .022, 'producer_b': -.026, 'producer_c': .004}[producer]
            + (.012 if meat_type == 'lamb' else 0) + .00009*(meat-100)
            - (.012 if meat < 30 else 0) - .2*(spice_ratio-.025) + rng.normal(0, .012))
        service_factor = (1.02 + {'producer_a': -.04, 'producer_b': .06, 'producer_c': 0}[producer]
            + .00016*(meat-100) + (.02 if meat < 30 else 0) + rng.normal(0, .028))
        assert 0 < yield_ratio < 1 and 0 < service_factor < 3
        qty = (meat+spice+casing)*yield_ratio/pack
        total = sum(costs)+estimate*service_factor
        production.append(common | dict(batch_segment='small' if meat < 30 else 'medium' if meat < 120 else 'large',
            meat_type=meat_type, meat_kg=meat, spice_kg=spice, casing_kg=casing,
            meat_cost_eur=costs[0], spice_cost_eur=costs[1], casing_cost_eur=costs[2],
            planned_producer_profile=producer, package_weight_kg=pack, estimated_service_eur=estimate,
            actual_yield_ratio=yield_ratio, actual_service_factor=service_factor,
            actual_finished_quantity=qty, actual_total_cost_eur=total, actual_ekp_eur_per_unit=total/qty))
        weight = rng.uniform(*cuts[segment])
        if i % 500 == 0: weight = 5.
        if i % 500 == 1: weight = 80.
        # Mostly linear weight effects with irreducible animal/operator variation.
        # These unobserved profiles are targets/noise, never leaked input features.
        ratios = (np.array([.235, .161, .158, .195, .123])
            + (weight-25)*np.array([.00035,-.00012,.00022,.00016,-.00014])
            + rng.normal(0, .005, 5))
        assert np.all(ratios > 0) and .75 < ratios.sum() < .98
        cutting.append(common | dict(species='Kuzu', input_weight_kg=weight, recipe_shape='five_parts_v1',
            **{f'actual_{p}_kg': weight*r for p, r in zip(PARTS, ratios)},
            actual_difference_kg=weight*(1-ratios.sum())))
    return pd.DataFrame(production), pd.DataFrame(cutting)


def save(output: Path, seed=SEED, count=COUNT):
    output.mkdir(parents=True, exist_ok=True)
    hashes, observed = {}, {}
    for name, frame in zip(['production', 'cutting'], generate(seed, count)):
        raw = frame.to_csv(index=False, float_format='%.10f', lineterminator='\n').encode()
        (output/f'{name}.csv').write_bytes(raw)
        hashes[name] = hashlib.sha256(raw).hexdigest()
        observed[name] = {k: {'minimum': float(frame[k].min()), 'maximum': float(frame[k].max())}
                          for k, spec in SCHEMAS[name].items() if 'categories' not in spec}
    manifest = dict(dataset_version=VERSION, data_origin='SYNTHETIC', seed=seed, count_per_model=count,
        generator='ml/data/generate.py', dataset_hashes=hashes, feature_schema=SCHEMAS,
        input_constraints={'production': CONSTRAINTS, 'cutting': []}, observed_ranges=observed,
        method='Balanced small/medium/large independent processes; conditional ingredient quantities, varied costs/profiles/package sizes, independent yield/service/part noise. Dates are fictional.',
        real_history_rows=0, historical_pdf_reference_used_for_training=False)
    (output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=Path('ml/data'))
    parser.add_argument('--seed', type=int, default=SEED)
    parser.add_argument('--count', type=int, default=COUNT)
    args = parser.parse_args()
    save(args.output, args.seed, args.count)
