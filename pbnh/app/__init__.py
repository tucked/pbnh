from flask import Flask

app = Flask(__name__)
# app.config['CONFIG'] = None
from pbnh.app import views
