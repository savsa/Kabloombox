import json
import requests

from . import auth
from . import const
from . import helper_funcs as help

def get_playlists_audio_features(access_token, refresh_token, playlist_id):
    """Get the playlist's audio features for each track."""
    # get playlist's track ids
    endpoint = 'http://api.spotify.com/v1/playlists/{}/tracks'.format(playlist_id)
    headers = { 'Authorization' : 'Bearer ' + access_token }
    params = {
        'fields' : 'total,items(track(id))',
        'offset' : 0,
    }
    response, access_token = help.request_endpoint(
        method='GET', endpoint=endpoint, headers=headers, params=params,
        access_token=access_token, refresh_token=refresh_token)
    tracks_json = response.json()
    if not response:
        return tracks_json, access_token
    track_ids = [track['track']['id'] for track in tracks_json['items'] if track['track']['id'] is not None]
    track_ids_string = ','.join(track_ids)

    # get audio features of each of the tracks
    endpoint = 'https://api.spotify.com/v1/audio-features'
    headers = { 'Authorization' : 'Bearer ' + access_token }
    params = { 'ids' : track_ids_string }
    response, access_token = help.request_endpoint(
        method='GET', endpoint=endpoint, headers=headers, params=params,
        access_token=access_token, refresh_token=refresh_token)
    features_json = response.json()
    return features_json, access_token

def get_tracks_stats(access_token, refresh_token, track_ids):
    """Get the track's stats, including song title, artist, and length."""
    endpoint = 'https://api.spotify.com/v1/tracks'
    track_ids = track_ids[:50]
    track_ids_string = ','.join(track_ids)

    headers = { 'Authorization' : 'Bearer ' + access_token }
    params = { 'ids' : track_ids_string }
    response, access_token = help.request_endpoint(
        method='GET', endpoint=endpoint, headers=headers, params=params,
        access_token=access_token, refresh_token=refresh_token)
    tracks_stats_json = response.json()
    return tracks_stats_json, access_token

def get_users_playlists(access_token, refresh_token):
    """Get the current user's playlists to display them on the page."""
    endpoint = 'https://api.spotify.com/v1/me/playlists'
    headers = { 'Authorization' : 'Bearer ' + access_token }
    params = { 'offset' : 0 }
    response, access_token = help.request_endpoint(
        method='GET', endpoint=endpoint, headers=headers, params=params,
        access_token=access_token, refresh_token=refresh_token)
    playlists_json = response.json()
    return playlists_json['items'], access_token

def get_account_info(access_token, refresh_token):
    """Get the current user's account id"""
    endpoint = 'https://api.spotify.com/v1/me'
    headers = { 'Authorization' : 'Bearer ' + access_token }
    response, access_token = help.request_endpoint(method='GET',
        endpoint=endpoint, headers=headers, access_token=access_token,
        refresh_token=refresh_token)
    if not response:
        return None
    user_account_json = response.json()
    return user_account_json, access_token

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

def create_playlist(access_token, refresh_token, user_id):
    endpoint = 'https://api.spotify.com/v1/users/{}/playlists'.format(user_id)
    print(playlist_endpoint)
    headers = {
        'Authorization' : 'Bearer ' + access_token, refresh_token,
        'Content-Type' : 'application/json',
    }
    params = {
        'name' : 'Blah',
        'public' : True,
    }
    response, access_token = help.request_endpoint(
        method='POST', endpoint=endpoint, headers=headers, json_params=params,
        access_token=access_token, refresh_token=refresh_token)
    # response = requests.post(playlist_endpoint, headers=headers, json=params)
    return response.json()

def add_tracks_to_playlist(access_token, refresh_token, playlist_id, track_uris):
    endpoint = 'https://api.spotify.com/v1/playlists/{}/tracks'.format(playlist_id)
    headers = {
        'Authorization' : 'Bearer ' + access_token, refresh_token,
        'Content-Type' : 'application/json',
    }
    params = { 'uris': track_uris }
    response, access_token = help.request_endpoint(
        method='POST', endpoint=endpoint, headers=headers, params=params,
        access_token=access_token, refresh_token=refresh_token)
    return response.json()

def filter_stats(tracks):
    # print(tracks)
    filters = ['name', 'id', 'duration_ms', 'uri']
    filtered_list = []
    try:
        for track in tracks['tracks']:
            filtered = { k: track[k] for k in filters}
            filtered['artists'] = track['artists'][0]['name']
            filtered_list.append(filtered)
    except KeyError:
        return tracks
    except IndexError:
        return tracks

    return filtered_list


def logout(session):
    session.clear()