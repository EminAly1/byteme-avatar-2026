"""Existing shared API authentication, command idempotency and DB transactions."""
from uuid import UUID
from fastapi import APIRouter, Depends
from app.api import authenticate, DB, Key, write
from app import predictions, prediction_schemas as s, models as m
from app.services import get

router=APIRouter(prefix='/v1/predictions',tags=['predictions'],dependencies=[Depends(authenticate)])


@router.get('/models')
def models():
    return predictions.models_info()


@router.post('/production',status_code=201)
def production(body:s.ProductionPrediction,key:Key):
    return write('predictions:production',key,body,lambda db,p:predictions.create_prediction(db,p,'production'))


@router.post('/cutting',status_code=201)
def cutting(body:s.CuttingPrediction,key:Key):
    return write('predictions:cutting',key,body,lambda db,p:predictions.create_prediction(db,p,'cutting'))


@router.get('/{prediction_id}')
def prediction(prediction_id:UUID,db:DB):
    return predictions.detail(db,get(db,m.PredictionRecord,prediction_id))
