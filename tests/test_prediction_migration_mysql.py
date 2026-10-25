"""Forecast migration adds one table without rewriting operational data."""
import os
from pathlib import Path
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text, inspect
from app.config import get_settings

pytestmark=pytest.mark.skipif(os.getenv('AVATAR_CORE_MYSQL_TEST')!='1',reason='Dedicated migration *_test schema required')


def test_forecast_migration_preserves_operational_rows(monkeypatch):
    engine=create_engine(get_settings().model_copy(update={'mysql_database':'avatar_migration_test'}).database_url())
    monkeypatch.setattr('app.database.get_engine',lambda:engine)
    config=Config(str(Path(__file__).resolve().parents[1]/'backend/alembic.ini'))
    try:
        command.downgrade(config,'base');command.upgrade(config,'fa8791f3cf0e')
        with engine.begin() as c:
            c.execute(text("INSERT INTO products(id,created_at,sku,name,type,base_unit) VALUES ('old-product',NOW(),'UNCHANGED','Before ML','raw','kg')"))
            before=c.execute(text('SELECT * FROM products')).fetchall()
        command.upgrade(config,'head')
        with engine.connect() as c:assert c.execute(text('SELECT * FROM products')).fetchall()==before
        assert 'prediction_records' in inspect(engine).get_table_names()
        command.check(config)
        command.downgrade(config,'fa8791f3cf0e')
        assert 'prediction_records' not in inspect(engine).get_table_names()
        with engine.connect() as c:assert c.execute(text('SELECT * FROM products')).fetchall()==before
        command.upgrade(config,'head')
    finally:engine.dispose()
