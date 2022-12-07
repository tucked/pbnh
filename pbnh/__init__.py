import os

import yaml


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
