"""Migration preserves historical rows and refuses destructive audit loss."""
import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text, delete, select

from app.config import get_settings
from app.models import Base

pytestmark=pytest.mark.skipif(os.getenv('AVATAR_CORE_MYSQL_TEST')!='1',reason='Dedicated migration test DB required')
PARENT='dc9109a1f001'
HEAD='e1307a26b001'
NEW_TABLES={'stock_transfers','customer_returns','customer_return_lines','sale_cancellations','sale_cancellation_lines'}


@pytest.fixture
def migration_db(monkeypatch):
    settings=get_settings().model_copy(update={'mysql_database':'avatar_migration_test'})
    engine=create_engine(settings.database_url());assert engine.url.database=='avatar_migration_test'
    monkeypatch.setattr('app.database.get_engine',lambda:engine)
    config=Config(str(Path(__file__).resolve().parents[1]/'backend/alembic.ini'))
    command.downgrade(config,'base');command.upgrade(config,PARENT)
    try:yield engine,config
    finally:
        # Explicitly purge only this test fixture, not an application downgrade.
        existing=set(inspect(engine).get_table_names())
        with engine.begin() as connection:
            for table in reversed(Base.metadata.sorted_tables):
                if table.name not in existing:continue
                if table.name=='stock_movements':
                    connection.execute(delete(table).where(table.c.reversal_of.is_not(None)))
                connection.execute(delete(table))
        command.downgrade(config,'base');command.upgrade(config,'head');engine.dispose()


def seed_old(engine):
    with engine.begin() as c:
        for statement in [
          "INSERT INTO products(id,created_at,sku,name,type,base_unit) VALUES ('p',NOW(),'OLD','KURGUSAL legacy','raw','kg')",
          "INSERT INTO parties(id,created_at,name,roles) VALUES ('c',NOW(),'KURGUSAL customer','[\"customer\"]')",
          "INSERT INTO locations(id,created_at,name,kind) VALUES ('a',NOW(),'KURGUSAL A','warehouse'),('b',NOW(),'KURGUSAL B','warehouse')",
          "INSERT INTO lots(id,created_at,product_id,external_code,received_at,blocked,original_quantity,total_cost,consumed_quantity,consumed_cost) VALUES ('l',NOW(),'p','KURGUSAL-OLD',NOW(),true,20,194,5,48.5)",
          "INSERT INTO stock_balances(lot_id,location_id,quantity) VALUES ('l','a',15)",
          "INSERT INTO stock_movements(id,created_at,lot_id,location_id,quantity,type) VALUES ('receipt',NOW(),'l','a',20,'receipt'),('issue',NOW(),'l','a',-5,'sale')",
          "INSERT INTO sales(id,created_at,customer_id,sold_at,currency,total_amount) VALUES ('s',NOW(),'c',NOW(),'EUR',100)",
          "INSERT INTO sale_lines(id,created_at,sale_id,line_no,product_id,lot_id,location_id,stock_movement_id,quantity,unit,unit_price,total_amount,consumed_cost) VALUES ('sl',NOW(),'s',1,'p','l','a','issue',5,'kg',20,100,48.5)",
        ]:c.execute(text(statement))


def legacy_snapshot(engine):
    with engine.connect() as c:
        return {name:[tuple(row) for row in c.execute(text('SELECT * FROM '+name+' ORDER BY 1'))]
                for name in ['lots','stock_balances','stock_movements','sales','sale_lines']}


def test_upgrade_downgrade_preserves_old_lot_sale_and_cost(migration_db):
    engine,config=migration_db;seed_old(engine);before=legacy_snapshot(engine)
    command.upgrade(config,'head');command.check(config)
    assert NEW_TABLES<=set(inspect(engine).get_table_names()) and legacy_snapshot(engine)==before
    uniques=inspect(engine).get_unique_constraints('stock_movements')
    assert any(row['column_names']==['reversal_of'] for row in uniques)
    command.downgrade(config,PARENT)
    assert not NEW_TABLES&set(inspect(engine).get_table_names()) and legacy_snapshot(engine)==before
    command.upgrade(config,'head');command.check(config)


def test_duplicate_legacy_reversal_rejects_before_any_ddl(migration_db):
    engine,config=migration_db;seed_old(engine)
    with engine.begin() as c:
        c.execute(text("INSERT INTO stock_movements(id,created_at,lot_id,location_id,quantity,type,reversal_of) VALUES ('r1',NOW(),'l','a',1,'KURGUSAL legacy','issue'),('r2',NOW(),'l','a',1,'KURGUSAL legacy','issue')"))
    before=legacy_snapshot(engine)
    with pytest.raises(RuntimeError,match='Duplicate legacy reversal'):command.upgrade(config,'head')
    assert legacy_snapshot(engine)==before and not NEW_TABLES&set(inspect(engine).get_table_names())
    with engine.connect() as c:assert c.scalar(text('SELECT version_num FROM alembic_version'))==PARENT


def test_posted_transfers_block_destructive_downgrade_before_ddl(migration_db):
    engine,config=migration_db;seed_old(engine);command.upgrade(config,'head')
    with engine.begin() as c:
        c.execute(text("UPDATE stock_balances SET quantity=8 WHERE lot_id='l' AND location_id='a'"))
        c.execute(text("INSERT INTO stock_balances(lot_id,location_id,quantity) VALUES ('l','b',7)"))
        c.execute(text("INSERT INTO stock_movements(id,created_at,lot_id,location_id,quantity,type,transfer_group_id) VALUES ('out',NOW(),'l','a',-7,'transfer_out','t'),('in',NOW(),'l','b',7,'transfer_in','t')"))
        c.execute(text("INSERT INTO stock_transfers(id,created_at,lot_id,product_id,from_location_id,to_location_id,quantity,unit,transferred_at,reason,out_movement_id,in_movement_id) VALUES ('t',NOW(),'l','p','a','b',7,'kg',NOW(),'KURGUSAL transfer','out','in')"))
    before=legacy_snapshot(engine)
    with pytest.raises(RuntimeError,match='destructive downgrade refused'):command.downgrade(config,PARENT)
    assert legacy_snapshot(engine)==before and NEW_TABLES<=set(inspect(engine).get_table_names())
    with engine.connect() as c:
        assert c.scalar(text('SELECT version_num FROM alembic_version'))==HEAD
        assert c.scalar(text('SELECT COUNT(*) FROM stock_transfers'))==1
