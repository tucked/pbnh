import logging

import pytest

import pbnh


def test_config_nondebug(override_config):
    """Setting DEBUG in config enables debug logging."""
    override_config["DEBUG"] = True
    pbnh.create_app(override_config).logger.level == logging.DEBUG
    override_config["DEBUG"] = False
    pbnh.create_app(override_config).logger.level != logging.DEBUG


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
    """Ensure that a malformed config file causes an exception to be raised."""
    path = tmp_path / "pbnh.yaml"
    path.write_text(text)
    monkeypatch.setenv(pbnh.CONFIG_PATH_ENV_VAR, str(path))
    with pytest.raises(Exception):
        pbnh.create_app(override_config)
    assert any(
        str(path) in record.message
        and "malformed" in record.message
        and record.levelname == "ERROR"
        for record in caplog.records
    )
