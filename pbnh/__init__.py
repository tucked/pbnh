"""Initialize the app."""

import logging
from typing import Any

from flask import Flask
import yaml


logger = logging.getLogger(__name__)


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

    # Apply config overrides.
    app.config.update(override_config or {})

    # Register blueprints.
    import pbnh.views

    app.register_blueprint(pbnh.views.blueprint)

    return app
