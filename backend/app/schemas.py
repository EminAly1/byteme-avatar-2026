"""Decimal values must arrive as JSON strings; no binary float conversion."""
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, BeforeValidator, ConfigDict, Field, model_validator


def decimal_string(value):
    if not isinstance(value, (str, Decimal)):
        raise ValueError("Ondalık değer JSON string olmalıdır")
    return value


DecimalValue = Annotated[Decimal, BeforeValidator(decimal_string), Field(max_digits=18, decimal_places=6, ge=0, le=Decimal('999999999999.999999'))]
PositiveQuantity = Annotated[DecimalValue, Field(gt=0)]
Money = Annotated[DecimalValue, Field(decimal_places=2)]
Name = Annotated[str, Field(min_length=1, max_length=200)]
Code = Annotated[str, Field(min_length=1, max_length=100)]


class Schema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ProductCreate(Schema):
    sku: Annotated[str, Field(min_length=1, max_length=64)]
    name: Name
    type: Literal['raw', 'finished', 'byproduct']
    base_unit: Literal['kg', 'package', 'unit']
    package_weight_kg: PositiveQuantity | None = None

    @model_validator(mode='after')
    def validate_conversion(self):
        if (self.base_unit == 'package') != (self.package_weight_kg is not None):
            raise ValueError('Paket ürünü için pozitif package_weight_kg gerekir; diğer birimlerde kullanılamaz')
        return self


class PartyCreate(Schema):
    name: Name
    roles: Annotated[list[Literal['supplier', 'producer', 'customer']], Field(min_length=1, max_length=3)]
    contact: Annotated[str, Field(max_length=300)] | None = None

    @model_validator(mode='after')
    def unique_roles(self):
        if len(set(self.roles)) != len(self.roles):
            raise ValueError('Roller tekrarlanamaz')
        return self


class LocationCreate(Schema):
    name: Name
    kind: Literal['warehouse', 'external_producer', 'quarantine'] = 'warehouse'
    party_id: UUID | None = None

    @model_validator(mode='after')
    def external_owner(self):
        if (self.kind == 'external_producer') != (self.party_id is not None):
            raise ValueError('Dış üretici konumu producer party_id gerektirir; diğer konumlar gerektirmez')
        return self


class ReceiptItem(Schema):
    product_id: UUID
    external_lot_code: Code
    quantity: PositiveQuantity
    total_cost: Money
    expires_at: date | None = None


class ReceiptCreate(Schema):
    supplier_id: UUID
    location_id: UUID
    received_at: AwareDatetime | None = None
    reference: Code | None = None
    lines: Annotated[list[ReceiptItem], Field(min_length=1, max_length=100)]


class OperationCreate(Schema):
    code: Code
    kind: Literal['external_production'] = 'external_production'
    producer_id: UUID


class LotQuantity(Schema):
    lot_id: UUID
    quantity: PositiveQuantity


class DispatchCreate(Schema):
    from_location_id: UUID
    to_location_id: UUID
    lines: Annotated[list[LotQuantity], Field(min_length=1, max_length=100)]

    @model_validator(mode='after')
    def unique_lots(self):
        if len({x.lot_id for x in self.lines}) != len(self.lines):
            raise ValueError('Aynı lot tek satırda olmalıdır')
        return self


class ConsumedInput(LotQuantity):
    location_id: UUID


class ReturnedInput(LotQuantity):
    from_location_id: UUID
    to_location_id: UUID


class OutputItem(Schema):
    product_id: UUID
    lot_code: Code
    quantity: PositiveQuantity
    unit: Literal['kg', 'package', 'unit'] | None = None
    expires_at: date | None = None


class ServiceItem(Schema):
    amount: Money
    currency: Literal['EUR'] = 'EUR'
    invoice_reference: Code | None = None


class OperationPost(Schema):
    consumed_inputs: Annotated[list[ConsumedInput], Field(min_length=1, max_length=100)]
    returned_inputs: Annotated[list[ReturnedInput], Field(max_length=100)] = Field(default_factory=list)
    output_location_id: UUID
    outputs: Annotated[list[OutputItem], Field(min_length=1, max_length=100)]
    service_costs: Annotated[list[ServiceItem], Field(max_length=100)] = Field(default_factory=list)
    allocation_method: Literal['quantity'] = 'quantity'
    loss_quantity: DecimalValue
    loss_reason: Annotated[str, Field(min_length=1, max_length=500)] | None = None

    @model_validator(mode='after')
    def validate_lines(self):
        keys = [(x.lot_id, x.location_id) for x in self.consumed_inputs]
        if len(set(keys)) != len(keys):
            raise ValueError('Tüketilen lot/konum satırı tekrarlanamaz')
        keys = [(x.lot_id, x.from_location_id) for x in self.returned_inputs]
        if len(set(keys)) != len(keys):
            raise ValueError('İade lot/konum satırı tekrarlanamaz')
        if len({(x.product_id, x.lot_code) for x in self.outputs}) != len(self.outputs):
            raise ValueError('Çıktı ürün/lot kodu tekrarlanamaz')
        if self.loss_quantity and not self.loss_reason:
            raise ValueError('Miktar farkı için loss_reason gerekir')
        return self
