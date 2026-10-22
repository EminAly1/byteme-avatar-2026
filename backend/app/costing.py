"""Exact ledger totals and deterministic remainder allocation."""
from decimal import Decimal, ROUND_HALF_UP, localcontext

from app.errors import DomainError

SIX = Decimal('0.000001')
CENT = Decimal('0.01')
MAX_VALUE = Decimal('999999999999.999999')


def quantize(value: Decimal) -> Decimal:
    with localcontext() as ctx:
        ctx.prec = 48
        result = value.quantize(SIX, rounding=ROUND_HALF_UP)
    if abs(result) > MAX_VALUE:
        raise DomainError('VALUE_OVERFLOW', 'Değer DECIMAL(18,6) sınırını aşıyor', 422)
    return result


def displayed(value: Decimal) -> str:
    return format(value.quantize(CENT, rounding=ROUND_HALF_UP), '.2f')


def allocate(total: Decimal, weights: list[Decimal]) -> list[Decimal]:
    if not weights or any(x <= 0 for x in weights):
        raise DomainError('INVALID_ALLOCATION', 'Pozitif dağıtım ağırlıkları gerekir', 422)
    # Cumulative rounding is monotonic, retains the exact total, and cannot make
    # a negative final line when many small allocations are rounded upwards.
    with localcontext() as ctx:
        ctx.prec = 48
        denominator = sum(weights)
        cumulative = Decimal('0')
        allocated = Decimal('0')
        result = []
        for i, weight in enumerate(weights):
            cumulative += weight
            target = total if i == len(weights)-1 else quantize(total*cumulative/denominator)
            result.append(target-allocated)
            allocated = target
    return result


def consumption_cost(total, original_quantity, previous_quantity, previous_cost, quantity):
    with localcontext() as ctx:
        ctx.prec = 48
        new_quantity = previous_quantity + quantity
        if new_quantity > original_quantity:
            raise DomainError('INSUFFICIENT_STOCK', 'Lot başlangıç miktarı aşılıyor')
        target = total if new_quantity == original_quantity else quantize(total*new_quantity/original_quantity)
        return target-previous_cost
