from flask import Flask

app = Flask(__name__)

# TODO Fix cyclic import:
from pbnh.app import views  # noqa: F401, E402
