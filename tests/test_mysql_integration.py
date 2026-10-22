"""Opt-in real MySQL test; requires configured MYSQL_* and AVATAR_MYSQL_TEST=1."""
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.config import get_settings
from app.database import get_engine
from app.main import app


@pytest.mark.skipif(os.getenv("AVATAR_MYSQL_TEST") != "1", reason="Set AVATAR_MYSQL_TEST=1 for real MySQL integration")
def test_mysql8_and_readiness():
    get_settings.cache_clear()
    get_engine.cache_clear()
    engine = get_engine()
    try:
        with engine.connect() as connection:
            version = connection.scalar(text("SELECT VERSION()"))
            assert version.startswith("8."), version
        response = TestClient(app).get("/health/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "database": "ok"}
    finally:
        engine.dispose()
        get_engine.cache_clear()
        get_settings.cache_clear()
