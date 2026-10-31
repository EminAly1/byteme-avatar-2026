from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal, localcontext
from uuid import uuid4

from sqlalchemy import inspect, select

from app.costing import allocate, consumption_cost, displayed, quantize
from app.errors import DomainError
from app import models as m

ZERO = Decimal('0')


def entity(row):
    def value(v):
        if isinstance(v, Decimal):
            return format(v, '.6f')
        if isinstance(v, datetime):
            return v.replace(tzinfo=timezone.utc).isoformat()
        if isinstance(v, date):
            return v.isoformat()
        return v
    return {c.key: value(getattr(row, c.key)) for c in inspect(type(row)).columns}


def get(db, model, identifier, lock=False):
    query = select(model).where(model.id == str(identifier))
    if lock:
        query = query.with_for_update()
    row = db.scalar(query)
    if row is None:
        raise DomainError('NOT_FOUND', 'Kayıt bulunamadı', 404)
    return row


def require_role(db, party_id, role):
    row = get(db, m.Party, party_id)
    if role not in row.roles:
        raise DomainError('INVALID_PARTY_ROLE', f'{role} rolü gerekli', 422)
    return row


def create_product(db, request):
    row = m.Product(**request.model_dump())
    db.add(row)
    db.flush()
    return entity(row)


def create_party(db, request):
    row = m.Party(**request.model_dump())
    db.add(row)
    db.flush()
    return entity(row)


def create_location(db, request):
    if request.party_id:
        require_role(db, request.party_id, 'producer')
    row = m.Location(name=request.name, kind=request.kind, party_id=str(request.party_id) if request.party_id else None)
    db.add(row)
    db.flush()
    return entity(row)


def counted_quantity(product, quantity):
    if product.base_unit != 'kg' and quantity != quantity.to_integral_value():
        raise DomainError('FRACTIONAL_COUNT', 'Adet/paket miktarı tam sayı olmalıdır', 422)


def weight(db, product_id, quantity, expected_unit=None):
    product = get(db, m.Product, product_id)
    counted_quantity(product, quantity)
    if expected_unit and expected_unit != product.base_unit:
        raise DomainError('UNIT_MISMATCH', 'Ürün birimiyle istek birimi uyuşmuyor', 422)
    factor = Decimal('1') if product.base_unit == 'kg' else product.package_weight_kg
    if factor is None:
        raise DomainError('WEIGHT_CONVERSION_REQUIRED', 'Ürün için kg dönüşümü tanımlı değil', 422)
    with localcontext() as ctx:
        ctx.prec = 48
        result = quantity * factor
    if quantize(result) != result:
        raise DomainError('WEIGHT_PRECISION', 'Ağırlık mikrokg hassasiyetinde olmalıdır', 422)
    return result


def lock_lots(db, ids):
    unique = sorted({str(x) for x in ids})
    rows = db.scalars(select(m.Lot).where(m.Lot.id.in_(unique)).order_by(m.Lot.id).with_for_update().execution_options(populate_existing=True)).all()
    if len(rows) != len(unique):
        raise DomainError('NOT_FOUND', 'Lot bulunamadı', 404)
    return {row.id: row for row in rows}


def usable(lot):
    if lot.blocked:
        raise DomainError('LOT_BLOCKED', 'Lot bloke edilmiş')
    if lot.expires_at and lot.expires_at < datetime.now(timezone.utc).date():
        raise DomainError('LOT_EXPIRED', 'Lot son tüketim tarihi geçmiş')


def move(db, lot_id, location_id, quantity, kind, operation_id=None, receipt_line_id=None, group=None):
    # Every caller must hold the lot row lock. It serializes first-time balances,
    # as well as existing balances across different locations.
    key = (str(lot_id), str(location_id))
    balance = db.scalar(select(m.StockBalance).where(m.StockBalance.lot_id == key[0], m.StockBalance.location_id == key[1]).with_for_update())
    if balance is None:
        balance = m.StockBalance(lot_id=key[0], location_id=key[1], quantity=ZERO)
        db.add(balance)
    result = balance.quantity + quantity
    if result < 0:
        raise DomainError('INSUFFICIENT_STOCK', 'Konumda yeterli lot stoğu yok')
    balance.quantity = quantize(result)
    row = m.StockMovement(lot_id=key[0], location_id=key[1], quantity=quantity, type=kind, operation_id=operation_id, receipt_line_id=receipt_line_id, transfer_group_id=group)
    db.add(row)
    db.flush()
    return row


def receipt_detail(db, row):
    rows = db.execute(select(m.ReceiptLine, m.Product, m.Lot)
        .join(m.Product, m.ReceiptLine.product_id == m.Product.id)
        .join(m.Lot, m.ReceiptLine.lot_id == m.Lot.id)
        .where(m.ReceiptLine.receipt_id == row.id).order_by(m.ReceiptLine.id)).all()
    return {**entity(row), 'supplier_name': get(db, m.Party, row.supplier_id).name,
            'location_name': get(db, m.Location, row.location_id).name,
            'total_cost': format(sum((line.total_cost for line, _, _ in rows), Decimal('0')), '.2f'),
            'lines': [{**entity(line), 'product_name': product.name, 'sku': product.sku,
                       'unit': product.base_unit, 'lot_code': lot.external_code} for line, product, lot in rows]}


def create_receipt(db, request):
    require_role(db, request.supplier_id, 'supplier')
    location = get(db, m.Location, request.location_id)
    if location.kind == 'external_producer':
        raise DomainError('INVALID_LOCATION', 'Alış önce işletme deposuna kaydedilmeli', 422)
    timestamp = request.received_at.astimezone(timezone.utc).replace(tzinfo=None) if request.received_at else m.now()
    receipt = m.Receipt(supplier_id=str(request.supplier_id), location_id=location.id, received_at=timestamp, reference=request.reference)
    db.add(receipt)
    db.flush()
    for line in request.lines:
        product = get(db, m.Product, line.product_id)
        counted_quantity(product, line.quantity)
        if line.unit_price is not None:
            with localcontext() as ctx:
                ctx.prec = 48
                expected = displayed(line.quantity * line.unit_price)
            if expected != displayed(line.total_cost):
                raise DomainError('RECEIPT_PRICE_MISMATCH', 'Miktar × birim fiyat ile doğrulanmış toplam alış tutarı uyuşmuyor', 422)
        lot = m.Lot(product_id=product.id, supplier_id=str(request.supplier_id), external_code=line.external_lot_code, received_at=timestamp, expires_at=line.expires_at, original_quantity=line.quantity, total_cost=line.total_cost)
        db.add(lot)
        db.flush()
        row = m.ReceiptLine(receipt_id=receipt.id, product_id=product.id, lot_id=lot.id, quantity=line.quantity, total_cost=line.total_cost, unit_price=line.unit_price)
        db.add(row)
        db.flush()
        # Newly inserted lots are exclusively owned by this transaction.
        move(db, lot.id, location.id, line.quantity, 'receipt', receipt_line_id=row.id)
    return receipt_detail(db, receipt)


def create_operation(db, request):
    require_role(db, request.producer_id, 'producer')
    row = m.Operation(code=request.code, producer_id=str(request.producer_id), kind=request.kind)
    db.add(row)
    db.flush()
    return operation_detail(db, row)


def draft_operation(db, operation_id, kind='external_production'):
    op = get(db, m.Operation, operation_id, lock=True)
    if op.status != 'draft':
        raise DomainError('OPERATION_POSTED', 'Kapanmış emir değiştirilemez')
    if op.kind != kind:
        raise DomainError('OPERATION_KIND', 'Bu endpoint operasyon türüne uygun değil', 422)
    return op


def dispatch(db, operation_id, request):
    op = draft_operation(db, operation_id)
    source = get(db, m.Location, request.from_location_id)
    target = get(db, m.Location, request.to_location_id)
    if source.kind != 'warehouse' or target.kind != 'external_producer' or target.party_id != op.producer_id:
        raise DomainError('INVALID_LOCATION', 'İşletme deposundan emrin dış üretici konumuna sevk gerekir', 422)
    lots = lock_lots(db, [x.lot_id for x in request.lines])
    movements = []
    for line in sorted(request.lines, key=lambda x: str(x.lot_id)):
        lot = lots[str(line.lot_id)]
        usable(lot)
        counted_quantity(get(db, m.Product, lot.product_id), line.quantity)
        group = str(uuid4())
        for location, quantity, kind in [(source, -line.quantity, 'dispatch_out'), (target, line.quantity, 'dispatch_in')]:
            movements.append(entity(move(db, lot.id, location.id, quantity, kind, op.id, group=group)))
    return {'operation_id': op.id, 'movements': movements}


def operation_detail(db, op):
    inputs = db.scalars(select(m.OperationInput).where(m.OperationInput.operation_id == op.id).order_by(m.OperationInput.id)).all()
    outputs = db.scalars(select(m.OperationOutput).where(m.OperationOutput.operation_id == op.id).order_by(m.OperationOutput.id)).all()
    rendered_outputs = []
    for out in outputs:
        with localcontext() as ctx:
            ctx.prec = 48
            unit_cost = out.allocated_cost/out.quantity
        rendered_outputs.append({**entity(out), 'unit_cost': format(quantize(unit_cost), '.6f'), 'unit_cost_display': displayed(unit_cost)})
    links = []
    if inputs:
        for link in db.scalars(select(m.LotLink).where(m.LotLink.input_id.in_([x.id for x in inputs])).order_by(m.LotLink.id)):
            src = next(x for x in inputs if x.id == link.input_id)
            dst = next(x for x in outputs if x.id == link.output_id)
            links.append({**entity(link), 'input_lot_id': src.lot_id, 'output_lot_id': dst.lot_id})
    return {**entity(op), 'currency': 'EUR', 'total_cost_display': displayed(op.total_cost), 'inputs': [entity(x) for x in inputs], 'outputs': rendered_outputs, 'lot_links': links,
            'service_costs': [entity(x) for x in db.scalars(select(m.ServiceCost).where(m.ServiceCost.operation_id == op.id).order_by(m.ServiceCost.id))]}


def post_operation(db, operation_id, request):
    op = draft_operation(db, operation_id)
    destination = get(db, m.Location, request.output_location_id)
    if destination.kind != 'warehouse':
        raise DomainError('INVALID_LOCATION', 'Mamul kabulü işletme deposuna yapılmalıdır', 422)
    # The operation lock excludes additional dispatches during this snapshot.
    dispatched = defaultdict(Decimal)
    for row in db.scalars(select(m.StockMovement).where(m.StockMovement.operation_id == op.id, m.StockMovement.type == 'dispatch_in')):
        dispatched[(row.lot_id, row.location_id)] += row.quantity
    accounted = defaultdict(Decimal)
    for line in request.consumed_inputs:
        accounted[(str(line.lot_id), str(line.location_id))] += line.quantity
    for line in request.returned_inputs:
        accounted[(str(line.lot_id), str(line.from_location_id))] += line.quantity
    if not dispatched or dict(dispatched) != dict(accounted):
        raise DomainError('DISPATCH_MISMATCH', 'Sevk edilen her lot/konum tüketim veya iadeyle tam açıklanmalıdır', 422)
    lots = lock_lots(db, [key[0] for key in dispatched])
    for lot in lots.values():
        usable(lot)
    input_weight = sum((weight(db, lots[str(x.lot_id)].product_id, x.quantity) for x in request.consumed_inputs), ZERO)
    ordered_outputs = sorted(request.outputs, key=lambda x: (str(x.product_id), x.lot_code))
    weights = [weight(db, x.product_id, x.quantity, x.unit) for x in ordered_outputs]
    if input_weight != sum(weights) + request.loss_quantity:
        raise DomainError('MASS_BALANCE', 'Girdi kg = mamul kg + açıklanmış fark kg olmalıdır', 422)
    for line in ordered_outputs:
        if get(db, m.Product, line.product_id).type == 'raw':
            raise DomainError('INVALID_OUTPUT', 'Üretim çıktısı mamul veya yan ürün olmalıdır', 422)
    inputs = []
    for line in sorted(request.consumed_inputs, key=lambda x: (str(x.lot_id), str(x.location_id))):
        lot = lots[str(line.lot_id)]
        cost = consumption_cost(lot.total_cost, lot.original_quantity, lot.consumed_quantity, lot.consumed_cost, line.quantity)
        move(db, lot.id, str(line.location_id), -line.quantity, 'production_input', op.id)
        lot.consumed_quantity += line.quantity
        lot.consumed_cost += cost
        row = m.OperationInput(operation_id=op.id, lot_id=lot.id, location_id=str(line.location_id), quantity=line.quantity, consumed_cost=cost)
        db.add(row)
        db.flush()
        inputs.append(row)
    for line in sorted(request.returned_inputs, key=lambda x: (str(x.lot_id), str(x.from_location_id))):
        target = get(db, m.Location, line.to_location_id)
        if target.kind not in ('warehouse', 'quarantine'):
            raise DomainError('INVALID_LOCATION', 'İade işletme deposuna/karantinaya yapılmalıdır', 422)
        counted_quantity(get(db, m.Product, lots[str(line.lot_id)].product_id), line.quantity)
        group = str(uuid4())
        move(db, str(line.lot_id), str(line.from_location_id), -line.quantity, 'return_out', op.id, group=group)
        move(db, str(line.lot_id), target.id, line.quantity, 'return_in', op.id, group=group)
    op.total_material_cost = quantize(sum((x.consumed_cost for x in inputs), ZERO))
    op.total_service_cost = quantize(sum((x.amount for x in request.service_costs), ZERO))
    op.total_cost = quantize(op.total_material_cost + op.total_service_cost)
    costs = allocate(op.total_cost, weights)
    outputs = []
    for item, allocation_weight, cost in zip(ordered_outputs, weights, costs):
        lot = m.Lot(product_id=str(item.product_id), external_code=item.lot_code, received_at=m.now(), expires_at=item.expires_at, original_quantity=item.quantity, total_cost=cost)
        db.add(lot)
        db.flush()
        row = m.OperationOutput(operation_id=op.id, lot_id=lot.id, quantity=item.quantity, allocation_weight=allocation_weight, allocated_cost=cost)
        db.add(row)
        db.flush()
        outputs.append(row)
        move(db, lot.id, destination.id, item.quantity, 'production_output', op.id)
    for line in inputs:
        for out, attributed in zip(outputs, allocate(line.quantity, weights)):
            if attributed <= 0:
                raise DomainError('LINK_PRECISION', 'Lot bağlantısı miktarı mevcut hassasiyette saklanamıyor', 422)
            db.add(m.LotLink(input_id=line.id, output_id=out.id, attributed_input_quantity=attributed))
    for item in request.service_costs:
        db.add(m.ServiceCost(operation_id=op.id, **item.model_dump()))
    op.loss_quantity, op.loss_reason = request.loss_quantity, request.loss_reason
    op.status, op.posted_at = 'posted', m.now()
    db.flush()
    return operation_detail(db, op)
