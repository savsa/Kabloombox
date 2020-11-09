import flask
import sys
import logging

# from google.cloud import tasks_v2
# from google.oauth2 import service_account
# import json

from .db_settings import get_db
from . import config
from . import const


app = flask.Flask(__name__)
app.secret_key = config.SESSIONS_KEY
db = get_db()

# debug, info, warning, error, critical
logging.basicConfig(
    level=logging.DEBUG, format="%(levelname)-8s [%(filename)s:%(lineno)d] %(message)s"
)
