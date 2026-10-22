import pytest
from pydantic import ValidationError

from app.config import Settings


def test_mysql_configuration_uses_environment_and_preserves_special_characters(monkeypatch):
    monkeypatch.setenv("MYSQL_HOST", "db.internal")
    monkeypatch.setenv("MYSQL_PORT", "3307")
    monkeypatch.setenv("MYSQL_PASSWORD", "test@password:/?#")
    settings = Settings()
    url = settings.database_url()
    assert url.host == "db.internal"
    assert url.port == 3307
    assert url.password == "test@password:/?#"
    assert "test@password" not in str(url)
    assert "test@password" not in repr(settings)
    assert url.drivername == "mysql+pymysql"


def test_missing_password_has_no_implicit_secret_default():
    with pytest.raises(ValueError, match="MYSQL_PASSWORD"):
        Settings(mysql_password=None).database_url()


@pytest.mark.parametrize("port", [0, 65536])
def test_invalid_port_rejected(port):
    with pytest.raises(ValidationError):
        Settings(mysql_port=port)
