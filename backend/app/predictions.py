"""Forecast-only persistence. Operational entities are read, never mutated."""
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP, localcontext
from uuid import uuid4
from sqlalchemy import select
from app import models as m
from app.commands import canonical
from app.config import get_settings
from app.errors import DomainError
from app.ml_runtime import FEATURES, PARTS, LIMITATIONS, ModelUnavailable, load_model
from app.services import get

Q=Decimal('.000001')


def decimal_text(value, places=Q):
    with localcontext() as ctx:
        ctx.prec=48
        return format(Decimal(str(value)).quantize(places,rounding=ROUND_HALF_UP),'f')


def model(kind):
    try:
        return load_model(get_settings().avatar_ml_model_dir,kind)
    except ModelUnavailable:
        raise DomainError('MODEL_UNAVAILABLE','Model yok/geçersiz. İncelenmiş JSON modelini kurup API sürecini yeniden başlatın.',503) from None


def models_info():
    return {'models':[{**model(kind).document['metadata'],'kind':kind,
        'feature_schema':model(kind).document['feature_schema'],'prediction_limitations':LIMITATIONS}
        for kind in ('production','cutting')]}


def lock_operation(db, request, kind):
    if not request.operation_id: return None
    op=db.scalar(select(m.Operation).where(m.Operation.id==str(request.operation_id)).with_for_update())
    if not op: raise DomainError('NOT_FOUND','İşlem bulunamadı',404)
    expected='external_production' if kind=='production' else 'cutting'
    if op.kind!=expected or op.status!='draft':
        raise DomainError('FORECAST_TOO_LATE','Tahmin yalnız eşleşen, kapanmamış işlem başlamadan kaydedilebilir',409)
    if db.scalar(select(m.StockMovement.id).where(m.StockMovement.operation_id==op.id).limit(1)):
        raise DomainError('FORECAST_TOO_LATE','Hammadde sevkinden sonra yeni işlem öncesi tahmin kaydedilemez',409)
    return op


def create_prediction(db, request, kind):
    op=lock_operation(db,request,kind)
    context={}
    if kind=='production':
        if request.output_product_id:
            product=get(db,m.Product,request.output_product_id)
            if product.type!='finished' or product.base_unit!='package' or product.package_weight_kg!=request.package_weight_kg:
                raise DomainError('PREDICTION_PRODUCT_MISMATCH','Paket ürünü ve ağırlığı eşleşmelidir',422)
            context['output_product_id']=product.id
        if op: context['producer_id']=op.producer_id
        features={k:getattr(request,k) for k in FEATURES[kind]}
    else:
        recipe=get(db,m.RecipeVersion,request.recipe_version_id)
        products={k:get(db,m.Product,v) for k,v in request.part_products.items()}
        lines=db.scalars(select(m.RecipeLine).where(m.RecipeLine.recipe_version_id==recipe.id)).all()
        if not recipe.available or recipe.species!=request.species or (op and op.recipe_version_id!=recipe.id):
            raise DomainError('PREDICTION_RECIPE_MISMATCH','Tür/reçete sürümü veya kullanılabilirlik eşleşmedi',422)
        if {p.id for p in products.values()}!={x.product_id for x in lines} or any(p.base_unit!='kg' or p.type!='finished' for p in products.values()):
            raise DomainError('PREDICTION_RECIPE_MISMATCH','Reçete beş farklı kg mamul parçası içermeli; yan ürünlü/başka reçete eğitimi yok',422)
        context={'recipe_version_id':recipe.id,'recipe_code':recipe.code,'recipe_version':recipe.version,
            'part_products':{k:p.id for k,p in products.items()},'part_names':{k:p.name for k,p in products.items()},
            'recipe_shape':'five_parts_v1'}
        features={'species':request.species,'input_weight_kg':request.input_weight_kg,'recipe_shape':'five_parts_v1'}
    artifact=model(kind)
    numeric={k:float(v) if isinstance(v,Decimal) else v for k,v in features.items()}
    try: values=artifact.predict(numeric)
    except ModelUnavailable:
        raise DomainError('MODEL_UNAVAILABLE','Model sonlu tahmin üretemedi',503) from None
    except ValueError:
        raise DomainError('PREDICTION_OUT_OF_DOMAIN','Girdiler belgelenmiş sentetik eğitim aralığı dışında',422) from None
    result={k:decimal_text(v) for k,v in values.items()}
    if kind=='cutting':
        # Round parts down, then derive the public totals in Decimal: sum can never exceed input.
        for p in PARTS:
            result[f'predicted_{p}_kg']=format(Decimal(str(values[f'predicted_{p}_kg'])).quantize(Q,rounding=ROUND_DOWN),'f')
        total=sum(Decimal(result[f'predicted_{p}_kg']) for p in PARTS)
        result.update(predicted_total_weight_kg=decimal_text(total),predicted_difference_kg=decimal_text(request.input_weight_kg-total),
            predicted_yield_ratio=decimal_text(total/request.input_weight_kg),unit='kg')
    else:
        result.update(quantity_unit='package',currency='EUR',predicted_ekp_display=decimal_text(values['predicted_ekp_eur_per_unit'],Decimal('.01')))
    meta=artifact.document['metadata']
    result.update(model_version=meta['model_version'],data_origin=meta['data_origin'],feature_schema_version=meta['feature_schema_version'],
        dataset_version=meta['dataset_version'],dataset_hash=meta['dataset_hash'],prediction_limitations=LIMITATIONS,
        cost_meaning='Bilinen planlı malzeme bedeli + tahmin edilen hizmet bedeli; gerçek muhasebe toplamı değildir.' if kind=='production' else None)
    record=m.PredictionRecord(id=str(uuid4()),created_at=m.now(),kind=kind,operation_id=op.id if op else None,
        model_version=meta['model_version'],feature_schema_version=meta['feature_schema_version'],features=canonical(features),context=canonical(context),prediction=result)
    db.add(record);db.flush()
    return render(record)


def render(record):
    return {'id':record.id,'kind':record.kind,'operation_id':record.operation_id,
        'predicted_at':record.created_at.isoformat(timespec='microseconds')+'+00:00',
        'features':record.features,'context':record.context,**record.prediction}


def actual_values(db,record):
    if not record.operation_id: return None,'İşlemle eşlenmemiş tahmin'
    op=get(db,m.Operation,record.operation_id)
    if op.status!='posted': return None,'İşlem henüz kapanmadı'
    outputs=db.scalars(select(m.OperationOutput).where(m.OperationOutput.operation_id==op.id)).all()
    inputs=db.scalars(select(m.OperationInput).where(m.OperationInput.operation_id==op.id)).all()
    with localcontext() as ctx:
        ctx.prec=48
        if record.kind=='production':
            target=record.context['output_product_id']
            if not outputs or any(get(db,m.Lot,o.lot_id).product_id!=target for o in outputs):
                return None,'Gerçek çıktılar tek hedef paket ürünüyle eşleşmiyor; karşılaştırma uygulanamaz'
            if any(get(db,m.Product,get(db,m.Lot,i.lot_id).product_id).base_unit!='kg' for i in inputs):
                return None,'Gerçek girdiler kg değil; karşılaştırma uygulanamaz'
            quantity=sum(o.quantity for o in outputs); mass=sum(i.quantity for i in inputs)
            if quantity<=0 or mass<=0: return None,'Sıfır gerçekleşme paydası'
            return {'predicted_finished_quantity':quantity,'predicted_yield_ratio':quantity*Decimal(record.features['package_weight_kg'])/mass,
                'predicted_total_cost_eur':op.total_cost,'predicted_ekp_eur_per_unit':op.total_cost/quantity},None
        mapping=record.context['part_products']; actual={k:Decimal('0') for k in mapping}
        reverse={v:k for k,v in mapping.items()}
        for output in outputs:
            product=get(db,m.Lot,output.lot_id).product_id
            if product not in reverse:return None,'Gerçek çıktılarda eğitilmemiş parça/yan ürün var; karşılaştırma uygulanamaz'
            actual[reverse[product]]+=output.quantity
        total=sum(actual.values()); mass=sum(i.quantity for i in inputs)
        if mass<=0:return None,'Sıfır gerçekleşme paydası'
        return {f'predicted_{p}_kg':x for p,x in actual.items()} | {'predicted_total_weight_kg':total,
            'predicted_difference_kg':mass-total,'predicted_yield_ratio':total/mass},None


def detail(db,record):
    actual,reason=actual_values(db,record)
    deviations={}
    with localcontext() as ctx:
        ctx.prec=48
        for key,value in record.prediction.items():
            if key in ('predicted_ekp_display',) or not key.startswith('predicted_'):continue
            a=actual.get(key) if actual else None
            delta=abs(Decimal(value)-a) if a is not None else None
            deviations[key]={'predicted':value,'actual':decimal_text(a) if a is not None else None,
                'absolute_deviation':decimal_text(delta) if delta is not None else None,
                'percentage_deviation':decimal_text(delta/abs(a)*100) if a else None}
    return {**render(record),'actual_unavailable_reason':reason,'comparison':deviations,
        'percentage_denominator':'abs(actual); zero or unavailable => null'}
