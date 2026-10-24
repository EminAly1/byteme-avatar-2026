"""Cutting migration preserves v3 ledger/recall data across round trips."""
import os
from decimal import Decimal
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text, inspect

from app.config import get_settings

pytestmark=pytest.mark.skipif(os.getenv('AVATAR_CORE_MYSQL_TEST')!='1',reason='Dedicated migration *_test database required')


def test_cutting_upgrade_downgrade_preserves_v3_rows(monkeypatch):
    engine=create_engine(get_settings().model_copy(update={'mysql_database':'avatar_migration_test'}).database_url())
    monkeypatch.setattr('app.database.get_engine',lambda:engine)
    config=Config(str(Path(__file__).resolve().parents[1]/'backend/alembic.ini'))
    try:
        command.downgrade(config,'base');command.upgrade(config,'bacb184a30d7')
        # Raw SQL intentionally uses only columns present before this migration.
        with engine.begin() as c:
            c.execute(text("INSERT INTO products(id,created_at,sku,name,type,base_unit) VALUES ('p',NOW(),'OLD','Before cutting','raw','kg')"))
            c.execute(text("INSERT INTO locations(id,created_at,name,kind) VALUES ('w',NOW(),'Old warehouse','warehouse')"))
            c.execute(text("INSERT INTO lots(id,created_at,product_id,external_code,received_at,blocked,original_quantity,total_cost,consumed_quantity,consumed_cost) VALUES ('l',NOW(),'p','OLD-LAMB',NOW(),true,25,287.50,0,0)"))
            c.execute(text("INSERT INTO stock_balances(lot_id,location_id,quantity) VALUES ('l','w',25)"))
            c.execute(text("INSERT INTO stock_movements(id,created_at,lot_id,location_id,quantity,type) VALUES ('m',NOW(),'l','w',25,'receipt')"))
            c.execute(text("INSERT INTO operations(id,created_at,code,kind,status,total_material_cost,total_service_cost,total_cost,loss_quantity,allocation_method) VALUES ('o',NOW(),'OLD-OP','external_production','draft',0,0,0,0,'quantity')"))
            c.execute(text("INSERT INTO recalls(id,created_at,source_lot_id,reason) VALUES ('r',NOW(),'l','Old recall')"))
            c.execute(text("INSERT INTO recall_lots(recall_id,lot_id) VALUES ('r','l')"))
        command.upgrade(config,'head');command.check(config)
        assert {'recipe_versions','recipe_lines','operation_differences'} <= set(inspect(engine).get_table_names())
        with engine.connect() as c:
            assert c.scalar(text("SELECT allocation_snapshot FROM operations WHERE id='o'")) is None
        command.downgrade(config,'bacb184a30d7')
        assert 'recipe_versions' not in inspect(engine).get_table_names()
        with engine.connect() as c:
            assert c.scalar(text("SELECT quantity FROM stock_balances WHERE lot_id='l'"))==25
            assert c.scalar(text("SELECT total_cost FROM lots WHERE id='l'"))==Decimal('287.50')
            assert c.scalar(text("SELECT blocked FROM lots WHERE id='l'"))==1
            assert c.scalar(text("SELECT COUNT(*) FROM recall_lots"))==1
            assert c.scalar(text("SELECT COUNT(*) FROM operations"))==1
        command.upgrade(config,'head');command.check(config)
    finally:engine.dispose()
