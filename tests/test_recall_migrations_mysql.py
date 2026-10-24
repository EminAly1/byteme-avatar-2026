"""MySQL v2 -> v3 -> v2 preserves sales, stock, and safety flags."""
import os
from decimal import Decimal as D
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from app import models as m
from app.config import get_settings

pytestmark = pytest.mark.skipif(os.getenv('AVATAR_CORE_MYSQL_TEST') != '1', reason='Dedicated migration *_test schema only')


def test_recall_upgrade_downgrade_preserves_existing_sales_stock_and_blocks(monkeypatch):
    settings = get_settings().model_copy(update={'mysql_database': 'avatar_migration_test'})
    engine = create_engine(settings.database_url())
    monkeypatch.setattr('app.database.get_engine', lambda: engine)
    config = Config(str(Path(__file__).resolve().parents[1] / 'backend/alembic.ini'))
    try:
        command.downgrade(config, 'base')
        command.upgrade(config, '81f4da20f36b')
        with Session(engine) as db, db.begin():
            product = m.Product(sku='RECALL-MIG', name='Fictional', type='finished', base_unit='kg')
            location = m.Location(name='Isolated', kind='warehouse')
            buyer = m.Party(name='Fictional buyer', roles=['customer'])
            db.add_all([product, location, buyer]); db.flush()
            lot = m.Lot(product_id=product.id, external_code='BEFORE-RECALL', received_at=m.now(), original_quantity=D('5'), total_cost=D('5'))
            db.add(lot); db.flush()
            receipt = m.StockMovement(lot_id=lot.id, location_id=location.id, quantity=D('5'), type='receipt')
            issue = m.StockMovement(lot_id=lot.id, location_id=location.id, quantity=D('-2'), type='sale')
            sale = m.Sale(customer_id=buyer.id, sold_at=m.now(), total_amount=D('4'))
            db.add_all([receipt, issue, sale]); db.flush()
            db.add(m.SaleLine(sale_id=sale.id, line_no=1, product_id=product.id, lot_id=lot.id, location_id=location.id,
                   stock_movement_id=issue.id, quantity=D('2'), unit='kg', unit_price=D('2'), total_amount=D('4'), consumed_cost=D('2')))
            db.add(m.StockBalance(lot_id=lot.id, location_id=location.id, quantity=D('3')))
            lot.consumed_quantity = lot.consumed_cost = D('2')
            lot_id, location_id, sale_id = lot.id, location.id, sale.id
        command.upgrade(config, 'head'); command.check(config)
        assert {'recalls', 'recall_lots'} <= set(inspect(engine).get_table_names())
        with Session(engine) as db, db.begin():
            recall = m.Recall(source_lot_id=lot_id, reason='Migration test'); db.add(recall); db.flush()
            db.add(m.RecallLot(recall_id=recall.id, lot_id=lot_id))
            db.get(m.Lot, lot_id).blocked = True
        command.downgrade(config, '81f4da20f36b')
        assert 'recalls' not in inspect(engine).get_table_names()
        with Session(engine) as db:
            assert db.get(m.Lot, lot_id).blocked  # Downgrade must never silently unblock.
            assert db.get(m.StockBalance, (lot_id,location_id)).quantity == 3
            assert db.get(m.Sale, sale_id).total_amount == 4
        command.upgrade(config, 'head'); command.check(config)
    finally:
        engine.dispose()
