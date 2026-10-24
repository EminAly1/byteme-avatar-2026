import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

pytestmark = pytest.mark.skipif(os.getenv('AVATAR_CORE_MYSQL_TEST') != '1', reason='Dedicated *_test MySQL schema required')


def test_upgrade_downgrade_and_metadata_agreement(monkeypatch):
    from app.config import get_settings
    from app.models import Base
    settings = get_settings().model_copy(update={'mysql_database': 'avatar_migration_test'})
    engine = create_engine(settings.database_url())
    monkeypatch.setattr('app.database.get_engine', lambda: engine)
    config = Config(str(Path(__file__).resolve().parents[1] / 'backend/alembic.ini'))
    try:
        command.downgrade(config, 'base')
        command.upgrade(config, 'head')
        assert set(inspect(engine).get_table_names()) == set(Base.metadata.tables) | {'alembic_version'}
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND ENGINE<>'InnoDB'")) == 0
        command.check(config)
        command.downgrade(config, 'base')
        assert inspect(engine).get_table_names() == ['alembic_version']
        command.upgrade(config, 'head')
    finally:
        engine.dispose()
