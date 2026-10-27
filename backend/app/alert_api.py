"""Authenticated read-only current alerts; no command/write routes."""
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from app.api import authenticate, DB
from app import alerts

router = APIRouter(prefix='/v1/alerts', tags=['alerts'], dependencies=[Depends(authenticate)])
Severity = Literal['critical', 'warning', 'info']
Rule = Literal['EXPIRY_PAST', 'EXPIRY_SOON', 'LOT_BLOCKED_STOCK', 'LOW_AVAILABLE_STOCK', 'PRODUCTION_EKP_DEVIATION', 'YIELD_DEVIATION']


@router.get('')
def listing(db: DB, severity: Severity | None = None, rule_code: Rule | None = None,
            lot_id: UUID | None = None, operation_id: UUID | None = None,
            limit: Annotated[int, Query(ge=1, le=100)] = 50,
            cursor: Annotated[str | None, Query(max_length=2048)] = None):
    return alerts.evaluate(db, severity=severity, rule_code=rule_code, lot_id=lot_id,
                           operation_id=operation_id, limit=limit, cursor=cursor)


@router.get('/summary')
def summary(db: DB):
    result = alerts.evaluate(db, limit=0)
    return {key: value for key, value in result.items() if key not in ('items', 'next_cursor')}


@router.get('/{alert_id}')
def detail(alert_id: UUID, db: DB):
    return alerts.evaluate(db, identifier=alert_id)
