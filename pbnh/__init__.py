"""Initialize the app."""

import logging
import os
from typing import Any

from flask import Flask
import yaml


CONFIG_PATH_DEFAULT = "/etc/pbnh.yaml"
CONFIG_PATH_ENV_VAR = "PBNH_CONFIG"
logger = logging.getLogger(__name__)


def create_app(
    override_config: dict[str, Any] | None = None, /, *, log_level: int = logging.DEBUG
) -> Flask:
    """Create and configure an instance of the Flask application."""
    logging.basicConfig(level=log_level)
    app = Flask(__name__, instance_relative_config=True)

    # Get the path to the config file.
    try:
        config_path = os.environ[CONFIG_PATH_ENV_VAR]
    except KeyError as exc:
        config_path = CONFIG_PATH_DEFAULT
        logger.info(f"{exc} is not set. Trying {config_path}...")

    # Load the config file.
    try:
        app.config.from_file(config_path, load=yaml.safe_load)
    except FileNotFoundError as exc:
        # Config can be provided via override_config,
        # so warn instead of failing:
        logger.warning(exc)
    else:
        logger.info(f"loaded {config_path} successfully")

    # Apply config overrides.
    app.config.update(override_config or {})

    # Register blueprints.
    import pbnh.views

    app.register_blueprint(pbnh.views.blueprint)

    return app
