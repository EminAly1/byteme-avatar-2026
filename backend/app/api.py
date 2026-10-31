"""Protected core API. No domain write may bypass execute()/its transaction."""
import hmac
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import JSONResponse
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app import models as m, schemas as s, services, sales, traceability, recalls, cuttings, inventory_adjustments as adjustments
from app.commands import execute
from app.config import get_settings
from app.database import get_engine
from app.errors import DomainError
from app import reworks, second_tier


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


@router.post('/distributions/second-tier', status_code=201)
def second_tier_create(body: s.SecondTierCreate, key: Key):
    return write('distributions:second-tier', key, body, second_tier.create)


@router.get('/distributions/second-tier/{distribution_id}')
def second_tier_get(distribution_id: UUID, db: DB):
    return second_tier.detail(db, services.get(db, m.SecondTierDistribution, distribution_id))


@router.get('/distributions/second-tier')
def second_tier_list(db: DB, limit: Limit = 50, cursor: UUID | None = None,
                     source_shipment_line_id: UUID | None = None,
                     source_lot_id: UUID | None = None, recipient_party_id: UUID | None = None):
    model = m.SecondTierDistribution
    query = select(model).order_by(model.id).limit(limit + 1)
    for field, value in [('source_shipment_line_id', source_shipment_line_id),
                         ('source_lot_id', source_lot_id), ('recipient_party_id', recipient_party_id)]:
        if value is not None:
            query = query.where(getattr(model, field) == str(value))
    if cursor:
        query = query.where(model.id > str(cursor))
    rows = db.scalars(query).all()
    return {'items': [second_tier.detail(db, row) for row in rows[:limit]],
            'next_cursor': rows[limit - 1].id if len(rows) > limit else None}


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


@router.get('/sales/{sale_id}/profitability')
def sale_profitability(sale_id: UUID, db: DB):
    # One coherent read snapshot across immutable sale and concurrent corrections.
    # This override belongs to this read connection, never a posting transaction.
    db.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
    return sales.profitability(db, services.get(db, m.Sale, sale_id))


@router.post('/shipments', status_code=201)
def shipment_create(body: s.ShipmentCreate, key: Key):
    return write('shipments', key, body, sales.create_shipment)


@router.get('/shipments/{shipment_id}')
def shipment_get(shipment_id: UUID, db: DB):
    return sales.shipment_detail(db, services.get(db, m.Shipment, shipment_id))


@router.post('/transfers', status_code=201)
def transfer_create(body: s.TransferCreate, key: Key):
    return write('transfers', key, body, adjustments.create_transfer)


@router.get('/transfers/{transfer_id}')
def transfer_get(transfer_id: UUID, db: DB):
    return adjustments.transfer_detail(db, services.get(db, m.StockTransfer, transfer_id))


@router.get('/transfers')
def transfer_list(db: DB, limit: Limit = 50, cursor: UUID | None = None, lot_id: UUID | None = None):
    query = select(m.StockTransfer).order_by(m.StockTransfer.id).limit(limit + 1)
    if lot_id:
        query = query.where(m.StockTransfer.lot_id == str(lot_id))
    if cursor:
        query = query.where(m.StockTransfer.id > str(cursor))
    rows = db.scalars(query).all()
    return {'items': [services.entity(row) for row in rows[:limit]],
            'next_cursor': rows[limit - 1].id if len(rows) > limit else None}


@router.post('/returns', status_code=201)
def customer_return_create(body: s.CustomerReturnCreate, key: Key):
    return write('returns', key, body, adjustments.create_return)


@router.get('/returns/{return_id}')
def customer_return_get(return_id: UUID, db: DB):
    return adjustments.return_detail(db, services.get(db, m.CustomerReturn, return_id))


@router.get('/returns')
def customer_return_list(db: DB, limit: Limit = 50, cursor: UUID | None = None, sale_id: UUID | None = None):
    query = select(m.CustomerReturn).order_by(m.CustomerReturn.id).limit(limit + 1)
    if sale_id:
        query = query.where(m.CustomerReturn.sale_id == str(sale_id))
    if cursor:
        query = query.where(m.CustomerReturn.id > str(cursor))
    rows = db.scalars(query).all()
    return {'items': [adjustments.correction_summary(row) for row in rows[:limit]],
            'next_cursor': rows[limit - 1].id if len(rows) > limit else None}


@router.post('/sales/{sale_id}/cancel')
def sale_cancel(sale_id: UUID, body: s.SaleCancelCreate, key: Key):
    return write(f'sales:{sale_id}:cancel', key, body,
                 lambda db, payload: adjustments.cancel_sale(db, sale_id, payload), 200)


@router.get('/sales/{sale_id}/cancellation')
def sale_cancellation(sale_id: UUID, db: DB):
    services.get(db, m.Sale, sale_id)
    row = adjustments.cancellation_for(db, sale_id)
    if row is None:
        raise DomainError('NOT_FOUND', 'Satışın iptal kaydı yok', 404)
    return adjustments.cancellation_detail(db, row)


router.add_api_route('/sales', listing(m.Sale, sales.sale_summary), methods=['GET'], name='list_sales')
router.add_api_route('/shipments', listing(m.Shipment), methods=['GET'], name='list_shipments')


@router.get('/lots/{lot_id}/trace')
def lot_trace(lot_id: UUID, db: DB, direction: Literal['forward', 'backward'] = 'forward'):
    return traceability.trace(db, lot_id, direction)


@router.post('/recalls', status_code=201)
def recall_create(body: s.RecallReviewedCreate, key: Key):
    if body.preview_fingerprint is None:
        # Preserve the exact historical canonical body/hash for saved commands.
        body = s.RecallCreate(source_lot_id=body.source_lot_id, reason=body.reason)
    return write('recalls', key, body, recalls.create_recall)


@router.get('/recalls/preview')
def recall_preview(source_lot_id: UUID, db: DB):
    return recalls.preview(db, source_lot_id)


@router.get('/recalls/{recall_id}')
def recall_get(recall_id: UUID, db: DB):
    return recalls.recall_detail(db, recall_id)


@router.post('/recipes', status_code=201)
def recipe_create(body: s.RecipeCreate, key: Key):
    return write('recipes', key, body, cuttings.create_recipe)


@router.get('/recipes/{recipe_id}')
def recipe_get(recipe_id: UUID, db: DB):
    return cuttings.recipe_detail(db, services.get(db, m.RecipeVersion, recipe_id))


@router.post('/recipes/{recipe_id}/availability')
def recipe_availability(recipe_id: UUID, body: s.RecipeAvailability, key: Key):
    return write(f'recipes:{recipe_id}:availability', key, body, lambda db, p: cuttings.set_availability(db, recipe_id, p), 200)


@router.post('/cuttings', status_code=201)
def cutting_create(body: s.CuttingCreate, key: Key):
    return write('cuttings', key, body, cuttings.create_cutting)


@router.get('/cuttings/{cutting_id}')
def cutting_get(cutting_id: UUID, db: DB):
    return cuttings.cutting_detail(db, services.get(db, m.Operation, cutting_id))


@router.post('/cuttings/{cutting_id}/post')
def cutting_post(cutting_id: UUID, body: s.CuttingPost, key: Key):
    return write(f'cuttings:{cutting_id}:post', key, body, lambda db, p: cuttings.post_cutting(db, cutting_id, p), 200)


def cutting_list(db: DB, limit: Limit = 50, cursor: UUID | None = None):
    query = select(m.Operation).where(m.Operation.kind == 'cutting').order_by(m.Operation.id).limit(limit+1)
    if cursor:
        query = query.where(m.Operation.id > str(cursor))
    rows = db.scalars(query).all()
    return {'items': [services.entity(x) for x in rows[:limit]], 'next_cursor': rows[limit-1].id if len(rows) > limit else None}


router.add_api_route('/cuttings', cutting_list, methods=['GET'], name='list_cuttings')


@router.post('/reworks', status_code=201)
def rework_create(body: s.ReworkCreate, key: Key):
    return write('reworks', key, body, reworks.create)


@router.get('/reworks/{rework_id}')
def rework_get(rework_id: UUID, db: DB):
    return reworks.detail(db, services.get(db, m.Operation, rework_id))


@router.post('/reworks/{rework_id}/post')
def rework_post(rework_id: UUID, body: s.ReworkPost, key: Key):
    return write(f'reworks:{rework_id}:post', key, body,
                 lambda db, payload: reworks.post(db, rework_id, payload), 200)


@router.get('/reworks')
def rework_list(db: DB, limit: Limit = 50, cursor: UUID | None = None):
    query = select(m.Operation).where(m.Operation.kind == 'rework').order_by(m.Operation.id).limit(limit + 1)
    if cursor:
        query = query.where(m.Operation.id > str(cursor))
    rows = db.scalars(query).all()
    return {'items': [services.entity(row) for row in rows[:limit]],
            'next_cursor': rows[limit - 1].id if len(rows) > limit else None}


@router.get('/recipes')
def recipe_list(db: DB, limit: Limit = 50, cursor: UUID | None = None):
    query = select(m.RecipeVersion).order_by(m.RecipeVersion.id).limit(limit+1)
    if cursor:
        query = query.where(m.RecipeVersion.id > str(cursor))
    rows = db.scalars(query).all()
    return {'items': [cuttings.recipe_detail(db, x) for x in rows[:limit]], 'next_cursor': rows[limit-1].id if len(rows) > limit else None}


# Only descriptive master fields are editable. All writes keep execute()'s
# transaction, bounded deadlock retry and method-specific idempotency scope.
from app import master_data


@router.get('/products/{record_id}')
def product_get(record_id: UUID, db: DB):
    return services.entity(services.get(db, m.Product, record_id))


@router.patch('/products/{record_id}')
def product_update(record_id: UUID, body: s.MasterNameUpdate, key: Key):
    return write(f'products:{record_id}:patch', key, body, lambda db, p: master_data.update(db, m.Product, record_id, p), 200)


@router.delete('/products/{record_id}')
def product_delete(record_id: UUID, key: Key, body: s.MasterDelete = s.MasterDelete()):
    return write(f'products:{record_id}:delete', key, body, lambda db, _: master_data.delete(db, m.Product, record_id), 200)


@router.get('/parties/{record_id}')
def party_get(record_id: UUID, db: DB):
    return services.entity(services.get(db, m.Party, record_id))


@router.patch('/parties/{record_id}')
def party_update(record_id: UUID, body: s.PartyUpdate, key: Key):
    return write(f'parties:{record_id}:patch', key, body, lambda db, p: master_data.update(db, m.Party, record_id, p), 200)


@router.delete('/parties/{record_id}')
def party_delete(record_id: UUID, key: Key, body: s.MasterDelete = s.MasterDelete()):
    return write(f'parties:{record_id}:delete', key, body, lambda db, _: master_data.delete(db, m.Party, record_id), 200)


@router.get('/locations/{record_id}')
def location_get(record_id: UUID, db: DB):
    return services.entity(services.get(db, m.Location, record_id))


@router.patch('/locations/{record_id}')
def location_update(record_id: UUID, body: s.MasterNameUpdate, key: Key):
    return write(f'locations:{record_id}:patch', key, body, lambda db, p: master_data.update(db, m.Location, record_id, p), 200)


@router.delete('/locations/{record_id}')
def location_delete(record_id: UUID, key: Key, body: s.MasterDelete = s.MasterDelete()):
    return write(f'locations:{record_id}:delete', key, body, lambda db, _: master_data.delete(db, m.Location, record_id), 200)
