from sqlalchemy import select
import pytest
from app import demo_catalog, models as m
from app.config import get_settings
from test_transfers_returns_mysql import snapshot


def test_catalog_guard_refuses_business_or_unconfirmed_database_before_connecting(monkeypatch):
    monkeypatch.setenv('MYSQL_DATABASE','avatar');get_settings.cache_clear()
    monkeypatch.setattr(demo_catalog,'get_engine',lambda:pytest.fail('Must refuse before opening DB'))
    try:
        with pytest.raises(SystemExit):demo_catalog.seed_catalog('avatar')
    finally:get_settings.cache_clear()


def test_demo_catalog_is_bounded_linked_and_second_run_creates_nothing(mysql_core):
    database=get_settings().mysql_database
    with pytest.raises(SystemExit):demo_catalog.seed_catalog('wrong_test')
    result=demo_catalog.seed_catalog(database)
    assert len(result['products'])==11<=30
    assert len([p for p in result['products'] if p['base_unit']=='kg' and p['type']=='finished'])==5
    assert all(p['sku'].startswith('DEMO28-') and p['name'].startswith('DEMO ') for p in result['products'])
    assert {l['product_id'] for l in result['recipe']['lines']}<={p['id'] for p in result['products']}
    assert result['financial_tables_unchanged']
    with mysql_core.connect() as c:
        for model in [m.Receipt,m.Lot,m.StockMovement,m.Sale,m.Operation]:assert c.execute(select(model.id)).first() is None
    before=snapshot(mysql_core);again=demo_catalog.seed_catalog(database)
    assert again==result and snapshot(mysql_core)==before
