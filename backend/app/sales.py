"""Final lot sales and deliveries. All writes run inside commands.execute()."""
from datetime import timezone
from decimal import Decimal, ROUND_HALF_UP, localcontext

from sqlalchemy import select

from app import models as m, services
from app.costing import CENT, consumption_cost, quantize
from app.errors import DomainError


def utc_timestamp(value):
    return value.astimezone(timezone.utc).replace(tzinfo=None) if value else m.now()


def cents(value):
    with localcontext() as context:
        context.prec = 48
        result = value.quantize(CENT, rounding=ROUND_HALF_UP)
    quantize(result)  # Same 12-integer-digit monetary bound as existing APIs.
    return result


def sale_summary(sale):
    result = services.entity(sale)
    result['total_amount'] = format(sale.total_amount, '.2f')
    return result


def sale_detail(db, sale):
    lines = db.scalars(select(m.SaleLine).where(m.SaleLine.sale_id == sale.id).order_by(m.SaleLine.line_no))
    result = sale_summary(sale)
    result['lines'] = []
    for row in lines:
        line = services.entity(row)
        line['unit_price'] = format(row.unit_price, '.2f')
        line['total_amount'] = format(row.total_amount, '.2f')
        result['lines'].append(line)
    return result


def shipment_detail(db, shipment):
    return {**services.entity(shipment), 'lines': [services.entity(row) for row in db.scalars(
        select(m.ShipmentLine).where(m.ShipmentLine.shipment_id == shipment.id).order_by(m.ShipmentLine.line_no))]}


def check_source(db, lot, line):
    # Caller holds the lot lock through commit, including the blocked check.
    services.usable(lot)
    location = services.get(db, m.Location, line.location_id)
    if location.kind != 'warehouse':
        raise DomainError('LOCATION_NOT_SALEABLE', 'Satış ve sevkiyat yalnız işletme deposundan yapılabilir')
    product = services.get(db, m.Product, lot.product_id)
    services.counted_quantity(product, line.quantity)
    if line.unit is not None and line.unit != product.base_unit:
        raise DomainError('UNIT_MISMATCH', 'Miktar birimi ürünün stok birimiyle eşleşmelidir', 422)
    return product


def issue(db, lot, line, kind):
    # Shared cumulative lot cost prevents rounding drift across sales/production.
    cost = consumption_cost(lot.total_cost, lot.original_quantity, lot.consumed_quantity, lot.consumed_cost, line.quantity)
    movement = services.move(db, lot.id, str(line.location_id), -line.quantity, kind)
    lot.consumed_quantity += line.quantity
    lot.consumed_cost += cost
    db.flush()
    return movement, cost


def create_sale(db, request):
    services.require_role(db, request.customer_id, 'customer')
    lots = services.lock_lots(db, [line.lot_id for line in request.lines])
    sale = m.Sale(customer_id=str(request.customer_id), sold_at=utc_timestamp(request.sold_at))
    db.add(sale)
    db.flush()
    total = Decimal('0')
    for number, line in sorted(enumerate(request.lines, 1), key=lambda pair: (str(pair[1].lot_id), str(pair[1].location_id))):
        lot = lots[str(line.lot_id)]
        product = check_source(db, lot, line)
        with localcontext() as context:
            context.prec = 48
            line_total = cents(line.quantity * line.unit_price)
        movement, cost = issue(db, lot, line, 'sale')
        db.add(m.SaleLine(sale_id=sale.id, line_no=number, product_id=product.id,
                          lot_id=lot.id, location_id=str(line.location_id), stock_movement_id=movement.id,
                          quantity=line.quantity, unit=product.base_unit, unit_price=line.unit_price,
                          total_amount=line_total, consumed_cost=cost))
        total += line_total
    sale.total_amount = cents(total)
    db.flush()
    return sale_detail(db, sale)


def linked_sale(db, request):
    if request.sale_id is None:
        return None
    # Prefix lock order for shipment/any future reversal: sale header -> sorted lots.
    sale = services.get(db, m.Sale, request.sale_id, lock=True)
    if sale.customer_id != str(request.customer_id):
        raise DomainError('CUSTOMER_MISMATCH', 'Sevkiyat müşterisi satış müşterisiyle eşleşmelidir', 422)
    return sale


def linked_line(db, sale, line, product):
    sold = services.get(db, m.SaleLine, line.sale_line_id)
    if (sold.sale_id != sale.id or sold.lot_id != str(line.lot_id)
            or sold.location_id != str(line.location_id) or sold.quantity != line.quantity
            or sold.unit != product.base_unit):
        raise DomainError('SALE_LINE_MISMATCH', 'Satış satırı aynı satış/lot/konum/birim ve tam miktarla sevk edilmelidir', 422)
    used = db.scalar(select(m.ShipmentLine.id).where(m.ShipmentLine.stock_movement_id == sold.stock_movement_id))
    if used:
        raise DomainError('SALE_LINE_ALREADY_SHIPPED', 'Satış hareketi daha önce sevkiyata bağlanmış')
    movement = services.get(db, m.StockMovement, sold.stock_movement_id)
    if (movement.type != 'sale' or movement.lot_id != sold.lot_id
            or movement.location_id != sold.location_id or movement.quantity != -sold.quantity):
        raise DomainError('SALE_MOVEMENT_MISMATCH', 'Satışın kesin stok hareketiyle satır uyuşmuyor')
    if db.scalar(select(m.StockMovement.id).where(m.StockMovement.reversal_of == movement.id)):
        raise DomainError('SALE_MOVEMENT_REVERSED', 'Ters hareketi olan satış sevk edilemez')
    return sold, movement


def create_shipment(db, request):
    customer = services.require_role(db, request.customer_id, 'customer')
    sale = linked_sale(db, request)
    lots = services.lock_lots(db, [line.lot_id for line in request.lines])
    timestamp = utc_timestamp(request.shipped_at)
    if sale and timestamp < sale.sold_at:
        raise DomainError('SHIPMENT_BEFORE_SALE', 'Bağlı sevkiyat tarihi satıştan önce olamaz', 422)
    shipment = m.Shipment(customer_id=customer.id, sale_id=sale.id if sale else None,
                          recipient_name=customer.name, recipient_contact=customer.contact,
                          shipped_at=timestamp)
    db.add(shipment)
    db.flush()
    for number, line in sorted(enumerate(request.lines, 1), key=lambda pair: (str(pair[1].lot_id), str(pair[1].location_id))):
        lot = lots[str(line.lot_id)]
        product = check_source(db, lot, line)
        if sale:
            sold, movement = linked_line(db, sale, line, product)
            cost = sold.consumed_cost
        else:
            sold = None
            movement, cost = issue(db, lot, line, 'shipment')
        db.add(m.ShipmentLine(shipment_id=shipment.id, line_no=number,
                              sale_line_id=sold.id if sold else None, product_id=product.id,
                              lot_id=lot.id, location_id=str(line.location_id),
                              stock_movement_id=movement.id, quantity=line.quantity,
                              unit=product.base_unit, consumed_cost=cost))
        db.flush()  # Unique movement/sale-line claims apply before any commit.
    return shipment_detail(db, shipment)
