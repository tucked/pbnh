import contextlib
import unittest.mock

import pytest


def fake_paster_context_factory(hashid, data):
    @contextlib.contextmanager
    def fake_paster_context():
        mock = unittest.mock.Mock()
        mock.query.return_value = {
            "hashid": hashid,
            "data": data,
        }
        yield mock

    return fake_paster_context


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


def test_cli_paste_info(test_cli_runner, monkeypatch):
    """Pastes can be looked up from the CLI."""
    data = b"Example Data"
    hashid = "3eb000f2018951656c8c27c5dc2a37445d029128"
    monkeypatch.setattr(
        "pbnh.db.paster_context", fake_paster_context_factory(hashid, data)
    )
    result = test_cli_runner.invoke(args=["paste", "info", hashid, hashid])
    assert hashid in result.output
    assert "data" in result.output


def test_cli_paste_info_not_found(app, test_cli_runner):
    """Looking up a nonexistent paste is handled gracefully."""
    hashid = "abc123"
    with app.app_context():
        result = test_cli_runner.invoke(args=["paste", "info", hashid])
    assert hashid in result.output
    assert "not found" in result.output


def test_cli_paste_info_hash_mismatch(test_cli_runner, monkeypatch):
    """A warning is emitted if a paste hashid doesn't match the data."""
    data = b"Example Data"
    hashid = "hash-does-not-match"
    monkeypatch.setattr(
        "pbnh.db.paster_context", fake_paster_context_factory(hashid, data)
    )
    result = test_cli_runner.invoke(args=["paste", "info", hashid])
    assert hashid in result.output
    assert "WARNING" in result.output


def test_cli_paste_remove(app, test_cli_runner):
    """Pastes can be removed from the cLI."""
    hashid = "abc123"
    with app.app_context():
        result = test_cli_runner.invoke(args=["paste", "remove", hashid])
    assert hashid in result.output
