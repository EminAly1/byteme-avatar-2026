"""No DB or third-party imports: use the exact deployed portable model runtime."""
import json
from pathlib import Path
from backend.app.ml_runtime import load_model


def main():
    directory=str(Path(__file__).resolve().parents[1]/'models')
    features={'production':dict(meat_type='beef',meat_kg=100.,spice_kg=2.,casing_kg=5.,meat_cost_eur=970.,spice_cost_eur=48.,casing_cost_eur=58.,
        planned_producer_profile='producer_a',package_weight_kg=1.,estimated_service_eur=450.),
        'cutting':dict(species='Kuzu',input_weight_kg=25.,recipe_shape='five_parts_v1')}
    results={}
    for kind,values in features.items():
        model=load_model(directory,kind)
        results[kind]={'features':values,'prediction':model.predict(values),'model_version':model.document['metadata']['model_version'],'data_origin':'SYNTHETIC'}
    print(json.dumps(results,indent=2,allow_nan=False))


if __name__=='__main__':main()
