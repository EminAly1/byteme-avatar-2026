"""Train-only preprocessing; chronological holdouts; validation-only alpha choice."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import numpy as np
import pandas as pd
from sklearn.feature_extraction import DictVectorizer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from ml.data.generate import save, PARTS, SEED
from backend.app.ml_runtime import FEATURES, PortableModel, outputs

SCHEMAS = {
 'production': {
  'meat_type': {'categories':['beef','lamb']},
  'planned_producer_profile': {'categories':['producer_a','producer_b','producer_c']},
  **{k:{'minimum':lo,'maximum':hi} for k,lo,hi in [
   ('meat_kg',60,160),('spice_kg',.8,4.2),('casing_kg',2,10.5),
   ('meat_cost_eur',0,2500),('spice_cost_eur',0,150),('casing_cost_eur',0,200),
   ('package_weight_kg',.5,1.5),('estimated_service_eur',200,900)]}},
 'cutting': {'species':{'categories':['Kuzu']}, 'recipe_shape':{'categories':['five_parts_v1']},
             'input_weight_kg':{'minimum':18,'maximum':40}}
}


def records(frame, kind):
    return frame[list(FEATURES[kind])].to_dict(orient='records')


def targets(frame, kind):
    if kind=='production': return frame[['actual_yield_ratio','actual_service_factor']].to_numpy()
    return frame[[f'actual_{p}_kg' for p in PARTS]].to_numpy()/frame[['input_weight_kg']].to_numpy()


def truth(frame,kind):
    if kind=='production':
        return dict(predicted_finished_quantity=frame.actual_finished_quantity.to_numpy(),predicted_yield_ratio=frame.actual_yield_ratio.to_numpy(),
            predicted_ekp_eur_per_unit=frame.actual_ekp_eur_per_unit.to_numpy(),predicted_total_cost_eur=frame.actual_total_cost_eur.to_numpy())
    parts=frame[[f'actual_{p}_kg' for p in PARTS]].to_numpy(); weight=frame.input_weight_kg.to_numpy()
    return {f'predicted_{p}_kg':parts[:,i] for i,p in enumerate(PARTS)} | dict(predicted_total_weight_kg=parts.sum(axis=1),predicted_difference_kg=weight-parts.sum(axis=1),predicted_yield_ratio=parts.sum(axis=1)/weight)


def evaluate(frame,kind,raw):
    predicted=[outputs(kind,f,list(r)) for f,r in zip(records(frame,kind),raw)]
    result={}
    for key,actual in truth(frame,kind).items():
        values=[p[key] for p in predicted]
        unit='ratio' if 'ratio' in key else ('EUR/package' if 'ekp' in key else ('EUR' if 'cost' in key else ('package' if 'quantity' in key else 'kg')))
        result[key]={'mae':float(mean_absolute_error(actual,values)),'rmse':float(np.sqrt(mean_squared_error(actual,values))),'unit':unit,'n':len(frame)}
    return result


def score(metrics,kind):
    # Different units normalized before model selection; test is never consulted.
    if kind=='production': return metrics['predicted_finished_quantity']['rmse']/100+metrics['predicted_ekp_eur_per_unit']['rmse']/20
    return sum(metrics[f'predicted_{p}_kg']['rmse'] for p in PARTS)


def train_one(data: Path, destination: Path, kind, trained_at):
    raw=(data/f'{kind}.csv').read_bytes(); dataset_hash=hashlib.sha256(raw).hexdigest()
    manifest=json.loads((data/'manifest.json').read_text())
    if manifest['data_origin']!='SYNTHETIC' or manifest['dataset_hashes'][kind]!=dataset_hash:
        raise ValueError('Dataset provenance/hash mismatch')
    frame=pd.read_csv(data/f'{kind}.csv').sort_values('occurred_at').reset_index(drop=True)
    if set(frame.data_origin) != {'SYNTHETIC'}: raise ValueError('v1 trains SYNTHETIC only')
    n=len(frame); a=int(n*.6); b=int(n*.8)
    train,validation,test=frame[:a],frame[a:b],frame[b:]
    vectorizer=DictVectorizer(sparse=False); x=vectorizer.fit_transform(records(train,kind))
    scaler=StandardScaler().fit(x); x=scaler.transform(x)
    y=targets(train,kind); baseline=y.mean(axis=0)
    candidates=[]
    for alpha in [.1,1.,10.]:
        learner=Ridge(alpha=alpha).fit(x,y)
        val=evaluate(validation,kind,learner.predict(scaler.transform(vectorizer.transform(records(validation,kind)))))
        candidates.append((score(val,kind),alpha,learner,val))
    _,alpha,learner,val=min(candidates,key=lambda t:t[0])
    baseline_metrics=evaluate(test,kind,np.tile(baseline,(len(test),1)))
    test_metrics=evaluate(test,kind,learner.predict(scaler.transform(vectorizer.transform(records(test,kind)))))
    splits={name:{'n':len(part),'first_date':part.occurred_at.iloc[0],'last_date':part.occurred_at.iloc[-1],
        'record_ids':part.record_id.tolist()} for name,part in [('train',train),('validation',validation),('test',test)]}
    report={'kind':kind,'data_origin':'SYNTHETIC','splits':splits,'baseline':'Training-only mean yield ratios / mean service factor',
        'baseline_test':baseline_metrics,'ridge_test':test_metrics,'validation_candidates':[{'alpha':a,'score':s} for s,a,_,_ in candidates],
        'chosen_alpha':alpha,'selected_validation':val,
        'test_used_for_selection':False,'preprocessing_fit_rows':len(train),'trained_on_real_history':False}
    document={'artifact_format':'avatar-linear-json-v1','kind':kind,'feature_names':vectorizer.get_feature_names_out().tolist(),
        'feature_schema':SCHEMAS[kind],'mean':scaler.mean_.tolist(),'scale':scaler.scale_.tolist(),
        'coef':learner.coef_.tolist(),'intercept':learner.intercept_.tolist(),
        'metadata':{'model_version':f'{kind}-ridge-v1-{dataset_hash[:12]}','trained_at':trained_at,'feature_schema_version':'preprocess-v1',
            'dataset_version':'synthetic-v1','dataset_hash':dataset_hash,'data_origin':'SYNTHETIC',
            'training_configuration':{'seed':manifest['seed'],'algorithm':'Ridge','alpha':alpha,'alpha_grid':[.1,1,10],
                'split':'chronological 60/20/20','fit':'train only; no refit after selection',
                'python':platform.python_version(),'sklearn':'1.6.1','numpy':np.__version__,'pandas':pd.__version__,
                'targets':['yield_ratio','service_factor'] if kind=='production' else [f'{p}_ratio' for p in PARTS],
                'projection':'production ratios bounded; cutting nonnegative then radial projection to simplex sum<=1'},
            'metrics':{'baseline_test':baseline_metrics,'ridge_test':test_metrics,'splits':{k:v['n'] for k,v in splits.items()}}}}
    # Verify the exact portable export agrees with the trained sklearn pipeline.
    portable=PortableModel(document,kind)
    for f,r in zip(records(test,kind),learner.predict(scaler.transform(vectorizer.transform(records(test,kind))))):
        for key,value in outputs(kind,f,list(r)).items():
            assert np.isclose(portable.predict(f)[key],value,rtol=1e-12,atol=1e-12)
    destination.mkdir(parents=True,exist_ok=True)
    encoded=(json.dumps(document,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
    (destination/f'{kind}.json').write_bytes(encoded)
    (destination/f'{kind}.sha256').write_text(hashlib.sha256(encoded).hexdigest()+'\n')
    return report


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--data',type=Path,default=Path('ml/data'))
    parser.add_argument('--models',type=Path,default=Path('ml/models'));parser.add_argument('--evaluation',type=Path,default=Path('ml/evaluation'))
    parser.add_argument('--trained-at',default=datetime.now(timezone.utc).isoformat())
    args=parser.parse_args(); manifest=save(args.data)
    report={kind:train_one(args.data,args.models,kind,args.trained_at) for kind in ('production','cutting')}
    args.evaluation.mkdir(parents=True,exist_ok=True)
    (args.evaluation/'metrics.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:{'alpha':v['chosen_alpha'],'baseline':v['baseline_test'],'ridge':v['ridge_test']} for k,v in report.items()},indent=2))


if __name__=='__main__': main()
