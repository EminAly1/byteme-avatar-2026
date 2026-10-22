from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.main import app

client = TestClient(app)


def test_liveness_does_not_require_database(monkeypatch):
    def should_not_connect():
        raise AssertionError("Liveness must not connect to MySQL")

    monkeypatch.setattr("app.main.check_database", should_not_connect)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_checks_database(monkeypatch):
    calls = []
    monkeypatch.setattr("app.main.check_database", lambda: calls.append(True))
    response = client.get("/health/ready")
    assert calls == [True]
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_readiness_unavailable_does_not_leak_connection_details(monkeypatch):
    def unavailable():
        raise OperationalError("secret connection string", {}, Exception("secret password"))

    monkeypatch.setattr("app.main.check_database", unavailable)
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert "secret" not in response.text


def test_readiness_reports_missing_configuration(monkeypatch):
    def missing():
        raise ValueError("MYSQL_PASSWORD must be supplied")

    monkeypatch.setattr("app.main.check_database", missing)
    response = client.get("/health/ready")
    assert response.status_code == 503
