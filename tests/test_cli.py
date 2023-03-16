import pytest


@pytest.fixture
def test_cli_runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()


def test_cli_db_init(test_cli_runner, monkeypatch):
    init_db_called = False

    def fake_init_db():
        nonlocal init_db_called
        init_db_called = True

    monkeypatch.setattr("pbnh.db.init_db", fake_init_db)
    result = test_cli_runner.invoke(args=["db", "init"])
    assert init_db_called
    assert "initialized" in result.output
