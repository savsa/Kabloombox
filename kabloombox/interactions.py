import json
import requests
import logging

from . import auth
from . import helper_funcs as help


def get_playlists_audio_features(access_token, refresh_token, playlist_id):
    """Get the playlist's audio features for each track.

    Arguments:
        access_token {string} -- a valid Spotify access token.
        refresh_token {string} -- a valid Spotify refresh token.
        playlist_id {string} -- the playlist to get the audio features from.

    Returns:
        (dict, string) -- a tuple with the response json as a dictionary and an
            updated access token.
    """
    endpoint = f"http://api.spotify.com/v1/playlists/{playlist_id}/tracks"
    headers = {"Authorization": "Bearer " + access_token}
    params = {
        "fields": "total,items(track(id))",
        "offset": 0,
    }
    response, access_token = help.request_endpoint(
        method="GET",
        endpoint=endpoint,
        headers=headers,
        params=params,
        access_token=access_token,
        refresh_token=refresh_token,
    )
    tracks_json = response.json()
    if not response:
        return tracks_json, access_token
    track_ids = [
        track["track"]["id"]
        for track in tracks_json["items"]
        if track["track"]["id"] is not None
    ]
    track_ids_string = ",".join(track_ids)

    # get audio features of each of the tracks
    endpoint = "https://api.spotify.com/v1/audio-features"
    headers = {"Authorization": "Bearer " + access_token}
    params = {"ids": track_ids_string}
    response, access_token = help.request_endpoint(
        method="GET",
        endpoint=endpoint,
        headers=headers,
        params=params,
        access_token=access_token,
        refresh_token=refresh_token,
    )
    features_json = response.json()
    return features_json, access_token


def get_tracks_stats(access_token, refresh_token, track_ids):
    """Get multiple tracks' stats, including song title, artist, and length.

    Arguments:
        access_token {string} -- a valid Spotify access token.
        refresh_token {string} -- a valid Spotify refresh token.
        track_ids {list} -- the track ids to be searched.

    Returns:
        (dict, string) -- a tuple with the response json as a dictionary and an
            updated access token.
    """
    endpoint = "https://api.spotify.com/v1/tracks"
    track_ids = track_ids[:50]
    track_ids_string = ",".join(track_ids)

    headers = {"Authorization": "Bearer " + access_token}
    params = {"ids": track_ids_string}
    response, access_token = help.request_endpoint(
        method="GET",
        endpoint=endpoint,
        headers=headers,
        params=params,
        access_token=access_token,
        refresh_token=refresh_token,
    )
    tracks_stats_json = response.json()
    return tracks_stats_json, access_token


def get_users_playlists(access_token, refresh_token):
    """Get the current user's playlists to display them on the page.

    Arguments:
        access_token {string} -- a valid Spotify access token.
        refresh_token {string} -- a valid Spotify refresh token.

    Returns:
        (dict, string) -- a tuple with the response json as a dictionary and an
            updated access token.
    """
    endpoint = "https://api.spotify.com/v1/me/playlists"
    headers = {"Authorization": "Bearer " + access_token}
    params = {"offset": 0}
    response, access_token = help.request_endpoint(
        method="GET",
        endpoint=endpoint,
        headers=headers,
        params=params,
        access_token=access_token,
        refresh_token=refresh_token,
    )
    playlists_json = response.json()
    return playlists_json["items"], access_token


def get_account_info(access_token, refresh_token):
    """Get the current user's account id

    Arguments:
        access_token {string} -- a valid Spotify access token.
        refresh_token {string} -- a valid Spotify refresh token.

    Returns:
        (dict, string) -- a tuple with the response json as a dictionary and an
            updated access token.
    """
    endpoint = "https://api.spotify.com/v1/me"
    headers = {"Authorization": "Bearer " + access_token}
    response, access_token = help.request_endpoint(
        method="GET",
        endpoint=endpoint,
        headers=headers,
        access_token=access_token,
        refresh_token=refresh_token,
    )
    if not response:
        return None, None
    user_account_json = response.json()
    return user_account_json, access_token


def calc_avg(features_json, feature_type):
    """Average the specified audio feature of a playlist.

    Arguments:
        features_json {dict} -- json of a track's features.
        feature_type {string} -- the feature type we want to average.
            Valid feature_type's are: loudness, tempo, danceability, energy,
            acousticness, instrumentalness, liveness, valence, speechiness,
            and mode.

    Returns:
        float -- the average of the specified feature_type of the whole
            playlist.
    """
    if len(features_json) == 0:
        return -1
    total_amount = 0
    for feature in features_json["audio_features"]:
        if not feature:
            return -1
        total_amount += feature[feature_type]
    avg_amount = float(total_amount) / len(features_json["audio_features"])
    return round(avg_amount, 3)


def get_profile_photo_url(profile_info):
    """Return the current user's profile image url if there is one."""
    try:
        return profile_info["images"][0]["url"]
    except (KeyError, IndexError):
        return ""


def get_profile_name(profile_info):
    name = profile_info["display_name"]
    name = (name[:15] + "...") if len(name) > 18 else name
    return name


def create_playlist(access_token, refresh_token, user_id, playlist_name):
    endpoint = "https://api.spotify.com/v1/users/{}/playlists".format(user_id)
    print(endpoint)
    headers = {
        "Authorization": "Bearer " + access_token,
        "Content-Type": "application/json",
    }
    params = {
        "name": playlist_name,
        "public": True,
    }
    response, access_token = help.request_endpoint(
        method="POST",
        endpoint=endpoint,
        headers=headers,
        json_params=params,
        access_token=access_token,
        refresh_token=refresh_token,
    )
    # response = requests.post(playlist_endpoint, headers=headers, json=params)
    return response.json()


def add_tracks_to_playlist(access_token, refresh_token, playlist_id, track_uris):
    endpoint = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
    headers = {
        "Authorization": "Bearer " + access_token,
        "Content-Type": "application/json",
    }

    params = {"uris": track_uris}
    response, access_token = help.request_endpoint(
        method="POST",
        endpoint=endpoint,
        headers=headers,
        params=params,
        access_token=access_token,
        refresh_token=refresh_token,
    )
    return response.json()


def filter_stats(tracks):
    # print(tracks)
    filters = ["name", "id", "duration_ms", "uri", "preview_url"]
    filtered_list = []

    for track in tracks["tracks"]:
        try:
            filtered = {k: track[k] for k in filters}
            filtered["artists"] = track["artists"][0]["name"]
            filtered_list.append(filtered)
        except (KeyError, IndexError):
            filtered = {k: track[k] for k in filters}
            filtered["artists"] = ""
            filtered_list.append(filtered)

    return filtered_list
