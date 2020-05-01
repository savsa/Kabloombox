import json

import auth
import const
import helper_funcs as help

def get_playlists_audio_features(access_token, playlist_id, session):
    """Get the playlist's audio features for each track."""
    # get playlist's track ids
    playlists_tracks_endpoint = 'http://api.spotify.com/v1/playlists/{}/tracks'.format(playlist_id)
    headers = { 'Authorization' : 'Bearer ' + access_token }
    params = {
        'fields' : 'total,items(track(id))',
        'offset' : 0,
    }
    tracks_response = help.request_endpoint(playlists_tracks_endpoint, session, headers, params)
    tracks_json = tracks_response.json()
    if not tracks_response:
        return tracks_json
    track_ids = [track['track']['id'] for track in tracks_json['items'] if track['track']['id'] is not None]
    track_ids_string = ','.join(track_ids)

    # get audio features of each of the tracks
    tracks_features_endpoint = 'https://api.spotify.com/v1/audio-features'
    headers = { 'Authorization' : 'Bearer ' + access_token }
    params = { 'ids' : track_ids_string }
    features_response = help.request_endpoint(tracks_features_endpoint, session, headers, params)
    features_json = features_response.json()
    return features_json

def get_tracks_stats(access_token, track_ids, session):
    """Get the track's stats, including song title, artist, and length."""
    tracks_stats_endpoint = 'https://api.spotify.com/v1/tracks'
    track_ids = track_ids[:50]
    track_ids_string = ','.join(track_ids)

    headers = { 'Authorization' : 'Bearer ' + access_token }
    params = { 'ids' : track_ids_string }
    tracks_stats_response = help.request_endpoint(tracks_stats_endpoint, session, headers, params)
    tracks_stats_json = tracks_stats_response.json()
    return tracks_stats_json

def get_users_playlists(access_token, session):
    """Get the current user's playlists to display them on the page."""
    playlists_endpoint = 'https://api.spotify.com/v1/me/playlists'
    headers = { 'Authorization' : 'Bearer ' + access_token }
    params = { 'offset' : 0 }
    playlists_response = help.request_endpoint(playlists_endpoint, session, headers, params)
    playlists_json = playlists_response.json()
    return playlists_json['items']

def get_account_info(access_token, session):
    """Get the current user's account id"""
    user_account_endpoint = 'https://api.spotify.com/v1/me'
    headers = { 'Authorization' : 'Bearer ' + access_token }
    user_account_response = help.request_endpoint(user_account_endpoint, session, headers)
    if not user_account_response:
        return None
    user_account_json = user_account_response.json()
    return user_account_json

def calculate_average(features_json, feature_type):
    """Average the specified audio feature of a playlist.

    Valid feature_type's are: loudness, tempo, danceability, energy,
    acousticness, instrumentalness, liveness, valence, speechiness, and mode.
    """
    if len(features_json) == 0: return -1
    total_amount = 0
    for feature in features_json['audio_features']:
        total_amount += feature[feature_type]
    avg_amount = float(total_amount) / len(features_json['audio_features'])
    return round(avg_amount, 3)

def get_profile_photo_url(profile_info):
    """Return the current user's profile image url if there is one."""
    try:
        return profile_info['images'][0]['url']
    except:
        return ''

def get_profile_name(profile_info):
    name = profile_info['display_name']
    name = (name[:15] + '...') if len(name) > 18 else name
    return name

def create_playlist(user_id):
    playlist_endpoint = 'https://api.spotify.com/v1/users/{}/playlists'.format(user_id)
    headers = {
        'Authorization' : 'Basic ' + base64.b64encode(const.CLIENT_ID_SPOTIFY + ':' + const.CLIENT_SECRET_SPOTIFY),
        'Content-Type' : 'application/json',
    }
    params = {
        'name' : 'Blah',
        'public' : True,
        'description' : 'description',
    }
    response = requests.post(headers=headers, data=params)
    # if response.status_code == 200 or response.status_code == 201:
    if response.status_code == requests.codes.ok:
        response_json = response.json()
        return response_json['id']

def add_tracks_to_playlist(playlist_id):
    playlist_endpoint = 'https://api.spotify.com/v1/playlists/{}/tracks'.format(playlist_id)
    headers = {
        'Authorization' : 'Basic ' + base64.b64encode(const.CLIENT_ID_SPOTIFY + ':' + const.CLIENT_SECRET_SPOTIFY),
        'Content-Type' : 'application/json',
    }
    params = {

    }

def logout(session):
    session.clear()