"""Append-only operator reports, not external stock or a second company issue."""
from decimal import Decimal

from sqlalchemy import func, select

from app import models as m, services
from app.errors import DomainError
from app.sales import utc_timestamp

ZERO = Decimal('0')


def totals(db, line_id):
    """Caller holds ShipmentLine FOR UPDATE after sale -> sorted lot locks."""
    distributed, last_distribution = db.execute(select(
        func.sum(m.SecondTierDistribution.quantity), func.max(m.SecondTierDistribution.distributed_at)
    ).where(m.SecondTierDistribution.source_shipment_line_id == line_id)).one()
    returned, last_return = db.execute(select(
        func.sum(m.CustomerReturnLine.quantity), func.max(m.CustomerReturn.returned_at)
    ).join(m.CustomerReturn, m.CustomerReturn.id == m.CustomerReturnLine.return_id)
      .where(m.CustomerReturnLine.shipment_line_id == line_id)).one()
    return distributed or ZERO, returned or ZERO, max(
        [value for value in (last_distribution, last_return) if value is not None], default=None)


def validate_capacity(db, line, quantity, timestamp, *, returning=False):
    distributed, returned, latest = totals(db, line.id)
    if returning and not distributed:
        return  # Existing return validation owns the unchanged no-distribution case.
    if distributed + returned + quantity > line.quantity:
        raise DomainError('DOCUMENTED_QUANTITY_EXCEEDED',
                          'İade ve ikinci kademe toplamı kaynak sevkiyat miktarını aşamaz')
    # Old returns without any second-tier claims retain their prior contract.
    # Once mixed evidence exists, require chronological, disjoint allocations.
    if latest and timestamp < latest and (not returning or distributed):
        raise DomainError('DISTRIBUTION_CHRONOLOGY_CONFLICT',
                          'İade/dağıtım bildirimi son kayıtlı olaydan önceye alınamaz; belge düzeltmesi gerekir')


def validate_return(db, line, quantity, timestamp):
    # create_return already owns sale -> sorted lots. Use the same final claim
    # lock as distribution; never acquire Sale after Lot or ShipmentLine.
    locked = services.get(db, m.ShipmentLine, line.id, lock=True)
    validate_capacity(db, locked, quantity, timestamp, returning=True)


def detail(db, row):
    line = services.get(db, m.ShipmentLine, row.source_shipment_line_id)
    shipment = services.get(db, m.Shipment, line.shipment_id)
    return {**services.entity(row), 'source_shipment_id': shipment.id,
            'source_recipient_snapshot': {'name': shipment.recipient_name, 'contact': shipment.recipient_contact},
            'recording_basis': 'system_operator_report_unverified_by_market',
            'recipient_snapshot_basis': 'party_card_at_recording_time',
            'company_stock_effect': 'none', 'company_financial_effect': 'none',
            'market_remaining_quantity': None, 'final_consumer_sold_quantity': None,
            'recipient_physical_stock_quantity': None}


def source(db, identifier):
    observed = services.get(db, m.ShipmentLine, identifier)
    shipment = services.get(db, m.Shipment, observed.shipment_id)
    keys = (observed.shipment_id, observed.lot_id, shipment.sale_id)
    sale = services.get(db, m.Sale, shipment.sale_id, lock=True) if shipment.sale_id else None
    lot = services.lock_lots(db, [observed.lot_id])[observed.lot_id]
    line = db.scalar(select(m.ShipmentLine).where(m.ShipmentLine.id == str(identifier))
                     .with_for_update().execution_options(populate_existing=True))
    shipment = services.get(db, m.Shipment, line.shipment_id)
    if (line.shipment_id, line.lot_id, shipment.sale_id) != keys:
        raise DomainError('SOURCE_SHIPMENT_MISMATCH', 'Kaynak sevkiyat kilit beklerken değişti')
    product = services.get(db, m.Product, lot.product_id)
    movement = services.get(db, m.StockMovement, line.stock_movement_id)
    valid = (line.product_id == lot.product_id and line.unit == product.base_unit
             and movement.lot_id == lot.id and movement.location_id == line.location_id
             and movement.quantity == -line.quantity and movement.reversal_of is None)
    if sale:
        sold = services.get(db, m.SaleLine, line.sale_line_id) if line.sale_line_id else None
        valid = valid and (sale.customer_id == shipment.customer_id and sold is not None
                           and sold.sale_id == sale.id and sold.lot_id == line.lot_id
                           and sold.product_id == line.product_id and sold.location_id == line.location_id
                           and sold.unit == line.unit and sold.quantity == line.quantity
                           and sold.stock_movement_id == line.stock_movement_id and movement.type == 'sale'
                           and sold.consumed_cost == line.consumed_cost)
        if db.scalar(select(m.SaleCancellation.id).where(m.SaleCancellation.sale_id == sale.id)):
            valid = False
    else:
        valid = valid and line.sale_line_id is None and movement.type == 'shipment'
    if db.scalar(select(m.StockMovement.id).where(m.StockMovement.reversal_of == movement.id)):
        valid = False
    if not valid:
        raise DomainError('SOURCE_SHIPMENT_MISMATCH', 'Sevkiyat müşteri/lot/ürün/satış/hareket kayıtları uyuşmuyor')
    return line, shipment, product


def create(db, request):
    line, shipment, product = source(db, request.source_shipment_line_id)
    recipient = services.get(db, m.Party, request.recipient_party_id)
    if recipient.id == shipment.customer_id:
        raise DomainError('SAME_DISTRIBUTION_RECIPIENT', 'İkinci kademe alıcı kaynak marketten farklı olmalı', 422)
    if request.unit != line.unit:
        raise DomainError('UNIT_MISMATCH', 'Bildirim birimi kaynak sevkiyat birimiyle eşleşmeli', 422)
    services.counted_quantity(product, request.quantity)
    timestamp = utc_timestamp(request.distributed_at)
    if timestamp < shipment.shipped_at:
        raise DomainError('DISTRIBUTION_BEFORE_SHIPMENT', 'Bildirim tarihi kaynak sevkiyattan önce olamaz', 422)
    if timestamp > m.now():
        raise DomainError('DISTRIBUTION_IN_FUTURE', 'Gelecekteki dağıtım kesin olay olarak kaydedilemez', 422)
    validate_capacity(db, line, request.quantity, timestamp)
    row = m.SecondTierDistribution(source_shipment_line_id=line.id, source_customer_id=shipment.customer_id,
        source_lot_id=line.lot_id, product_id=line.product_id, recipient_party_id=recipient.id,
        recipient_name=recipient.name, recipient_contact=recipient.contact, quantity=request.quantity,
        unit=line.unit, distributed_at=timestamp, reference=request.reference, evidence_note=request.evidence_note)
    db.add(row)
    db.flush()
    return detail(db, row)


def report(db, lot_ids):
    from app.lot_graph import rows_for
    rows = rows_for(db, m.SecondTierDistribution, m.SecondTierDistribution.source_lot_id, lot_ids)
    return [detail(db, row) for row in rows]
