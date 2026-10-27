"""Ephemeral customer-facing sale projection. No ledger commands or persistence."""
from datetime import date, datetime, timezone
import hashlib
import json
from typing import Annotated, Literal
import unicodedata
from uuid import UUID
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select

from app import models as m, sales, services
from app.errors import DomainError

STATES = {'active': 'Aktif satış', 'partially_returned': 'Kısmi iade',
          'returned': 'Tam iade', 'cancelled': 'İptal edilmiş satış'}
DISCLAIMERS = {
    'proforma': 'PROFORMA TASLAĞI — RESMÎ FATURA DEĞİLDİR',
    'sale_summary': 'SATIŞ ÖZETİ — MALİ BELGE DEĞİLDİR',
}


def today():
    return datetime.now(ZoneInfo('Europe/Istanbul')).date()


class DraftFields(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    title: str = Field(default='', max_length=120)
    description: str = Field(default='', max_length=600)
    seller_name: str = Field(default='', max_length=200)
    seller_contact: str = Field(default='', max_length=300)
    document_date: date = Field(default_factory=today)
    payment_note: str = Field(default='', max_length=500)
    delivery_note: str = Field(default='', max_length=500)
    note: str = Field(default='', max_length=1500)
    reference: str = Field(default='', max_length=100)
    demo: bool = False

    @field_validator('*', mode='after')
    @classmethod
    def safe_text(cls, value):
        if isinstance(value, str) and any(unicodedata.category(c).startswith('C') and c not in '\n\t' for c in value):
            raise ValueError('Kontrol veya yön değiştirme karakterleri kullanılamaz')
        if isinstance(value, str) and value.count('\n') > 20:
            raise ValueError('Bir taslak alanı en fazla 21 satır olabilir')
        return value


class PdfRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    sale_id: UUID
    kind: Literal['proforma', 'sale_summary'] = 'proforma'
    expected_source_fingerprint: Annotated[str, Field(pattern=r'^[a-f0-9]{64}$')]
    draft: DraftFields = Field(default_factory=DraftFields)


def stamp(value):
    return value.replace(tzinfo=timezone.utc).isoformat()


def source(db, sale_id):
    # A consistent view of sale, subsequent corrections and linked shipments.
    # Session.close rolls back; isolation override is reset on pool return.
    db.autoflush = False
    connection = db.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
    connection.exec_driver_sql('SET TRANSACTION READ ONLY')
    sale = services.get(db, m.Sale, sale_id)
    customer = services.get(db, m.Party, sale.customer_id)
    records = db.execute(select(m.SaleLine, m.Product, m.Lot)
        .join(m.Product, m.Product.id == m.SaleLine.product_id)
        .join(m.Lot, m.Lot.id == m.SaleLine.lot_id)
        .where(m.SaleLine.sale_id == sale.id).order_by(m.SaleLine.line_no)).all()
    # Reuse the existing authoritative correction / net revenue implementation.
    # Its internal cost and profit fields NEVER enter the document projection.
    financial = sales.profitability(db, sale)
    adj = financial['adjustments']
    result = {
        'sale_id': sale.id, 'sold_at': stamp(sale.sold_at), 'currency': sale.currency,
        'customer': {'id': customer.id, 'name': customer.name, 'contact': customer.contact},
        'customer_basis': 'current_party_record_not_historical_billing_snapshot',
        'original_total_eur': format(sale.total_amount, '.2f'),
        'state': adj['state'], 'state_label': STATES[adj['state']],
        'return_credit_eur': adj['return_credit_eur'],
        'cancellation_credit_eur': adj['cancellation_credit_eur'],
        'net_after_adjustments_eur': financial['net_after_adjustments']['net_revenue_eur'],
        'payment_status': 'not_recorded', 'cash_refund_status': adj['cash_refund_status'],
        'tax_information': 'not_recorded',
        'lines': [{'id': line.id, 'line_no': line.line_no, 'product_id': product.id,
                   'product_name': product.name, 'sku': product.sku, 'lot_id': lot.id,
                   'lot_code': lot.external_code, 'quantity': format(line.quantity, '.6f'),
                   'unit': line.unit, 'unit_price_eur': format(line.unit_price, '.2f'),
                   'total_eur': format(line.total_amount, '.2f')} for line, product, lot in records],
        'shipments': [], 'corrections': [],
    }
    headers = db.scalars(select(m.Shipment).where(m.Shipment.sale_id == sale.id).order_by(m.Shipment.id)).all()
    linked = db.scalars(select(m.ShipmentLine).join(m.Shipment, m.Shipment.id == m.ShipmentLine.shipment_id)
                       .where(m.Shipment.sale_id == sale.id).order_by(m.ShipmentLine.line_no)).all()
    for header in headers:
        result['shipments'].append({'id': header.id, 'shipped_at': stamp(header.shipped_at),
            'recipient_name': header.recipient_name, 'recipient_contact': header.recipient_contact,
            'lines': [{'sale_line_id': line.sale_line_id, 'lot_id': line.lot_id,
                       'quantity': format(line.quantity, '.6f'), 'unit': line.unit}
                      for line in linked if line.shipment_id == header.id]})
    for model, line_model, fk, kind, time in [
        (m.CustomerReturn, m.CustomerReturnLine, m.CustomerReturnLine.return_id, 'return', 'returned_at'),
        (m.SaleCancellation, m.SaleCancellationLine, m.SaleCancellationLine.cancellation_id, 'cancellation', 'cancelled_at'),
    ]:
        headers = db.scalars(select(model).where(model.sale_id == sale.id).order_by(model.id)).all()
        lines = db.execute(select(line_model, fk).join(model, model.id == fk)
                           .where(model.sale_id == sale.id).order_by(line_model.id)).all()
        for header in headers:
            result['corrections'].append({'id': header.id, 'kind': kind, 'recorded_at': stamp(getattr(header, time)),
                'reason': header.reason, 'credit_eur': format(header.credit_amount, '.2f'),
                'lines': [{'sale_line_id': line.sale_line_id, 'lot_id': line.lot_id,
                           'quantity': format(line.quantity, '.6f'), 'unit': line.unit,
                           'credit_eur': format(line.credit_amount, '.2f')} for line, parent in lines if parent == header.id]})
    result['source_fingerprint'] = hashlib.sha256(json.dumps(result, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return result


def assert_fresh(data, expected):
    if data['source_fingerprint'] != expected:
        raise DomainError('DOCUMENT_SOURCE_CHANGED', 'Satış, iade veya sevkiyat kaynağı değişti. Önizlemeyi yenileyip tekrar deneyin.', 409)
