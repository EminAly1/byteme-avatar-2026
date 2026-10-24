from decimal import Decimal as D

import pytest
from app.costing import allocate, consumption_cost, displayed, quantize
from app.errors import DomainError


def test_required_ekp_without_reconstructing_total_from_display():
    materials = D('970') + D('48') + D('58')
    total = materials + D('467.50')
    assert total == D('1543.50')
    assert displayed(total / D('85')) == '18.16'
    assert D('18.16') * D('85') != total
    assert sum(allocate(total, [D('30'), D('25'), D('30')])) == total


def test_tiny_rounding_remainders_never_go_negative():
    result = allocate(D('0.000002'), [D('1')]*4)
    assert sum(result) == D('0.000002')
    assert all(x >= 0 for x in result)


def test_partial_consumption_keeps_last_cost_remainder():
    q, cost = D('0'), D('0')
    for _ in range(3):
        portion = consumption_cost(D('1'), D('3'), q, cost, D('1'))
        q += 1
        cost += portion
    assert cost == D('1')


@pytest.mark.parametrize('weights', [[], [D('0')], [D('-1')]])
def test_invalid_allocation_rejected(weights):
    with pytest.raises(DomainError):
        allocate(D('1'), weights)


def test_decimal_overflow_rejected_before_database():
    with pytest.raises(DomainError, match='DECIMAL'):
        quantize(D('1000000000000'))
