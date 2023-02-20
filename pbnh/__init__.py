"""Initialize the app."""


import os
import logging
from typing import Any

from flask import Flask
import yaml


logger = logging.getLogger(__name__)


def get_config():
    for path in [
        # This is basically the dev config file, this is the path
        # that docker-compose is using for secrets:
        os.path.expanduser("~/.config/.pbnh.yml"),
        # This is basically the prod config file, this is the path that a
        # docker container will pull its config from if secrets are
        # configured right:
        "/run/secrets/secrets.yml",
        # As a final fallback, try checking the local dir:
        "secrets.yml",
    ]:
        try:
            with open(path) as f:
                return yaml.safe_load(f)
        except OSError:
            pass
    # should probalt log instead of print. Whatever
    print("no configuration files found")
    return {  # defaults
        "server": {
            "bind_ip": "127.0.0.1",
            "bind_port": 5000,
            "debug": False,
        },
        "database": {
            "dbname": "pastedb",
            "dialect": "sqlite",
            "driver": None,
            "host": None,
            "password": None,
            "port": None,
            "username": None,
        },
    }


def create_app(
    override_config: dict[str, Any] | None = None, /, *, log_level: int = logging.DEBUG
) -> Flask:
    """Create and configure an instance of the Flask application."""
    logging.basicConfig(level=log_level)
    app = Flask(__name__, instance_relative_config=True)

    config_path = "/etc/pbnh.yaml"
    try:
        config_loaded = app.config.from_file(config_path, load=yaml.safe_load)
    except FileNotFoundError:
        logger.info(f"{config_path} not found")
    else:
        if config_loaded:
            logger.info(f"loaded {config_path} successfully")
        else:
            logger.warn(f"{config_path} found but NOT loaded")

    app.config.update({"CONFIG": get_config()})
    app.config.update(override_config or {})

    # Register blueprints.
    import pbnh.views

    app.register_blueprint(pbnh.views.blueprint)

    return app
