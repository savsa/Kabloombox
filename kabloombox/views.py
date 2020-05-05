# import auth
from . import auth
from . import const
from . import helper_funcs as help
from . import interactions as actions
from . import scrape

import datetime
import flask
from flask.ext.session import Session


SESSION_TYPE = 'redis'
app.config.from_object(__name__)
Session(app)

@app.route('/', methods=['GET'])
def home_and_login():
    try:
        code = flask.session['code']
    except KeyError:
        code = ''

    access_token = flask.request.cookies.get('access_token')
    refresh_token = flask.request.cookies.get('refresh_token')
    response = requests.get_account_info(access_token, refresh_token)

    if not response: # TODO:
        # user is already logged in and has an access token
        profile_json, access_token = actions.get_account_info(
            access_token, refresh_token)
        if help.is_auth_error(profile_json):
            # flask.session.clear()
            flask.redirect(flask.url_for('/'))
        elif help.is_client_error(profile_json):
            flask.redirect(flask.url_for('/error'))

        playlists_json, access_token = actions.get_users_playlists(
            access_token, refresh_token)
        if help.is_auth_error(playlists_json):
            flask.session.clear()
            flask.redirect(flask.url_for('/'))
        elif help.is_client_error(playlists_json):
            flask.redirect(flask.url_for('/error'))

        profile_photo = actions.get_profile_photo_url(profile_json)
        profile_name = actions.get_profile_name(profile_json)
        return flask.render_template(
            'homeAndLoginPage.html',
            profile_photo=profile_photo,
            profile_name=profile_name,
            playlists_json=playlists_json,
            access_token=access_token)
    elif code:
        # user isn't logged in yet. get the neccessary tokens and store
        # them in the session
        access_token, refresh_token = auth.get_tokens(code)
        if access_token and refresh_token:
            profile_json, access_token = actions.get_account_info(access_token)
            if help.is_auth_error(profile_json):
                flask.session.clear()
                flask.redirect(flask.url_for('/'))
            elif help.is_client_error(profile_json):
                flask.redirect(flask.url_for('/error'))

            playlists_json, access_token = actions.get_users_playlists(access_token)
            if help.is_auth_error(playlists_json):
                flask.session.clear()
                flask.redirect(flask.url_for('/'))
            elif help.is_client_error(playlists_json):
                flask.redirect(flask.url_for('/error'))

            render = flask.render_template('templates/homeAndLoginPage.html',
                profile_photo=profile_photo,
                profile_name=profile_name,
                playlists_json=playlists_json,
                access_token=access_token)
            render.set_cookie(
                key='access_token',
                value=access_token,
                max_age=3600,
                expires=datetime.datetime.now() + datetime.timedelta(hours=1),
                secure=True,
                httponly=True,
                samesite=True)
            render.set_cookie(
                key='refresh_token',
                value=refresh_token,
                max_age=100000,
                expires=datetime.datetime.now() + datetime.timedelta(weeks=52),
                secure=True,
                httponly=True,
                samesite=True)
            return render
        else:
            print('COULDN\'T GET ACCESS TOKEN FROM CODE')
            flask.session.clear()
            flask.redirect(flask.url_for('/error'))

    return flask.render_template('templates/homeAndLoginPage.html')

@app.route('/playlist', methods=['GET'])
def playlist():
    if flask.request.method == 'GET':
        return flask.render_template('templates/playlist.html')

@app.route('/about', methods=['GET'])
def about():
    if flask.request.method == 'GET':
        return flask.render_template('templates/about.html')

@app.route('/error', methods=['GET'])
def error():
    if flask.request.method == 'GET':
        return flask.render_template('templates/error.html')

###################

@app.route('/login', methods=['GET'])
def login():
    if flask.request.method == 'GET':
        url = '{}?client_id={}' \
                '&response_type=code' \
                '&redirect_uri={}' \
                '&scope={}'.format(const.SPOTIFY_AUTH_URL, const.CLIENT_ID_SPOTIFY, const.REDIRECT_URI, const.SCOPE)
        self.redirect(url)

@app.route('/scrape', methods=['GET', 'POST'])
def scrape():
    if flask.request.method == 'GET':
        template = env.get_template('templates/search.html')
        self.response.write(template.render())

    if flask.request.method == 'POST':
        language = flask.request.args.get('language')
        code = flask.session['code']
        if code:
            token = auth.get_token(code)
            print('TOKEN:', token)
            assert token
            if token:
                flask.session['access_token'] = token.access_token
                flask.session['refresh_token'] = token.refresh_token
                scrape.scan_subreddit(language, token.access_token)

@app.route('/redirect', methods=['GET'])
def redirect():
    '''Gets the code after getting redirected from the Spotify login page'''
    if flask.request.method == 'GET':
        code = flask.request.args.get('code')
        if not code:
            print('----COULD NOT GET CODE----')
            flask.redirect(flask.url_for('/error'))
        flask.session['code'] = code
        flask.redirect(flask.url_for('/'))
        # flask.redirect(flask.url_for('/scrape')



@app.errorhandler(404)
def not_found(error):
    return flask.render_template('error.html'), 404


# @app.errorhandler(InternalServerError)
# def handle_500(e):
#     original = getattr(e, "original_exception", None)
#     if original is None:
#         return render_template("500.html"), 500
#     # wrapped unhandled error
#     return render_template("500_unhandled.html", e=original), 500