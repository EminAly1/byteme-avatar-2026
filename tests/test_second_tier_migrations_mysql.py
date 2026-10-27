"""Real MySQL upgrade, metadata agreement and refusal of audit-loss downgrade."""
import hashlib

import pytest
from alembic import command
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError, OperationalError

from app import models as m
from test_transfers_returns_migrations_mysql import migration_db, seed_old

pytestmark = pytest.mark.skipif(__import__('os').getenv('AVATAR_CORE_MYSQL_TEST') != '1', reason='Isolated migration DB required')
PARENT='e1307a26b001'
HEAD='f1507a26b001'


def old_tables(engine):
    with engine.connect() as c:
        return {name: hashlib.sha256(repr(sorted(repr(tuple(row)) for row in c.execute(table.select()))).encode()).hexdigest()
                for name,table in m.Base.metadata.tables.items() if name!='second_tier_distributions'}


def seed_shipment(engine):
    with engine.begin() as c:
        c.execute(text("INSERT INTO parties(id,created_at,name,roles) VALUES ('x',NOW(),'KURGUSAL second tier','[\"customer\"]')"))
        c.execute(text("INSERT INTO shipments(id,created_at,customer_id,sale_id,recipient_name,shipped_at) VALUES ('sh',NOW(),'c','s','KURGUSAL first tier',NOW())"))
        c.execute(text("INSERT INTO shipment_lines(id,created_at,shipment_id,line_no,sale_line_id,product_id,lot_id,location_id,stock_movement_id,quantity,unit,consumed_cost) VALUES ('shl',NOW(),'sh',1,'sl','p','l','a','issue',5,'kg',48.5)"))


def insert_evidence(engine, **changes):
    values={'id':'d','line':'shl','customer':'c','lot':'l','product':'p','recipient':'x','quantity':'2','unit':'kg'} | changes
    with engine.begin() as c:
        c.execute(text("INSERT INTO second_tier_distributions(id,created_at,source_shipment_line_id,source_customer_id,source_lot_id,product_id,recipient_party_id,recipient_name,quantity,unit,distributed_at,reference,evidence_note) VALUES (:id,NOW(),:line,:customer,:lot,:product,:recipient,'KURGUSAL snapshot',:quantity,:unit,NOW(),'KURGUSAL-REF','KURGUSAL operator report')"),values)


def test_upgrade_empty_downgrade_and_all_29_old_tables_preserved(migration_db):
    engine,config=migration_db;seed_old(engine);command.upgrade(config,PARENT);seed_shipment(engine)
    before=old_tables(engine);assert len(before)==29
    command.upgrade(config,'head');command.check(config)
    assert old_tables(engine)==before and 'second_tier_distributions' in inspect(engine).get_table_names()
    assert len(inspect(engine).get_foreign_keys('second_tier_distributions'))==5
    command.downgrade(config,PARENT)
    assert 'second_tier_distributions' not in inspect(engine).get_table_names() and old_tables(engine)==before
    command.upgrade(config,'head');command.check(config)


def test_populated_downgrade_refused_before_any_ddl(migration_db):
    engine,config=migration_db;seed_old(engine);command.upgrade(config,'head');seed_shipment(engine);insert_evidence(engine)
    before=old_tables(engine)
    with pytest.raises(RuntimeError,match='audit records exist; destructive downgrade refused'):
        command.downgrade(config,PARENT)
    with engine.connect() as c:
        assert c.scalar(text('SELECT version_num FROM alembic_version'))==HEAD
        assert c.scalar(text('SELECT COUNT(*) FROM second_tier_distributions'))==1
    assert old_tables(engine)==before


@pytest.mark.parametrize('changes',[{'line':'missing'},{'recipient':'missing'},{'lot':'missing'},
                                   {'product':'missing'},{'customer':'missing'},{'quantity':'0'},
                                   {'unit':'package','quantity':'0.5'},{'recipient':'c'}])
def test_new_table_fk_and_check_constraints(migration_db,changes):
    engine,config=migration_db;seed_old(engine);command.upgrade(config,'head');seed_shipment(engine)
    with pytest.raises((IntegrityError, OperationalError)) as caught:
        insert_evidence(engine,**changes)
    assert caught.value.orig.args[0] == (3819 if any(key in changes for key in ('quantity','unit')) or changes.get('recipient')=='c' else 1452)
    with engine.connect() as c:assert c.scalar(text('SELECT COUNT(*) FROM second_tier_distributions'))==0
