"""Read-only reporting over actual immutable sale cost snapshots."""
import hashlib
import os
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app import models as m
from test_core_mysql import scenario, post
from test_sales_shipments_mysql import manufactured, sale_body

pytestmark = pytest.mark.skipif(os.getenv('AVATAR_CORE_MYSQL_TEST') != '1', reason='Dedicated *_test MySQL schema required')


def snapshot(engine):
    with engine.connect() as connection:
        return {name: hashlib.sha256('\n'.join(sorted(repr(tuple(row)) for row in connection.execute(table.select()))).encode()).hexdigest()
                for name, table in m.Base.metadata.tables.items()}


def test_real_net_vkp_profit_margin_uses_exact_consumed_cost_without_writes(manufactured, mysql_core):
    s = manufactured
    sale = post(s['client'], '/sales', sale_body(s))
    before = snapshot(mysql_core)
    response = s['client'].get('/v1/sales/' + sale['id'] + '/profitability')
    assert response.status_code == 200
    report = response.json()
    cost = Decimal(sale['lines'][0]['consumed_cost'])
    assert report['net_revenue_eur'] == '750.00'
    assert Decimal(report['recognized_cost_eur']) == cost
    assert Decimal(report['gross_profit_eur']) == Decimal('750.00') - cost
    assert report['lines'][0]['vkp_eur_per_unit'] == '25.00'
    assert Decimal(report['margin_percent']) == ((Decimal('750') - cost) / Decimal('750') * 100).quantize(Decimal('.000001'))
    assert Decimal(report['recognized_cost_eur']) != Decimal('30') * Decimal('18.16')
    assert report['lines'][0]['stock_movement_id'] == sale['lines'][0]['stock_movement_id']
    assert s['client'].get('/v1/sales/' + sale['id'] + '/profitability').json() == report
    assert snapshot(mysql_core) == before


def test_free_sale_keeps_actual_loss_and_undefined_margin(manufactured):
    s = manufactured
    body = sale_body(s, '1'); body['lines'][0]['unit_price'] = '0'
    sale = post(s['client'], '/sales', body)
    report = s['client'].get('/v1/sales/' + sale['id'] + '/profitability').json()
    assert report['net_revenue_eur'] == '0.00'
    assert report['margin_percent'] is None and report['lines'][0]['margin_percent'] is None
    assert Decimal(report['gross_profit_eur']) == -Decimal(sale['lines'][0]['consumed_cost'])


def test_profitability_auth_and_missing_sale(manufactured):
    client = manufactured['client']
    path = '/v1/sales/' + str(uuid4()) + '/profitability'
    assert client.get(path, headers={'X-API-Key': 'invalid'}).status_code == 401
    assert client.get(path).status_code == 404
