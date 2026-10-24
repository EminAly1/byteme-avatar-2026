"""Protected core API. No domain write may bypass execute()/its transaction."""
import hmac
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import JSONResponse
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app import models as m, schemas as s, services, sales
from app.commands import execute
from app.config import get_settings
from app.database import get_engine
from app.errors import DomainError


def authenticate(x_api_key: Annotated[str | None, Header()] = None):
    secret = get_settings().avatar_api_key
    if not secret or not secret.get_secret_value():
        raise DomainError('API_NOT_CONFIGURED', 'İş API anahtarı yapılandırılmamış', 503)
    if x_api_key is None or not hmac.compare_digest(x_api_key.encode(), secret.get_secret_value().encode()):
        raise DomainError('UNAUTHORIZED', 'Geçerli X-API-Key gerekli', 401)


def database():
    try:
        engine = get_engine()
    except ValueError:
        raise DomainError('DATABASE_UNAVAILABLE', 'Veritabanı yapılandırılmamış', 503) from None
    with Session(engine) as db:
        yield db


router = APIRouter(prefix='/v1', dependencies=[Depends(authenticate)])
DB = Annotated[Session, Depends(database)]
Key = Annotated[UUID, Header(alias='Idempotency-Key')]
Limit = Annotated[int, Query(ge=1, le=100)]


def write(scope, key, payload, service, status=201):
    body, code = execute(scope, key, payload, service, status)
    return JSONResponse(body, status_code=code)


@router.post('/products', status_code=201)
def product_create(body: s.ProductCreate, key: Key):
    return write('products', key, body, services.create_product)


@router.post('/parties', status_code=201)
def party_create(body: s.PartyCreate, key: Key):
    return write('parties', key, body, services.create_party)


@router.post('/locations', status_code=201)
def location_create(body: s.LocationCreate, key: Key):
    return write('locations', key, body, services.create_location)


@router.post('/receipts', status_code=201)
def receipt_create(body: s.ReceiptCreate, key: Key):
    return write('receipts', key, body, services.create_receipt)


@router.get('/receipts/{receipt_id}')
def receipt_get(receipt_id: UUID, db: DB):
    return services.receipt_detail(db, services.get(db, m.Receipt, receipt_id))


@router.post('/operations', status_code=201)
def operation_create(body: s.OperationCreate, key: Key):
    return write('operations', key, body, services.create_operation)


@router.get('/operations/{operation_id}')
def operation_get(operation_id: UUID, db: DB):
    return services.operation_detail(db, services.get(db, m.Operation, operation_id))


@router.post('/operations/{operation_id}/dispatch')
def operation_dispatch(operation_id: UUID, body: s.DispatchCreate, key: Key):
    return write(f'operations:{operation_id}:dispatch', key, body, lambda db, p: services.dispatch(db, operation_id, p), 200)


@router.post('/operations/{operation_id}/post')
def operation_post(operation_id: UUID, body: s.OperationPost, key: Key):
    return write(f'operations:{operation_id}:post', key, body, lambda db, p: services.post_operation(db, operation_id, p), 200)


@router.get('/lots/{lot_id}')
def lot_get(lot_id: UUID, db: DB):
    return services.entity(services.get(db, m.Lot, lot_id))


def listing(model, serialize=services.entity):
    def endpoint(db: DB, limit: Limit = 50, cursor: UUID | None = None):
        query = select(model).order_by(model.id).limit(limit+1)
        if cursor:
            query = query.where(model.id > str(cursor))
        rows = db.scalars(query).all()
        return {'items': [serialize(x) for x in rows[:limit]], 'next_cursor': rows[limit-1].id if len(rows) > limit else None}
    return endpoint


for path, model in [('products', m.Product), ('parties', m.Party), ('locations', m.Location), ('lots', m.Lot), ('receipts', m.Receipt), ('operations', m.Operation)]:
    router.add_api_route('/'+path, listing(model), methods=['GET'], name='list_'+path)


@router.get('/stocks')
def stocks(db: DB, limit: Limit = 50, cursor: str | None = None, lot_id: UUID | None = None, product_id: UUID | None = None, location_id: UUID | None = None):
    query = select(m.StockBalance, m.Lot, m.Location).join(m.Lot, m.StockBalance.lot_id == m.Lot.id).join(m.Location, m.StockBalance.location_id == m.Location.id)
    for value, column in [(lot_id, m.Lot.id), (product_id, m.Lot.product_id), (location_id, m.StockBalance.location_id)]:
        if value:
            query = query.where(column == str(value))
    if cursor:
        try:
            a, b = (str(UUID(x)) for x in cursor.split(':'))
        except (ValueError, TypeError):
            raise DomainError('INVALID_CURSOR', 'Stok cursor biçimi geçersiz', 422) from None
        query = query.where(or_(m.StockBalance.lot_id > a, and_(m.StockBalance.lot_id == a, m.StockBalance.location_id > b)))
    rows = db.execute(query.order_by(m.StockBalance.lot_id, m.StockBalance.location_id).limit(limit+1)).all()
    items = []
    for balance, lot, location in rows[:limit]:
        unavailable = location.kind == 'quarantine'
        try:
            services.usable(lot)
        except DomainError:
            unavailable = True
        items.append({**services.entity(balance), 'product_id': lot.product_id, 'blocked': lot.blocked, 'available_quantity': '0.000000' if unavailable else format(balance.quantity, '.6f')})
    next_cursor = f'{rows[limit-1][0].lot_id}:{rows[limit-1][0].location_id}' if len(rows) > limit else None
    return {'items': items, 'next_cursor': next_cursor}


@router.get('/stock-movements')
def movements(db: DB, limit: Limit = 50, cursor: UUID | None = None, lot_id: UUID | None = None, location_id: UUID | None = None, operation_id: UUID | None = None):
    query = select(m.StockMovement).order_by(m.StockMovement.id).limit(limit+1)
    for value, column in [(lot_id, m.StockMovement.lot_id), (location_id, m.StockMovement.location_id), (operation_id, m.StockMovement.operation_id)]:
        if value:
            query = query.where(column == str(value))
    if cursor:
        query = query.where(m.StockMovement.id > str(cursor))
    rows = db.scalars(query).all()
    return {'items': [services.entity(x) for x in rows[:limit]], 'next_cursor': rows[limit-1].id if len(rows) > limit else None}


@router.post('/sales', status_code=201)
def sale_create(body: s.SaleCreate, key: Key):
    return write('sales', key, body, sales.create_sale)


@router.get('/sales/{sale_id}')
def sale_get(sale_id: UUID, db: DB):
    return sales.sale_detail(db, services.get(db, m.Sale, sale_id))


@router.post('/shipments', status_code=201)
def shipment_create(body: s.ShipmentCreate, key: Key):
    return write('shipments', key, body, sales.create_shipment)


@router.get('/shipments/{shipment_id}')
def shipment_get(shipment_id: UUID, db: DB):
    return sales.shipment_detail(db, services.get(db, m.Shipment, shipment_id))


router.add_api_route('/sales', listing(m.Sale, sales.sale_summary), methods=['GET'], name='list_sales')
router.add_api_route('/shipments', listing(m.Shipment), methods=['GET'], name='list_shipments')
