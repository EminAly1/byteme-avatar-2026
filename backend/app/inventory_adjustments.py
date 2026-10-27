"""Append-only transfers and sale corrections; callers use commands.execute.

Lot consumption counters are historical gross issues, never rewound. Returned
or cancelled quantities/costs are separate recovery records, always quarantined.
There is intentionally no quarantine release/revaluation workflow in this API.
"""
from decimal import Decimal, localcontext
from uuid import uuid4

from sqlalchemy import func, select

from app import models as m, services
from app.costing import quantize
from app.errors import DomainError
from app.sales import cents, utc_timestamp

ZERO = Decimal('0')


def transfer_detail(db, row):
    return {**services.entity(row), 'cost_effect': 'none',
            'movements': [services.entity(services.get(db, m.StockMovement, identifier))
                          for identifier in (row.out_movement_id, row.in_movement_id)]}


def create_transfer(db, request):
    lot = services.lock_lots(db, [request.lot_id])[str(request.lot_id)]
    source = services.get(db, m.Location, request.from_location_id)
    target = services.get(db, m.Location, request.to_location_id)
    if source.id == target.id:
        raise DomainError('SAME_LOCATION', 'Kaynak ve hedef konum aynı olamaz', 422)
    if source.kind == 'external_producer' or target.kind == 'external_producer':
        raise DomainError('INVALID_LOCATION', 'Bağımsız transfer yalnız işletme deposu/karantina arasındadır', 422)
    if source.kind == 'quarantine' and target.kind != 'quarantine':
        raise DomainError('QUARANTINE_RELEASE_REQUIRED', 'Karantinadan çıkış için ayrı kalite ve değerleme onayı gerekir')
    # Blocked/expired goods may only move INTO (or between) quarantine.
    if target.kind != 'quarantine':
        services.usable(lot)
    product = services.get(db, m.Product, lot.product_id)
    services.counted_quantity(product, request.quantity)
    if request.unit != product.base_unit:
        raise DomainError('UNIT_MISMATCH', 'Transfer birimi ürünün stok birimiyle eşleşmelidir', 422)
    timestamp = utc_timestamp(request.transferred_at)
    if timestamp < lot.received_at:
        raise DomainError('TRANSFER_BEFORE_RECEIPT', 'Transfer tarihi lot girişinden önce olamaz', 422)
    identifier = str(uuid4())
    outgoing = services.move(db, lot.id, source.id, -request.quantity, 'transfer_out', group=identifier)
    incoming = services.move(db, lot.id, target.id, request.quantity, 'transfer_in', group=identifier)
    row = m.StockTransfer(id=identifier, lot_id=lot.id, product_id=lot.product_id,
                          from_location_id=source.id, to_location_id=target.id,
                          quantity=request.quantity, unit=product.base_unit,
                          transferred_at=timestamp, reference=request.reference, reason=request.reason,
                          out_movement_id=outgoing.id, in_movement_id=incoming.id)
    db.add(row); db.flush()
    return transfer_detail(db, row)


def correction_summary(row):
    return {**services.entity(row), 'currency': 'EUR',
            'credit_amount': format(row.credit_amount, '.2f'),
            'inventory_status': 'quarantine_only',
            'financial_basis': 'recorded_net_sale_credit_and_cost_reversal',
            'cash_refund_status': 'not_recorded'}


def correction_detail(db, row, line_model, header_column):
    lines = db.scalars(select(line_model).where(header_column == row.id).order_by(line_model.sale_line_id)).all()
    result = correction_summary(row)
    result['lines'] = []
    for line in lines:
        sold = services.get(db, m.SaleLine, line.sale_line_id)
        movement = services.get(db, m.StockMovement, line.stock_movement_id)
        result['lines'].append({**services.entity(line),
                                'credit_amount': format(line.credit_amount, '.2f'),
                                'original_sold_quantity': format(sold.quantity, '.6f'),
                                'original_sale_movement_id': sold.stock_movement_id,
                                'movement': services.entity(movement)})
        if isinstance(line, m.SaleCancellationLine):
            result['lines'][-1]['quarantine_movements'] = [
                services.entity(services.get(db, m.StockMovement, identifier))
                for identifier in (line.quarantine_out_movement_id, line.quarantine_in_movement_id)]
    return result


def return_detail(db, row):
    return correction_detail(db, row, m.CustomerReturnLine, m.CustomerReturnLine.return_id)


def cancellation_detail(db, row):
    return correction_detail(db, row, m.SaleCancellationLine, m.SaleCancellationLine.cancellation_id)


def quarantine(db, identifier):
    location = services.get(db, m.Location, identifier)
    if location.kind != 'quarantine':
        raise DomainError('QUARANTINE_REQUIRED', 'Geri kabul yalnız karantina konumuna yapılabilir', 422)
    return location


def cancellation_for(db, sale_id):
    return db.scalar(select(m.SaleCancellation).where(m.SaleCancellation.sale_id == str(sale_id)))


def return_totals(db, sale_line_id):
    values = db.execute(select(func.sum(m.CustomerReturnLine.quantity),
                               func.sum(m.CustomerReturnLine.credit_amount),
                               func.sum(m.CustomerReturnLine.restored_cost))
                        .where(m.CustomerReturnLine.sale_line_id == str(sale_line_id))).one()
    return tuple(value if value is not None else ZERO for value in values)


def original_sale_movement(db, sold):
    original = services.get(db, m.StockMovement, sold.stock_movement_id)
    if (original.type != 'sale' or original.lot_id != sold.lot_id
            or original.location_id != sold.location_id or original.quantity != -sold.quantity
            or original.reversal_of is not None):
        raise DomainError('SALE_MOVEMENT_MISMATCH', 'Kaynak satışın kesin stok hareketi uyuşmuyor')
    if db.scalar(select(m.StockMovement.id).where(m.StockMovement.reversal_of == original.id)):
        raise DomainError('SALE_MOVEMENT_REVERSED', 'Satış hareketi daha önce terslenmiş')
    return original


def create_return(db, request):
    # Same prefix as linked shipment/cancellation: sale -> sorted lots -> balances.
    sale = services.get(db, m.Sale, request.sale_id, lock=True)
    if cancellation_for(db, sale.id):
        raise DomainError('SALE_CANCELLED', 'İptal edilmiş satış için müşteri iadesi kabul edilemez')
    destination = quarantine(db, request.acceptance_location_id)
    lines = [services.get(db, m.SaleLine, line.sale_line_id) for line in request.lines]
    if any(line.sale_id != sale.id for line in lines):
        raise DomainError('SALE_LINE_MISMATCH', 'İade satırı kaynak satışa ait olmalıdır', 422)
    services.lock_lots(db, [line.lot_id for line in lines])
    timestamp = utc_timestamp(request.returned_at)
    row = m.CustomerReturn(sale_id=sale.id, customer_id=sale.customer_id,
                           acceptance_location_id=destination.id, returned_at=timestamp,
                           reason=request.reason, reference=request.reference)
    db.add(row); db.flush()
    sold_by_id = {line.id: line for line in lines}
    for item in sorted(request.lines, key=lambda x: str(x.sale_line_id)):
        sold = sold_by_id[str(item.sale_line_id)]
        shipped = db.scalar(select(m.ShipmentLine).where(m.ShipmentLine.sale_line_id == sold.id))
        if shipped is None:
            raise DomainError('SALE_LINE_NOT_SHIPPED', 'Müşteri iadesi için kayıtlı bağlı sevkiyat gerekir; sevksiz satışta iptal kullanın')
        shipment = services.get(db, m.Shipment, shipped.shipment_id)
        if (shipment.sale_id != sale.id or shipment.customer_id != sale.customer_id
                or shipped.lot_id != sold.lot_id or shipped.product_id != sold.product_id
                or shipped.quantity != sold.quantity or shipped.unit != sold.unit
                or shipped.stock_movement_id != sold.stock_movement_id):
            raise DomainError('SOURCE_SHIPMENT_MISMATCH', 'Kaynak sevkiyat satış satırı ve hareketiyle uyuşmuyor')
        original_sale_movement(db, sold)
        if timestamp < max(sale.sold_at, shipment.shipped_at):
            raise DomainError('RETURN_BEFORE_DELIVERY', 'İade tarihi satış/sevkiyattan önce olamaz', 422)
        from app.second_tier import validate_return
        validate_return(db, shipped, item.quantity, timestamp)
        product = services.get(db, m.Product, sold.product_id)
        services.counted_quantity(product, item.quantity)
        if item.unit != sold.unit:
            raise DomainError('UNIT_MISMATCH', 'İade birimi kaynak satış birimiyle eşleşmelidir', 422)
        previous, credited, recovered = return_totals(db, sold.id)
        cumulative = previous + item.quantity
        if cumulative > sold.quantity:
            raise DomainError('RETURN_EXCEEDS_SALE', 'Kümülatif iade miktarı satılmış miktarı aşamaz')
        with localcontext() as context:
            context.prec = 48
            credit_target = sold.total_amount if cumulative == sold.quantity else cents(sold.total_amount * cumulative / sold.quantity)
            cost_target = sold.consumed_cost if cumulative == sold.quantity else quantize(sold.consumed_cost * cumulative / sold.quantity)
        credit, cost = credit_target - credited, cost_target - recovered
        movement = services.move(db, sold.lot_id, destination.id, item.quantity, 'customer_return')
        # Partial returns are not full reversals of the original sale movement.
        db.add(m.CustomerReturnLine(return_id=row.id, sale_line_id=sold.id,
                                    shipment_line_id=shipped.id, lot_id=sold.lot_id,
                                    product_id=sold.product_id, stock_movement_id=movement.id,
                                    quantity=item.quantity, unit=sold.unit,
                                    credit_amount=credit, restored_cost=cost))
        row.credit_amount = cents(row.credit_amount + credit)
        row.restored_cost = quantize(row.restored_cost + cost)
        db.flush()
    return return_detail(db, row)


def cancel_sale(db, sale_id, request):
    sale = services.get(db, m.Sale, sale_id, lock=True)
    if cancellation_for(db, sale.id):
        raise DomainError('SALE_ALREADY_CANCELLED', 'Satış daha önce iptal edilmiş')
    lines = db.scalars(select(m.SaleLine).where(m.SaleLine.sale_id == sale.id).order_by(m.SaleLine.id)).all()
    if db.scalar(select(m.Shipment.id).where(m.Shipment.sale_id == sale.id)):
        raise DomainError('SALE_ALREADY_SHIPPED', 'Sevk edilmiş satış iptal edilemez; müşteri iadesi kullanın')
    if db.scalar(select(m.CustomerReturn.id).where(m.CustomerReturn.sale_id == sale.id)):
        raise DomainError('SALE_HAS_RETURNS', 'İade kaydı olan satış iptal edilemez')
    destination = quarantine(db, request.acceptance_location_id)
    services.lock_lots(db, [line.lot_id for line in lines])
    timestamp = utc_timestamp(request.cancelled_at)
    if timestamp < sale.sold_at:
        raise DomainError('CANCEL_BEFORE_SALE', 'İptal tarihi satıştan önce olamaz', 422)
    row = m.SaleCancellation(sale_id=sale.id, customer_id=sale.customer_id,
                             acceptance_location_id=destination.id,
                             cancelled_at=timestamp, reason=request.reason)
    db.add(row); db.flush()
    for sold in lines:
        original = original_sale_movement(db, sold)
        # Exact inverse first: same lot/location and opposite quantity. Then
        # relocate to quarantine in this same uncommitted transaction. Readers
        # never observe a committed saleable intermediate restoration.
        movement = services.move(db, sold.lot_id, original.location_id, sold.quantity, 'sale_cancellation')
        movement.reversal_of = original.id
        line_id = str(uuid4())
        outgoing = services.move(db, sold.lot_id, original.location_id, -sold.quantity, 'cancel_hold_out', group=line_id)
        incoming = services.move(db, sold.lot_id, destination.id, sold.quantity, 'cancel_hold_in', group=line_id)
        db.add(m.SaleCancellationLine(id=line_id, cancellation_id=row.id, sale_line_id=sold.id,
                                      lot_id=sold.lot_id, product_id=sold.product_id,
                                      stock_movement_id=movement.id, quantity=sold.quantity,
                                      quarantine_out_movement_id=outgoing.id,
                                      quarantine_in_movement_id=incoming.id,
                                      unit=sold.unit, credit_amount=sold.total_amount,
                                      restored_cost=sold.consumed_cost))
        row.credit_amount = cents(row.credit_amount + sold.total_amount)
        row.restored_cost = quantize(row.restored_cost + sold.consumed_cost)
        db.flush()
    return cancellation_detail(db, row)


def financial_adjustments(db, sale, lines):
    returned = db.scalars(select(m.CustomerReturn).where(m.CustomerReturn.sale_id == sale.id).order_by(m.CustomerReturn.id)).all()
    cancelled = cancellation_for(db, sale.id)
    credits = sum((row.credit_amount for row in returned), ZERO)
    cost = sum((row.restored_cost for row in returned), ZERO)
    cancelled_credit = cancelled.credit_amount if cancelled else ZERO
    cancelled_cost = cancelled.restored_cost if cancelled else ZERO
    quantities = [return_totals(db, line.id)[0] for line in lines]
    state = ('cancelled' if cancelled else 'returned' if lines and all(q == line.quantity for q, line in zip(quantities, lines))
             else 'partially_returned' if any(quantities) else 'active')
    return {'state': state, 'return_ids': [row.id for row in returned],
            'cancellation_id': cancelled.id if cancelled else None,
            'return_credit_eur': format(credits, '.2f'),
            'cancellation_credit_eur': format(cancelled_credit, '.2f'),
            'cost_reversal_eur': format(cost + cancelled_cost, '.6f'),
            'cash_refund_status': 'not_recorded',
            'lines': [{'sale_line_id': line.id, 'original_sold_quantity': format(line.quantity, '.6f'),
                       'returned_quantity': format(q, '.6f'),
                       'cancelled_quantity': format(line.quantity if cancelled else ZERO, '.6f')}
                      for q, line in zip(quantities, lines)]}
