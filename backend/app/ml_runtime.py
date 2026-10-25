"""Bounded JSON linear inference. No sklearn, pickle, DB access or ledger writes."""
from functools import lru_cache
from datetime import datetime
from pathlib import Path
import hashlib
import json
import math
import re
from numbers import Real

PARTS = ('leg', 'shoulder', 'back', 'rib', 'mince')
FEATURES = {
    'production': ('meat_type','meat_kg','spice_kg','casing_kg','meat_cost_eur','spice_cost_eur','casing_cost_eur','planned_producer_profile','package_weight_kg','estimated_service_eur'),
    'cutting': ('species','input_weight_kg','recipe_shape'),
}
LIMITATIONS = [
    'SYNTHETIC eğitim/test verisi: gerçek işletme başarımı kanıtlanmadı.',
    'Karar desteğidir; stok, lot, recall veya muhasebe kaydı oluşturmaz.',
    'Gözlenmeyen süreç değişkenleri ve dağılım kayması nedeniyle hata mümkündür; güven aralığı kalibre edilmedi.',
]


class ModelUnavailable(ValueError):
    pass


def finite(values):
    if not all(isinstance(x,Real) and not isinstance(x,bool) and math.isfinite(x) for x in values):
        raise ModelUnavailable('Non-finite model value')


def constrain(kind, raw):
    finite(raw)
    if kind == 'production':
        return [min(1., max(.01, raw[0])), min(3., max(.01, raw[1]))]
    ratios = [max(0., x) for x in raw]
    total = sum(ratios)
    return [x/max(1.,total) for x in ratios]


def outputs(kind, features, raw):
    value = constrain(kind, raw)
    if kind == 'production':
        qty = value[0]*(features['meat_kg']+features['spice_kg']+features['casing_kg'])/features['package_weight_kg']
        total = sum(features[k] for k in ('meat_cost_eur','spice_cost_eur','casing_cost_eur')) + features['estimated_service_eur']*value[1]
        result = dict(predicted_finished_quantity=qty,predicted_yield_ratio=value[0],predicted_ekp_eur_per_unit=total/qty,predicted_total_cost_eur=total)
    else:
        weight=features['input_weight_kg']; parts=[weight*x for x in value]; total=sum(parts)
        result={f'predicted_{p}_kg':x for p,x in zip(PARTS,parts)} | dict(predicted_total_weight_kg=total,predicted_difference_kg=max(0.,weight-total),predicted_yield_ratio=total/weight)
    finite(result.values())
    return result


class PortableModel:
    def __init__(self, document, kind):
        try:
            self.document = document
            if document['artifact_format'] != 'avatar-linear-json-v1' or document['kind'] != kind:
                raise ValueError('Wrong format or kind')
            self.kind=kind
            meta=document['metadata']; schema=document['feature_schema']
            if meta['feature_schema_version'] != 'preprocess-v1' or meta['data_origin'] != 'SYNTHETIC':
                raise ValueError('Unsupported schema or source')
            if not isinstance(meta['model_version'],str) or not 1<=len(meta['model_version'])<=100 or not re.fullmatch('[a-f0-9]{64}',meta['dataset_hash']):
                raise ValueError('Missing provenance')
            if datetime.fromisoformat(meta['trained_at']).tzinfo is None:
                raise ValueError('Training timestamp must have timezone')
            for required in ('dataset_version','training_configuration','metrics'):
                if not meta[required]: raise ValueError('Missing metadata')
            if set(schema) != set(FEATURES[kind]): raise ValueError('Feature mismatch')
            expected_names=[]
            for name,spec in schema.items():
                if not isinstance(spec,dict):raise ValueError('Invalid feature schema')
                if 'categories' in spec:
                    cats=spec['categories']
                    if not isinstance(cats,list) or not cats or len(cats)>32 or not all(isinstance(c,str) and c for c in cats) or len(set(cats))!=len(cats):
                        raise ValueError('Invalid categories')
                    expected_names.extend(name+'='+c for c in cats)
                else:
                    finite([spec['minimum'],spec['maximum']])
                    if spec['minimum']>spec['maximum']:raise ValueError('Invalid range')
                    expected_names.append(name)
            n=len(document['feature_names']); targets=2 if kind=='production' else 5
            if n<1 or n>64 or len(set(document['feature_names']))!=n: raise ValueError('Vector length')
            if set(expected_names)!=set(document['feature_names']):raise ValueError('Vector schema mismatch')
            if len(document['mean'])!=n or len(document['scale'])!=n or len(document['coef'])!=targets or len(document['intercept'])!=targets:
                raise ValueError('Matrix dimensions')
            for row in document['coef']:
                if len(row)!=n: raise ValueError('Coefficient dimensions')
                finite(row)
            finite(document['mean']+document['scale']+document['intercept'])
            if any(x<=0 for x in document['scale']): raise ValueError('Invalid scale')
            for name in document['feature_names']:
                if name.split('=')[0] not in schema: raise ValueError('Unknown vector feature')
        except (KeyError,TypeError,ValueError,OverflowError,AttributeError) as exc:
            raise ModelUnavailable('Invalid model artifact') from exc

    def predict(self, features):
        doc=self.document
        if set(features)!=set(FEATURES[self.kind]): raise ValueError('Feature schema mismatch')
        for name, spec in doc['feature_schema'].items():
            val=features[name]
            if 'categories' in spec:
                if val not in spec['categories']: raise ValueError('Unsupported category: '+name)
            else:
                if not math.isfinite(float(val)) or not spec['minimum'] <= val <= spec['maximum']:
                    raise ValueError('Outside training domain: '+name)
        vector=[]
        for name in doc['feature_names']:
            if '=' in name:
                key,cat=name.split('=',1); vector.append(float(features[key]==cat))
            else: vector.append(float(features[name]))
        z=[(v-m)/s for v,m,s in zip(vector,doc['mean'],doc['scale'])]
        raw=[sum(c*x for c,x in zip(coef,z))+b for coef,b in zip(doc['coef'],doc['intercept'])]
        return outputs(self.kind,features,raw)


@lru_cache(maxsize=8)
def load_model(directory: str, kind: str):
    try:
        path=Path(directory)/f'{kind}.json'
        if path.stat().st_size > 1_000_000: raise ValueError('Oversized artifact')
        raw=path.read_bytes()
        expected=path.with_suffix('.sha256').read_text().strip()
        if hashlib.sha256(raw).hexdigest()!=expected: raise ValueError('Checksum mismatch')
        document=json.loads(raw,parse_constant=lambda _: (_ for _ in ()).throw(ValueError('NaN')))
        return PortableModel(document,kind)
    except (OSError,ValueError,TypeError) as exc:
        raise ModelUnavailable('Model missing or invalid; deploy reviewed JSON artifacts') from exc
