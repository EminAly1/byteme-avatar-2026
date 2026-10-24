"""Migration chain preserves pre-sales inventory; never targets a business DB."""
import os
from pathlib import Path
from decimal import Decimal

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from app import models as m
from app.config import get_settings

pytestmark=pytest.mark.skipif(os.getenv('AVATAR_CORE_MYSQL_TEST')!='1',reason='Isolated MySQL migration test only')


def test_sales_upgrade_and_downgrade_preserve_core_inventory(monkeypatch):
    settings=get_settings().model_copy(update={'mysql_database':'avatar_migration_test'})
    engine=create_engine(settings.database_url())
    monkeypatch.setattr('app.database.get_engine',lambda:engine)
    config=Config(str(Path(__file__).resolve().parents[1]/'backend/alembic.ini'))
    try:
        command.downgrade(config,'base');command.upgrade(config,'eeea4b5dd1a8')
        with Session(engine) as db,db.begin():
            product=m.Product(sku='MIG',name='Migration',type='finished',base_unit='package',package_weight_kg=Decimal('1'))
            location=m.Location(name='Test',kind='warehouse')
            db.add_all([product,location]);db.flush()
            lot=m.Lot(product_id=product.id,external_code='MIG-LOT',received_at=m.now(),original_quantity=Decimal('85'),total_cost=Decimal('1543.50'))
            db.add(lot);db.flush()
            lot_id,location_id=lot.id,location.id
            db.add(m.StockBalance(lot_id=lot.id,location_id=location.id,quantity=Decimal('85')))
            db.add(m.StockMovement(lot_id=lot.id,location_id=location.id,quantity=Decimal('85'),type='receipt'))
        command.upgrade(config,'head');command.check(config)
        assert {'sales','sale_lines','shipments','shipment_lines'} <= set(inspect(engine).get_table_names())
        command.downgrade(config,'eeea4b5dd1a8')
        assert 'sales' not in inspect(engine).get_table_names()
        with Session(engine) as db:
            assert db.get(m.Lot,lot_id).total_cost==Decimal('1543.50')
            assert db.get(m.StockBalance,(lot_id,location_id)).quantity==Decimal('85')
        command.upgrade(config,'head');command.check(config)
    finally:engine.dispose()
