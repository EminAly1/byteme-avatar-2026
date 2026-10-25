"""Explicit pre-process inputs; actual_* fields are forbidden."""
from typing import Literal
from uuid import UUID
from pydantic import model_validator
from app.schemas import Schema, DecimalValue, PositiveQuantity

Part = Literal['leg','shoulder','back','rib','mince']


class ProductionPrediction(Schema):
    operation_id: UUID | None = None
    output_product_id: UUID | None = None
    meat_type: Literal['beef','lamb']
    meat_kg: PositiveQuantity
    spice_kg: PositiveQuantity
    casing_kg: PositiveQuantity
    meat_cost_eur: DecimalValue
    spice_cost_eur: DecimalValue
    casing_cost_eur: DecimalValue
    planned_producer_profile: Literal['producer_a','producer_b','producer_c']
    package_weight_kg: PositiveQuantity
    estimated_service_eur: DecimalValue
    quantity_unit: Literal['package'] = 'package'
    material_unit: Literal['kg'] = 'kg'
    currency: Literal['EUR'] = 'EUR'

    @model_validator(mode='after')
    def attached_product(self):
        if self.operation_id and not self.output_product_id:
            raise ValueError('İşleme bağlı tahminde output_product_id gereklidir')
        return self


class CuttingPrediction(Schema):
    operation_id: UUID | None = None
    recipe_version_id: UUID
    part_products: dict[Part,UUID]
    species: Literal['Kuzu']
    input_weight_kg: PositiveQuantity
    unit: Literal['kg'] = 'kg'

    @model_validator(mode='after')
    def exact_parts(self):
        if set(self.part_products) != {'leg','shoulder','back','rib','mince'} or len(set(self.part_products.values()))!=5:
            raise ValueError('Beş farklı parça ürün kimliği gereklidir')
        return self
