"""Initialize the app."""

import logging
import os
import time
from typing import Any

from flask import Flask
import yaml


CONFIG_PATH_DEFAULT = "/etc/pbnh.yaml"
CONFIG_PATH_ENV_VAR = "PBNH_CONFIG"


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

    # Tell Flask it is behind a reverse proxy.
    if "WERKZEUG_PROXY_FIX" in app.config:
        # https://flask.palletsprojects.com/en/2.2.x/deploying/proxy_fix/
        from werkzeug.middleware.proxy_fix import ProxyFix

        app.wsgi_app = ProxyFix(  # type: ignore
            app.wsgi_app, **app.config["WERKZEUG_PROXY_FIX"]
        )

    # Register blueprints.
    import pbnh.cli
    import pbnh.views

    app.register_blueprint(pbnh.cli.blueprint)
    app.register_blueprint(pbnh.views.blueprint)

    # Ensure the DB is accessible.
    while check_db:
        import pbnh.db

        with app.app_context():
            try:
                with pbnh.db.paster_context() as paster:
                    paster.query(hashid="Has the database been initialized?")
            except Exception as exc:
                app.logger.error(exc)
                secs = 10
                app.logger.info(
                    f"The database is not usable. Trying again in {secs} seconds..."
                )
                time.sleep(secs)
            else:
                check_db = False

    return app
