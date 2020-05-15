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

# client = tasks_v2.CloudTasksClient()
# parent = client.queue_path(
#             const.AE_PROJECT_NAME, const.AE_SERVER_LOCATION, const.AE_QUEUE)

# with open('kabloombox-creds.json') as source:
#     info = json.load(source)
# storage_credentials = service_account.Credentials.from_service_account_info('kabloombox-creds.json')
# client = tasks_v2.CloudTasksClient(credentials=storage_credentials)
# parent = client.queue_path(
#             const.AE_PROJECT_NAME, const.AE_SERVER_LOCATION, const.AE_QUEUE)

client, parent = '', ''


logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)-8s [%(filename)s:%(lineno)d] %(message)s')

# debug, info, warning, error, critical
