import pytest
from app.demo_safety import require_local_demo


@pytest.mark.parametrize('database,url', [
    ('avatar', 'http://127.0.0.1:8000'),
    ('avatar_test', 'http://backend:8000'),
    ('avatar_test', 'https://127.0.0.1:8000'),
    ('avatar_test', 'http://operator@127.0.0.1:8000'),
    ('avatar_test', 'http://127.0.0.1:8000/other'),
    ('avatar_test', 'http://127.0.0.1:8000?target=elsewhere'),
    ('avatar_test', 'http://127.0.0.1:99999'),
])
def test_demo_rejects_shared_database_and_non_loopback_targets(monkeypatch, database, url):
    monkeypatch.setenv('MYSQL_DATABASE', database)
    monkeypatch.setenv('AVATAR_API_BASE_URL', url)
    with pytest.raises(SystemExit):
        require_local_demo()


def test_explicit_isolated_local_demo_is_accepted(monkeypatch):
    monkeypatch.setenv('MYSQL_DATABASE', 'avatar_release_demo_test')
    monkeypatch.setenv('AVATAR_API_BASE_URL', 'http://127.0.0.1:8012/')
    require_local_demo()
