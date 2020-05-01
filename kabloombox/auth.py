import base64
import requests

import const
import models

def get_token(code):
    """Get a valid access and refresh token from a code."""
    payload = {
        'grant_type' : 'authorization_code',
        'code' : code,
        'redirect_uri' : const.REDIRECT_URI,
    }
    headers = { 'Authorization' : 'Basic ' + base64.b64encode(const.CLIENT_ID_SPOTIFY + ':' + const.CLIENT_SECRET_SPOTIFY) }
    response = requests.post(const.SPOTIFY_TOKEN_URL, data=payload, headers=headers)
    token_json = response.json()
    try:
        token = models.Token(token_json['access_token'], token_json['refresh_token'])
        return token
    except KeyError:
        print('NO TOKEN COULD BE GOTTEN')
        return None

def get_access_from_refresh_token(refresh_token):
    payload = {
        'grant_type' : 'refresh_token',
        'refresh_token' : refresh_token
    }
    headers = { 'Authorization' : 'Basic ' + base64.b64encode(const.CLIENT_ID_SPOTIFY + ':' + const.CLIENT_SECRET_SPOTIFY) }
    response = requests.post(const.SPOTIFY_TOKEN_URL, data=payload, headers=headers)
    response_json = response.json()
    try:
        access_token = response_json['access_token']
        return access_token
    except KeyError:
        # logout(session)
        # raise Exception('REFRESH TOKEN BAD')
        return None