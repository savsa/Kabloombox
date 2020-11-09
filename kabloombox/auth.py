import base64
import requests
import logging

from . import const


def get_tokens(code):
    """Get a valid access and refresh token from a code."""
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": const.REDIRECT_URI,
    }

    str = f"{const.CLIENT_ID_SPOTIFY}:{const.CLIENT_SECRET_SPOTIFY}"
    byte_str = base64.b64encode(bytes(str, "utf-8"))
    headers = {"Authorization": "Basic " + byte_str.decode()}
    response = requests.post(const.SPOTIFY_TOKEN_URL, data=payload, headers=headers)
    token_json = response.json()
    logging.debug(token_json)
    logging.debug(headers)
    try:
        return token_json["access_token"], token_json["refresh_token"]
    except KeyError:
        print("NO TOKEN COULD BE GOTTEN")
        logging.error(token_json)
        return None, None


def get_access_from_refresh_token(refresh_token):
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    str = f"{const.CLIENT_ID_SPOTIFY}:{const.CLIENT_SECRET_SPOTIFY}"
    byte_str = base64.b64encode(bytes(str, "utf-8"))
    headers = {"Authorization": "Basic " + byte_str.decode()}
    response = requests.post(const.SPOTIFY_TOKEN_URL, data=payload, headers=headers)
    response_json = response.json()
    try:
        access_token = response_json["access_token"]
        return access_token
    except KeyError:
        logging.error("Could not get access from refresh.")
        logging.error(response_json)
        return None
