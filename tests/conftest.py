from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import os
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import delete, select


@pytest.fixture(scope='session')
def mysql_core_engine():
    from app.config import get_settings
    from app.database import get_engine
    from app.models import Base
    settings = get_settings()
    if not settings.mysql_database.endswith('_test'):
        pytest.fail('Destructive core tests require a separate MYSQL_DATABASE ending in _test')
    engine = get_engine()
    config = Config(str(Path(__file__).resolve().parents[1] / 'backend/alembic.ini'))
    command.upgrade(config, 'head')
    yield engine
    engine.dispose()
    get_engine.cache_clear()


@pytest.fixture
def mysql_core(mysql_core_engine):
    from app.models import Base
    # Only the explicitly selected *_test database is cleared, never avatar.
    with mysql_core_engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            if table.name == 'stock_movements':
                # InnoDB checks self-FKs row by row. Remove synthetic reversal
                # leaves before their originals, without disabling any FK.
                reversals = dict(connection.execute(select(table.c.id, table.c.reversal_of)
                                  .where(table.c.reversal_of.is_not(None))).all())
                while reversals:
                    leaves = set(reversals) - set(reversals.values())
                    if not leaves:
                        pytest.fail('Cyclic test reversal records; cleanup refused')
                    connection.execute(delete(table).where(table.c.id.in_(leaves)))
                    for identifier in leaves:
                        reversals.pop(identifier)
            connection.execute(delete(table))
    return mysql_core_engine


@pytest.fixture
def core_client(mysql_core, monkeypatch):
    from app.config import get_settings
    from app.main import app
    monkeypatch.setenv('AVATAR_API_KEY', 'test-key-only-not-a-production-credential')
    get_settings.cache_clear()
    with TestClient(app, headers={'X-API-Key': 'test-key-only-not-a-production-credential'}) as client:
        yield client
    get_settings.cache_clear()
