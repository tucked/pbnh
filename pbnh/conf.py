import yaml
import copy

DEFAULTS = {
    "server": {
        "bind_ip": "0.0.0.0",
        "bind_port": 5001,
        "debug": True,
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


def get_config():
    try:
        with open("secrets.yml") as config:
            return yaml.load(config)
    except IOError:
        return copy.copy(DEFAULTS)
