"""In-house kg rework using the existing operation, cost and FK lot ledger."""
from datetime import datetime, timezone
from decimal import Decimal

from pydantic import ValidationError
from sqlalchemy import select

from app import models as m, schemas, services
from app.costing import allocate, consumption_cost, quantize
from app.errors import DomainError

POLICIES = {
    'unit': 'kg_only', 'allocation': 'actual_output_kg',
    'loss_cost': 'absorbed_by_all_recorded_outputs',
    'expiry': 'inherit_source_or_shorten_only; unknown_stays_unknown',
    'quarantine': 'separate_quality_release_and_valuation_required',
    'cost_basis': 'incremental_original_lot_consumption_plus_explicit_actual_services',
    'lot_link': 'full_consumed_kg_allocated_by_actual_output_kg_including_loss',
}


def output_product(db, identifier):
    product = services.get(db, m.Product, identifier)
    if product.base_unit != 'kg' or product.type not in ('finished', 'byproduct'):
        raise DomainError('REWORK_OUTPUT_KG_REQUIRED', 'Rework çıktısı kg mamul/yan ürün olmalı', 422)
    return product


def eligible_source(db, plan):
    lot = services.lock_lots(db, [plan.source_lot_id])[str(plan.source_lot_id)]
    location = services.get(db, m.Location, plan.source_location_id)
    if location.kind == 'quarantine':
        raise DomainError('REWORK_QUALITY_RELEASE_REQUIRED', 'Karantina için ayrı kalite onayı ve değerleme gerekir')
    if location.kind != 'warehouse':
        raise DomainError('REWORK_WAREHOUSE_REQUIRED', 'Rework girdisi işletme deposunda olmalı', 422)
    services.usable(lot)
    product = services.get(db, m.Product, lot.product_id)
    if product.base_unit != 'kg' or product.type not in ('finished', 'byproduct'):
        raise DomainError('REWORK_SOURCE_KG_REQUIRED', 'Kaynak kg mamul/yan ürün olmalı', 422)
    origin = db.scalar(select(m.OperationOutput).join(m.Operation, m.Operation.id == m.OperationOutput.operation_id)
                       .where(m.OperationOutput.lot_id == lot.id, m.Operation.status == 'posted',
                              m.Operation.kind.in_(['external_production', 'cutting', 'rework'])))
    if origin is None:
        raise DomainError('REWORK_PRODUCED_SOURCE_REQUIRED', 'Kaynak lotun kesin üretim çıktısı FK kaydı gerekli')
    if origin.quantity != lot.original_quantity or origin.allocated_cost != lot.total_cost:
        raise DomainError('REWORK_SOURCE_LEDGER_MISMATCH', 'Kaynak lot üretim miktar/maliyet kaydıyla uyuşmuyor')
    balance = db.scalar(select(m.StockBalance).where(m.StockBalance.lot_id == lot.id,
                        m.StockBalance.location_id == location.id).with_for_update())
    if balance is None or balance.quantity < plan.input_quantity:
        raise DomainError('INSUFFICIENT_STOCK', 'Kaynak depoda yeterli mamul lot stoğu yok')
    return lot


def detail(db, op):
    if op.kind != 'rework':
        raise DomainError('NOT_FOUND', 'Rework kaydı bulunamadı', 404)
    result = services.operation_detail(db, op)
    result['plan_reference_scope'] = 'draft_proposal_not_posted_genealogy'
    result['differences'] = [services.entity(row) for row in db.scalars(
        select(m.OperationDifference).where(m.OperationDifference.operation_id == op.id).order_by(m.OperationDifference.id))]
    for row in result['outputs']:
        lot = services.get(db, m.Lot, row['lot_id'])
        expiry = lot.expires_at
        row.update(product_id=lot.product_id, lot_code=lot.external_code)
        row['expires_at'] = expiry.isoformat() if expiry else None
    result['outputs'].sort(key=lambda row: (row['product_id'], row['lot_code']))
    return result


def create(db, request):
    eligible_source(db, request)
    for identifier in sorted(request.output_product_ids, key=str):
        # The plan stores IDs in JSON, so hold the parent until its commit.
        services.get(db, m.Product, identifier, lock=True)
        output_product(db, identifier)
    op = m.Operation(code=request.code, kind='rework', allocation_method='quantity',
                     allocation_snapshot={'schema_version': 1, 'type': 'rework_plan',
                                          'plan': request.model_dump(mode='json'), 'policies': dict(POLICIES)})
    db.add(op); db.flush()
    return detail(db, op)


def post(db, identifier, request):
    op = services.draft_operation(db, identifier, kind='rework')
    snapshot = op.allocation_snapshot
    if not isinstance(snapshot, dict) or snapshot.get('type') != 'rework_plan' or snapshot.get('schema_version') != 1:
        raise DomainError('REWORK_PLAN_INVALID', 'Doğrulanmış rework planı gerekli')
    try:
        plan = schemas.ReworkCreate.model_validate(snapshot['plan'])
    except (ValidationError, KeyError, TypeError):
        raise DomainError('REWORK_PLAN_INVALID', 'Rework planı sözleşmeye uymuyor') from None
    if plan.code != op.code:
        raise DomainError('REWORK_PLAN_INVALID', 'Rework kodu ve planı uyuşmuyor')
    # Existing lock protocol: own operation -> sorted source lots -> balances.
    lot = eligible_source(db, plan)
    destination = services.get(db, m.Location, request.output_location_id)
    if destination.kind != 'warehouse':
        raise DomainError('REWORK_WAREHOUSE_REQUIRED', 'Rework çıktısı işletme deposuna kabul edilmeli', 422)
    ordered = sorted(request.outputs, key=lambda item: (str(item.product_id), item.lot_code))
    if {str(x.product_id) for x in ordered} != {str(x) for x in plan.output_product_ids}:
        raise DomainError('REWORK_PLAN_MISMATCH', 'Fiilî çıktı ürünleri planla eşleşmeli', 422)
    expiries = []
    for item in ordered:
        product = output_product(db, item.product_id)
        if product.type == 'byproduct' and not item.explanation:
            raise DomainError('BYPRODUCT_EXPLANATION', 'Yan ürünün açıklaması gerekli', 422)
        if lot.expires_at is None and item.expires_at is not None:
            raise DomainError('REWORK_EXPIRY_EVIDENCE_REQUIRED', 'Kaynak SKT bilinmiyor; yeni SKT için kalite kanıtı gerekli', 422)
        if lot.expires_at and item.expires_at and item.expires_at > lot.expires_at:
            raise DomainError('REWORK_EXPIRY_EXTENSION', 'Rework kaynak SKT tarihini uzatamaz', 422)
        effective = item.expires_at or lot.expires_at
        if effective:
            if effective < datetime.now(timezone.utc).date():
                raise DomainError('REWORK_OUTPUT_EXPIRED', 'Çıktı SKT geçmiş olamaz', 422)
        expiries.append(effective)
    loss = quantize(sum((item.quantity for item in request.differences), Decimal(0)))
    weights = [item.quantity for item in ordered]
    if plan.input_quantity != quantize(sum(weights, Decimal(0)) + loss):
        raise DomainError('MASS_BALANCE', 'Girdi kg = fiilî çıktı kg + açıklanmış fark kg olmalı', 422)
    for item in request.service_costs:
        if item.amount and not item.invoice_reference:
            raise DomainError('REWORK_SERVICE_REFERENCE', 'Pozitif fiilî işlem bedelinin kayıt referansı gerekli', 422)
    material = consumption_cost(lot.total_cost, lot.original_quantity, lot.consumed_quantity, lot.consumed_cost, plan.input_quantity)
    if material < 0:
        raise DomainError('REWORK_SOURCE_LEDGER_MISMATCH', 'Kaynak kümülatif maliyet kaydı tutarsız')
    service = quantize(sum((item.amount for item in request.service_costs), Decimal(0)))
    total = quantize(material + service)
    costs = allocate(total, weights)
    services.move(db, lot.id, str(plan.source_location_id), -plan.input_quantity, 'rework_input', op.id)
    lot.consumed_quantity += plan.input_quantity; lot.consumed_cost += material
    source = m.OperationInput(operation_id=op.id, lot_id=lot.id, location_id=str(plan.source_location_id),
                              quantity=plan.input_quantity, consumed_cost=material)
    db.add(source); db.flush()
    for item, expiry, cost, attributed in zip(ordered, expiries, costs, allocate(plan.input_quantity, weights)):
        if attributed <= 0:
            raise DomainError('LINK_PRECISION', 'Lot bağlantısı miktarı saklama hassasiyetinin altında', 422)
        output = m.Lot(product_id=str(item.product_id), external_code=item.lot_code, received_at=m.now(),
                       expires_at=expiry, original_quantity=item.quantity, total_cost=cost)
        db.add(output); db.flush()
        row = m.OperationOutput(operation_id=op.id, lot_id=output.id, quantity=item.quantity,
                                allocation_weight=item.quantity, allocated_cost=cost, explanation=item.explanation)
        db.add(row); db.flush()
        services.move(db, output.id, destination.id, item.quantity, 'rework_output', op.id)
        db.add(m.LotLink(input_id=source.id, output_id=row.id, attributed_input_quantity=attributed))
    for item in request.differences:
        db.add(m.OperationDifference(operation_id=op.id, **item.model_dump()))
    for item in request.service_costs:
        db.add(m.ServiceCost(operation_id=op.id, **item.model_dump()))
    op.total_material_cost, op.total_service_cost, op.total_cost = material, service, total
    op.loss_quantity = loss
    op.loss_reason = 'Sınıflandırılmış farklar: operation_differences' if loss else None
    op.status, op.posted_at = 'posted', m.now()
    db.flush()
    return detail(db, op)
