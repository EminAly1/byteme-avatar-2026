"""Isolated SQL execution checks, not MySQL integration tests."""
from sqlalchemy import create_engine, event

from app.database import check_database


def test_readiness_executes_select_against_real_sql_connection(monkeypatch):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    statements = []

    @event.listens_for(engine, "before_cursor_execute")
    def record_statement(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    monkeypatch.setattr("app.database.get_engine", lambda: engine)
    try:
        check_database()
        assert statements == ["SELECT 1"]
    finally:
        engine.dispose()
