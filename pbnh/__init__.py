"""Initialize the app."""

import logging
import os
from typing import Any

from flask import Flask

# Deprecated (only db.py should know about sqlalchemy):
from sqlalchemy.engine import URL  # type: ignore
import yaml


CONFIG_PATH_DEFAULT = "/etc/pbnh.yaml"
CONFIG_PATH_ENV_VAR = "PBNH_CONFIG"


def _uri_from_legacy(database: dict[str, Any]) -> URL:
    """Build an SQLALCHEMY_DATABASE_URI from legacy config."""
    # e.g.
    #   database:
    #     dbname    : "paste"
    #     dialect   : "postgresql"
    #     driver    : null
    #     host      : "database.example.com"
    #     password  : "WARMACHINEROX"
    #     port      : 5432
    #     username  : "someuser"
    return URL.create(
        drivername="+".join(
            value
            for key in ["dialect", "driver"]
            for value in [database.get(key)]
            if value
        ),
        username=database.get("username"),
        password=database.get("password"),
        host=database.get("host"),
        port=database.get("port"),
        database=database.get("dbname"),
    )


def create_app(
    override_config: dict[str, Any] | None = None, /, *, check_db: bool = False
) -> Flask | None:
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__, instance_relative_config=True)

    # Configure logging.
    gunicorn_logger = logging.getLogger("gunicorn.error")
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)

    # Get the path to the config file.
    try:
        config_path = os.environ[CONFIG_PATH_ENV_VAR]
    except KeyError as exc:
        config_path = CONFIG_PATH_DEFAULT
        app.logger.info(
            f"{exc.args[0]} is not set in the environment. Trying {config_path}..."
        )

    # Load the config file.
    try:
        app.config.from_file(config_path, load=yaml.safe_load)
    except FileNotFoundError as exc:
        # Config can be provided via override_config,
        # so warn instead of failing:
        app.logger.warning(exc)
    except (ValueError, yaml.parser.ParserError):
        app.logger.error(f"{config_path} is malformed.")
        return None
    else:
        app.logger.info(f"{config_path} was loaded successfully.")

    # Apply config overrides.
    app.config.update(override_config or {})
    if app.debug:
        app.logger.setLevel(logging.DEBUG)

    # Adapt legacy config (deprecated).
    if "SQLALCHEMY_DATABASE_URI" not in app.config and "database" in app.config:
        app.logger.warning("Legacy config detected")
        app.config["SQLALCHEMY_DATABASE_URI"] = _uri_from_legacy(app.config["database"])

    # Register blueprints.
    import pbnh.cli
    import pbnh.views

    app.register_blueprint(pbnh.cli.blueprint)
    app.register_blueprint(pbnh.views.blueprint)

    # Ensure the DB is accessible.
    if check_db:
        import pbnh.db

        with app.app_context():
            try:
                with pbnh.db.paster_context() as paster:
                    paster.query(hashid="Has the database been initialized?")
            except Exception as exc:
                app.logger.error(exc)
                return None

    return app
