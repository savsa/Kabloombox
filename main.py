import os
import flask
import sys

# import kabloombox.views
from kabloombox import views

#
# # file_dir = os.path.dirname(__file__)
# sys.path.append(os.path.dirname(__file__))

app = flask.Flask(__name__)

if __name__ == '__main__':
    if os.getenv('GAE_ENV', '').startswith('standard'):
        app.run()  # production
    else:
        app.run(port=8080, host='localhost', debug=True)  # localhost