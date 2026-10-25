"""Explicitly fictional stochastic process, not reconstructed enterprise history."""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np
import pandas as pd

SEED = 202609
VERSION = 'synthetic-v1'
PARTS = ['leg', 'shoulder', 'back', 'rib', 'mince']


def generate(seed=SEED, count=600):
    rng = np.random.default_rng(seed)
    production, cutting = [], []
    for i in range(count):
        common = {'record_id': f'SYNTHETIC-{i:04d}', 'occurred_at': str(pd.Timestamp('2024-01-01') + pd.Timedelta(days=i)),
                  'data_origin': 'SYNTHETIC', 'dataset_version': VERSION}
        meat = rng.uniform(60, 160)
        spice, casing = meat*rng.uniform(.014, .026), meat*rng.uniform(.035, .065)
        producer = str(rng.choice(['producer_a', 'producer_b', 'producer_c']))
        meat_type = str(rng.choice(['beef', 'lamb']))
        pack = float(rng.choice([.5, 1, 1.5]))
        costs = [meat*rng.uniform(8, 14), spice*rng.uniform(18, 28), casing*rng.uniform(9, 16)]
        estimate = meat*rng.uniform(3.6, 5.5)  # Pre-production independent quote, not actual output × tariff.
        yield_ratio = .79 + {'producer_a': .018, 'producer_b': -.025, 'producer_c': .005}[producer] + (.012 if meat_type == 'lamb' else 0) + .0002*(meat-100) + rng.normal(0, .009)
        service_factor = 1.02 + {'producer_a': -.04, 'producer_b': .06, 'producer_c': 0}[producer] + .0003*(meat-100) + rng.normal(0, .022)
        qty = (meat+spice+casing)*yield_ratio/pack
        total = sum(costs)+estimate*service_factor
        production.append(common | dict(meat_type=meat_type, meat_kg=meat, spice_kg=spice, casing_kg=casing,
            meat_cost_eur=costs[0], spice_cost_eur=costs[1], casing_cost_eur=costs[2], planned_producer_profile=producer,
            package_weight_kg=pack, estimated_service_eur=estimate, actual_yield_ratio=yield_ratio,
            actual_service_factor=service_factor, actual_finished_quantity=qty, actual_total_cost_eur=total,
            actual_ekp_eur_per_unit=total/qty))
        weight = rng.uniform(18, 40)
        # More than one yield/part profile; independent unobserved noise is deliberately irreducible.
        ratios = np.array([.235, .161, .158, .195, .123]) + (weight-25)*np.array([.0008,-.0002,.0005,.0004,-.0003]) + rng.normal(0,.004,5)
        ratios = np.maximum(ratios, 0)
        if ratios.sum() > .97:
            ratios *= .97/ratios.sum()
        cutting.append(common | dict(species='Kuzu', input_weight_kg=weight, recipe_shape='five_parts_v1',
            **{f'actual_{p}_kg': weight*r for p,r in zip(PARTS,ratios)}, actual_difference_kg=weight*(1-ratios.sum())))
    return pd.DataFrame(production), pd.DataFrame(cutting)


def save(output: Path, seed=SEED, count=600):
    output.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for name, frame in zip(['production','cutting'], generate(seed, count)):
        raw = frame.to_csv(index=False, float_format='%.10f', lineterminator='\n').encode()
        (output/f'{name}.csv').write_bytes(raw)
        hashes[name] = hashlib.sha256(raw).hexdigest()
    manifest = dict(dataset_version=VERSION, data_origin='SYNTHETIC', seed=seed, count_per_model=count,
        generator='ml/data/generate.py', dataset_hashes=hashes,
        method='Fictional pre-process features plus independent unobserved yield/service noise; chronological dates are synthetic.',
        real_history_rows=0, historical_pdf_reference_used_for_training=False)
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


if __name__ == '__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--output',type=Path,default=Path('ml/data'))
    args=parser.parse_args(); save(args.output)
