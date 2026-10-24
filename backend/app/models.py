"""MySQL ledger entities. Schema is installed exclusively through Alembic."""
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Index, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.mysql import DATETIME

from app.database import Base

Q = Numeric(18, 6)
OPTIONS = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Identified:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), default=now)


class Product(Identified, Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("type IN ('raw','finished','byproduct')", name="ck_product_type"),
        CheckConstraint("base_unit IN ('kg','package','unit')", name="ck_product_unit"),
        CheckConstraint("package_weight_kg IS NULL OR package_weight_kg > 0", name="ck_product_weight"), OPTIONS,
    )
    sku: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(24))
    base_unit: Mapped[str] = mapped_column(String(16))
    package_weight_kg: Mapped[Decimal | None] = mapped_column(Q)


class Party(Identified, Base):
    __tablename__ = "parties"
    __table_args__ = OPTIONS
    name: Mapped[str] = mapped_column(String(200))
    roles: Mapped[list] = mapped_column(JSON)
    contact: Mapped[str | None] = mapped_column(String(300))


class Location(Identified, Base):
    __tablename__ = "locations"
    __table_args__ = (
        CheckConstraint("kind IN ('warehouse','external_producer','quarantine')", name="ck_location_kind"), OPTIONS,
    )
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(24))
    party_id: Mapped[str | None] = mapped_column(ForeignKey("parties.id"))


class Lot(Identified, Base):
    __tablename__ = "lots"
    __table_args__ = (
        CheckConstraint("original_quantity > 0", name="ck_lot_original"),
        CheckConstraint("total_cost >= 0", name="ck_lot_cost"),
        CheckConstraint("consumed_quantity >= 0 AND consumed_quantity <= original_quantity", name="ck_lot_consumed"),
        CheckConstraint("consumed_cost >= 0 AND consumed_cost <= total_cost", name="ck_lot_consumed_cost"),
        Index("ix_lots_external_code", "external_code"), OPTIONS,
    )
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"))
    supplier_id: Mapped[str | None] = mapped_column(ForeignKey("parties.id"))
    external_code: Mapped[str] = mapped_column(String(100))
    received_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))
    expires_at: Mapped[date | None] = mapped_column(Date)
    blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    original_quantity: Mapped[Decimal] = mapped_column(Q)
    total_cost: Mapped[Decimal] = mapped_column(Q)
    consumed_quantity: Mapped[Decimal] = mapped_column(Q, default=Decimal("0"))
    consumed_cost: Mapped[Decimal] = mapped_column(Q, default=Decimal("0"))


class Receipt(Identified, Base):
    __tablename__ = "receipts"
    __table_args__ = OPTIONS
    supplier_id: Mapped[str] = mapped_column(ForeignKey("parties.id"))
    location_id: Mapped[str] = mapped_column(ForeignKey("locations.id"))
    received_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))
    reference: Mapped[str | None] = mapped_column(String(100))


class ReceiptLine(Identified, Base):
    __tablename__ = "receipt_lines"
    __table_args__ = (CheckConstraint("quantity > 0 AND total_cost >= 0", name="ck_receipt_values"), OPTIONS)
    receipt_id: Mapped[str] = mapped_column(ForeignKey("receipts.id"))
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"))
    lot_id: Mapped[str] = mapped_column(ForeignKey("lots.id"), unique=True)
    quantity: Mapped[Decimal] = mapped_column(Q)
    total_cost: Mapped[Decimal] = mapped_column(Q)


class Operation(Identified, Base):
    __tablename__ = "operations"
    __table_args__ = (
        CheckConstraint("kind IN ('external_production','cutting','rework')", name="ck_operation_kind"),
        CheckConstraint("status IN ('draft','posted')", name="ck_operation_status"),
        CheckConstraint("total_material_cost >= 0 AND total_service_cost >= 0 AND total_cost >= 0 AND loss_quantity >= 0", name="ck_operation_values"), OPTIONS,
    )
    code: Mapped[str] = mapped_column(String(100), unique=True)
    kind: Mapped[str] = mapped_column(String(24), default="external_production")
    producer_id: Mapped[str | None] = mapped_column(ForeignKey("parties.id"))
    status: Mapped[str] = mapped_column(String(16), default="draft")
    posted_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6))
    total_material_cost: Mapped[Decimal] = mapped_column(Q, default=Decimal("0"))
    total_service_cost: Mapped[Decimal] = mapped_column(Q, default=Decimal("0"))
    total_cost: Mapped[Decimal] = mapped_column(Q, default=Decimal("0"))
    loss_quantity: Mapped[Decimal] = mapped_column(Q, default=Decimal("0"))
    loss_reason: Mapped[str | None] = mapped_column(String(500))
    allocation_method: Mapped[str] = mapped_column(String(16), default="quantity")


class OperationInput(Identified, Base):
    __tablename__ = "operation_inputs"
    __table_args__ = (
        UniqueConstraint("operation_id", "lot_id", "location_id", name="uq_operation_input"),
        CheckConstraint("quantity > 0 AND consumed_cost >= 0", name="ck_input_values"), OPTIONS,
    )
    operation_id: Mapped[str] = mapped_column(ForeignKey("operations.id"))
    lot_id: Mapped[str] = mapped_column(ForeignKey("lots.id"))
    location_id: Mapped[str] = mapped_column(ForeignKey("locations.id"))
    quantity: Mapped[Decimal] = mapped_column(Q)
    consumed_cost: Mapped[Decimal] = mapped_column(Q)


class OperationOutput(Identified, Base):
    __tablename__ = "operation_outputs"
    __table_args__ = (CheckConstraint("quantity > 0 AND allocation_weight > 0 AND allocated_cost >= 0", name="ck_output_values"), OPTIONS)
    operation_id: Mapped[str] = mapped_column(ForeignKey("operations.id"))
    lot_id: Mapped[str] = mapped_column(ForeignKey("lots.id"), unique=True)
    quantity: Mapped[Decimal] = mapped_column(Q)
    allocation_weight: Mapped[Decimal] = mapped_column(Q)
    allocated_cost: Mapped[Decimal] = mapped_column(Q)


class LotLink(Identified, Base):
    __tablename__ = "lot_links"
    __table_args__ = (
        UniqueConstraint("input_id", "output_id", name="uq_lot_link"),
        CheckConstraint("attributed_input_quantity > 0", name="ck_link_quantity"), OPTIONS,
    )
    input_id: Mapped[str] = mapped_column(ForeignKey("operation_inputs.id"))
    output_id: Mapped[str] = mapped_column(ForeignKey("operation_outputs.id"))
    attributed_input_quantity: Mapped[Decimal] = mapped_column(Q)


class ServiceCost(Identified, Base):
    __tablename__ = "service_costs"
    __table_args__ = (CheckConstraint("amount >= 0 AND currency = 'EUR'", name="ck_service_amount"), OPTIONS)
    operation_id: Mapped[str] = mapped_column(ForeignKey("operations.id"))
    amount: Mapped[Decimal] = mapped_column(Q)
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    invoice_reference: Mapped[str | None] = mapped_column(String(100))


class StockBalance(Base):
    __tablename__ = "stock_balances"
    __table_args__ = (CheckConstraint("quantity >= 0", name="ck_balance_nonnegative"), OPTIONS)
    lot_id: Mapped[str] = mapped_column(ForeignKey("lots.id"), primary_key=True)
    location_id: Mapped[str] = mapped_column(ForeignKey("locations.id"), primary_key=True)
    quantity: Mapped[Decimal] = mapped_column(Q)


class StockMovement(Identified, Base):
    __tablename__ = "stock_movements"
    __table_args__ = (
        CheckConstraint("quantity <> 0", name="ck_movement_nonzero"),
        Index("ix_movement_lot_location", "lot_id", "location_id", "id"),
        Index("ix_movement_operation", "operation_id"), OPTIONS,
    )
    lot_id: Mapped[str] = mapped_column(ForeignKey("lots.id"))
    location_id: Mapped[str] = mapped_column(ForeignKey("locations.id"))
    quantity: Mapped[Decimal] = mapped_column(Q)
    type: Mapped[str] = mapped_column(String(32))
    operation_id: Mapped[str | None] = mapped_column(ForeignKey("operations.id"))
    receipt_line_id: Mapped[str | None] = mapped_column(ForeignKey("receipt_lines.id"))
    transfer_group_id: Mapped[str | None] = mapped_column(String(36))
    reversal_of: Mapped[str | None] = mapped_column(ForeignKey("stock_movements.id"))


class IdempotencyRequest(Base):
    __tablename__ = "idempotency_requests"
    __table_args__ = OPTIONS
    scope: Mapped[str] = mapped_column(String(128), primary_key=True)
    key: Mapped[str] = mapped_column(String(36), primary_key=True)
    request_hash: Mapped[str] = mapped_column(String(64))
    http_status: Mapped[int] = mapped_column(default=0)
    response: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), default=now)


class Sale(Identified, Base):
    __tablename__ = "sales"
    __table_args__ = (
        CheckConstraint("currency = 'EUR' AND total_amount >= 0", name="ck_sale_amount"),
        Index("ix_sale_customer", "customer_id", "id"), OPTIONS,
    )
    customer_id: Mapped[str] = mapped_column(ForeignKey("parties.id"))
    sold_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))


class SaleLine(Identified, Base):
    __tablename__ = "sale_lines"
    __table_args__ = (
        UniqueConstraint("sale_id", "line_no", name="uq_sale_line_number"),
        UniqueConstraint("sale_id", "lot_id", "location_id", name="uq_sale_lot_location"),
        CheckConstraint("line_no > 0 AND quantity > 0 AND unit_price >= 0 AND total_amount >= 0 AND consumed_cost >= 0", name="ck_sale_line_values"),
        CheckConstraint("unit IN ('kg','package','unit')", name="ck_sale_line_unit"),
        Index("ix_sale_line_lot", "lot_id", "sale_id"), OPTIONS,
    )
    sale_id: Mapped[str] = mapped_column(ForeignKey("sales.id"))
    line_no: Mapped[int] = mapped_column()
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"))
    lot_id: Mapped[str] = mapped_column(ForeignKey("lots.id"))
    location_id: Mapped[str] = mapped_column(ForeignKey("locations.id"))
    stock_movement_id: Mapped[str] = mapped_column(ForeignKey("stock_movements.id"), unique=True)
    quantity: Mapped[Decimal] = mapped_column(Q)
    unit: Mapped[str] = mapped_column(String(16))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    consumed_cost: Mapped[Decimal] = mapped_column(Q)


class Shipment(Identified, Base):
    __tablename__ = "shipments"
    __table_args__ = (Index("ix_shipment_customer", "customer_id", "id"), OPTIONS)
    customer_id: Mapped[str] = mapped_column(ForeignKey("parties.id"))
    sale_id: Mapped[str | None] = mapped_column(ForeignKey("sales.id"))
    recipient_name: Mapped[str] = mapped_column(String(200))
    recipient_contact: Mapped[str | None] = mapped_column(String(300))
    shipped_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))


class ShipmentLine(Identified, Base):
    __tablename__ = "shipment_lines"
    __table_args__ = (
        UniqueConstraint("shipment_id", "line_no", name="uq_shipment_line_number"),
        UniqueConstraint("shipment_id", "lot_id", "location_id", name="uq_shipment_lot_location"),
        CheckConstraint("line_no > 0 AND quantity > 0 AND consumed_cost >= 0", name="ck_shipment_line_values"),
        CheckConstraint("unit IN ('kg','package','unit')", name="ck_shipment_line_unit"),
        Index("ix_shipment_line_lot", "lot_id", "shipment_id"), OPTIONS,
    )
    shipment_id: Mapped[str] = mapped_column(ForeignKey("shipments.id"))
    line_no: Mapped[int] = mapped_column()
    sale_line_id: Mapped[str | None] = mapped_column(ForeignKey("sale_lines.id"), unique=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"))
    lot_id: Mapped[str] = mapped_column(ForeignKey("lots.id"))
    location_id: Mapped[str] = mapped_column(ForeignKey("locations.id"))
    stock_movement_id: Mapped[str] = mapped_column(ForeignKey("stock_movements.id"), unique=True)
    quantity: Mapped[Decimal] = mapped_column(Q)
    unit: Mapped[str] = mapped_column(String(16))
    consumed_cost: Mapped[Decimal] = mapped_column(Q)
