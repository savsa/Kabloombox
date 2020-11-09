# import auth
from . import auth
from . import const
from . import helper_funcs as help
from . import interactions as actions
from . import scrape
from . import app

import datetime
import flask

import sys

import logging

# from flask.ext.session import Session


# SESSION_TYPE = 'redis'
# app.config.from_object(__name__)
# Session(app)


@app.route("/", methods=["GET"])
def home_and_login():
    code = ""
    if "code" in flask.session:
        code = flask.session["code"]
        flask.session.pop("code")

    access_token = flask.request.cookies.get("access_token")
    refresh_token = flask.request.cookies.get("refresh_token")

    account_json = None
    if access_token:
        account_json, access_token = actions.get_account_info(
            access_token, refresh_token
        )
    if account_json:  # TODO:
        logging.debug("access token: " + access_token)
        logging.debug("refresh: " + refresh_token)

        # user is already logged in and has an access token
        profile_json, access_token = actions.get_account_info(
            access_token, refresh_token
        )
        if help.is_auth_error(profile_json):
            flask.redirect(flask.url_for("/"))
        elif help.is_client_error(profile_json):
            return flask.redirect(flask.url_for("error"))

        playlists_json, access_token = actions.get_users_playlists(
            access_token, refresh_token
        )
        if help.is_auth_error(playlists_json):
            flask.session.clear()
            return flask.redirect(flask.url_for("/"))
        elif help.is_client_error(playlists_json):
            return flask.redirect(flask.url_for("error"))

        profile_photo = actions.get_profile_photo_url(profile_json)
        profile_name = actions.get_profile_name(profile_json)
        return flask.render_template(
            "homeAndLoginPage.html",
            profile_photo=profile_photo,
            profile_name=profile_name,
            playlists_json=playlists_json,
            access_token=access_token,
        )
    elif code:
        # user isn't logged in yet. get the neccessary tokens and store
        # them in the session
        access_token, refresh_token = auth.get_tokens(code)
        if not access_token or not refresh_token:
            logging.critical("COULD NOT GET TOKENS FROM CODE IN HOME")
            return flask.redirect(flask.url_for("error"))
        logging.debug("access token: " + access_token)
        logging.debug("refresh: " + refresh_token)
        profile_json, access_token = actions.get_account_info(
            access_token, refresh_token
        )
        if help.is_auth_error(profile_json):
            return flask.redirect(flask.url_for("home_and_login"))
        elif help.is_client_error(profile_json):
            return flask.redirect(flask.url_for("error"))

        playlists_json, access_token = actions.get_users_playlists(
            access_token, refresh_token
        )
        if help.is_auth_error(playlists_json):
            flask.session.clear()
            return flask.redirect(flask.url_for("home_and_login"))
        elif help.is_client_error(playlists_json):
            return flask.redirect(flask.url_for("error"))

        logging.info("CREATING COOKIES.")
        response = flask.make_response(
            flask.render_template(
                "homeAndLoginPage.html",
                playlists_json=playlists_json,
                access_token=access_token,
            )
        )
        response.set_cookie(
            key="access_token",
            value=access_token,
            expires=datetime.datetime.now() + datetime.timedelta(hours=10),
            # secure=True,
            # httponly=True,
            # samesite='Strict',
        )
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            expires=datetime.datetime.now() + datetime.timedelta(weeks=52),
            # secure=True,
            # httponly=True,
            # samesite='Strict',
        )
        return response

    return flask.render_template("homeAndLoginPage.html")


@app.route("/playlist", methods=["GET"])
def playlist():
    access_token = flask.request.cookies.get("access_token")
    return flask.render_template("playlist.html", access_token=access_token)


@app.route("/about", methods=["GET"])
def about():
    return flask.render_template("about.html")


@app.route("/error", methods=["GET"])
def error():
    return flask.render_template("error.html")


###################


@app.route("/login", methods=["GET"])
def login():
    url = (
        f"{const.SPOTIFY_AUTH_URL}?client_id={const.CLIENT_ID_SPOTIFY}"
        f"&response_type=code"
        f"&redirect_uri={const.REDIRECT_URI}"
        f"&scope={const.SCOPE}"
    )
    return flask.redirect(url)


@app.route("/scrape", methods=["GET", "POST"])
def scrape_reddit():
    if flask.request.method == "GET":
        access_token = flask.request.cookies.get("access_token")
        if "code" not in flask.session and not access_token:
            return (
                flask.jsonify(
                    {"error": {"message": "Couldn\t get code.", "status": 401,}}
                ),
                401,
            )

        if "code" in flask.session:
            code = flask.session["code"]
            flask.session.pop("code")
            access_token, _ = auth.get_tokens(code)

        response = flask.make_response(flask.render_template("search.html"))
        response.set_cookie(
            key="access_token",
            value=access_token,
            expires=datetime.datetime.now() + datetime.timedelta(hours=10),
            # secure=True,
            # httponly=True,
            # samesite='Strict',
        )
        return response

    if flask.request.method == "POST":
        scrape.scan_subreddit_debug()
        access_token = flask.request.cookies.get("access_token")
        refresh_token = flask.request.cookies.get("refresh_token")
        language = flask.request.form.get("language")
        if not access_token:
            logging.critical("NO ACCESS TOKEN")
            return (
                flask.jsonify(
                    {"error": {"message": "Didn't get tokens.", "status": 401,}}
                ),
                401,
            )

        _, access_token = actions.get_account_info(access_token, refresh_token)

        # scrape.scan_subreddit(language, access_token)
        return flask.jsonify({}), 200


@app.route("/redirect", methods=["GET"])
def redirect():
    """Gets the code from the Spotify login page and then redirects."""
    code = flask.request.args.get("code")
    if not code:
        logging.critical("----COULD NOT GET CODE----")
        return flask.redirect(flask.url_for("error"))
    flask.session["code"] = code
    return flask.redirect(flask.url_for("home_and_login"))
    # return flask.redirect(flask.url_for('scrape_reddit'))


@app.errorhandler(404)
def not_found(error):
    return flask.render_template("error.html"), 404


# @app.errorhandler(InternalServerError)
# def handle_500(e):
#     original = getattr(e, "original_exception", None)
#     if original is None:
#         return render_template("500.html"), 500
#     # wrapped unhandled error
#     return render_template("500_unhandled.html", e=original), 500
