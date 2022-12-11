import pbnh


def test_config_path_env_var(tmp_path, monkeypatch, override_config):
    """Ensure that PBNH_CONFIG can be used to specify a config file."""
    path = tmp_path / "pbnh.yaml"
    key, value = "FOO", "BAR"
    path.write_text(f"{key}: {value}\n")
    monkeypatch.setenv(pbnh.CONFIG_PATH_ENV_VAR, str(path))
    assert pbnh.create_app(override_config).config.get(key) == value
