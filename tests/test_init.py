import json
import logging
from urllib.parse import urlsplit

import pytest

import pbnh


def test_create_app_check_db(app):
    """Passing check_db to create_app passes if the DB is initialized."""
    assert pbnh.create_app(app.config, check_db=True)


def test_create_app_check_db_fails(override_config):
    """Passing check_db to create_app fails if the DB is not initialized."""
    assert pbnh.create_app(override_config, check_db=True) is None


def test_config_nondebug(override_config):
    """Setting DEBUG in config enables debug logging."""
    override_config["DEBUG"] = True
    pbnh.create_app(override_config).logger.level == logging.DEBUG
    override_config["DEBUG"] = False
    pbnh.create_app(override_config).logger.level != logging.DEBUG


@pytest.mark.parametrize("drivername", ["sqlite", "postgresql+psycopg2"])
def test_legacy_config(monkeypatch, drivername):
    """Ensure that legacy config is adapted correctly."""
    dialect, _, driver = drivername.partition("+")
    database = {
        "dbname": "paste",
        "dialect": dialect,
        "driver": driver,
        "host": "database.example.com",
        "password": "WARMACHINEROX",
        "port": 5432,
        "username": "someuser",
    }
    monkeypatch.setenv(pbnh.CONFIG_PATH_ENV_VAR, "")
    url = pbnh.create_app({"database": database}).config.get("SQLALCHEMY_DATABASE_URI")
    assert url.database == database["dbname"]
    assert url.drivername == drivername
    assert url.host == database["host"]
    assert url.password == database["password"]
    assert url.port == database["port"]
    assert url.username == database["username"]


def test_config_path_env_var(tmp_path, monkeypatch, override_config):
    """Ensure that PBNH_CONFIG can be used to specify a config file."""
    path = tmp_path / "pbnh.yaml"
    key, value = "FOO", "BAR"
    path.write_text(f"{key}: {value}\n")
    monkeypatch.setenv(pbnh.CONFIG_PATH_ENV_VAR, str(path))
    assert pbnh.create_app(override_config).config.get(key) == value


def test_config_missing(monkeypatch, override_config, caplog):
    """Ensure that a missing config file causes a warning to be logged."""
    path = "/does/not/exist"
    monkeypatch.setenv(pbnh.CONFIG_PATH_ENV_VAR, str(path))
    pbnh.create_app(override_config)
    assert any(
        path in record.message and record.levelname == "WARNING"
        for record in caplog.records
    )


def test_config_missing_default(monkeypatch, override_config, caplog):
    """Ensure that a missing default config file causes a warning to be logged."""
    path = "/does/not/exist"
    monkeypatch.setattr(pbnh, "CONFIG_PATH_DEFAULT", path)
    pbnh.create_app(override_config)
    assert any(
        path in record.message and record.levelname == "WARNING"
        for record in caplog.records
    )


@pytest.mark.parametrize(
    "text",
    [
        "not yaml",  # ValueError
        ":",  # yaml.parser.ParserError
    ],
)
def test_config_malformed(tmp_path, text, monkeypatch, override_config, caplog):
    """Ensure that a malformed config file prevents app creation."""
    path = tmp_path / "pbnh.yaml"
    path.write_text(text)
    monkeypatch.setenv(pbnh.CONFIG_PATH_ENV_VAR, str(path))
    assert pbnh.create_app(override_config) is None
    assert any(
        str(path) in record.message
        and "malformed" in record.message
        and record.levelname == "ERROR"
        for record in caplog.records
    )


def test_proxy_fix(app):
    """Setting x_proto in WERKZEUG_PROXY_FIX affects the returned link."""

    def _proto_forwarded_link_scheme(app):
        response = app.test_client().post(
            "/", data={"content": "abc"}, headers={"X-Forwarded-Proto": "https"}
        )
        return urlsplit(json.loads(response.data.decode("utf-8"))["link"]).scheme

    for x_proto, scheme in {0: "http", 1: "https"}.items():
        app.config["WERKZEUG_PROXY_FIX"] = {"x_proto": x_proto}
        assert (
            _proto_forwarded_link_scheme(pbnh.create_app(app.config)) == scheme
        ), x_proto
