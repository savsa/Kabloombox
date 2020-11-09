import requests
import heapq
import math
import json
import flask
import logging
import time

from . import const
from . import helper_funcs as help
from . import interactions as actions
from . import models
from . import app, db


def track_delta(track_features_dict, target_track_dict):
    deltas = [
        math.pow(value - track_features_dict[key], 2)
        for key, value in target_track_dict.items()
    ]
    return math.sqrt(sum(deltas))


def find_closest_matches(language, target_dict):
    # track_model = db.collection('tracks').where(
    #     'language', '==', language).stream()
    # track_model = db.collection('tracks').stream()
    # tracks = [track.to_dict() for track in track_model]

    # DEBUG
    with open("tracks.txt") as f:
        tracks = json.load(f)["tracks"]

    # logging.debug(tracks)

    closest_matches = heapq.nsmallest(
        10, tracks, key=lambda features_dict: track_delta(features_dict, target_dict)
    )
    # for c in closest_matches:
    #     logging.debug(c)
    track_match_ids = [closest_match["track_id"] for closest_match in closest_matches]
    # logging.debug(track_match_ids)
    # logging.debug('CLOSEST MATCHES:', closest_matches)
    return track_match_ids


@app.route("/api/start-analysis", methods=["POST"])
def start_analysis():
    """Calculate the best possible matches to the user's playlist.
    """
    if not flask.request.is_json:
        logging.info("Request is not JSON.")
        return (
            flask.jsonify({"error": {"message": "Data must be JSON.", "status": 400,}}),
            400,
        )
    # if not flask.request.is_secure:
    #     return flask.jsonify({
    #         'error': {
    #             'message': 'Unsecure request.',
    #             'status': 400,
    #         }
    #     }), 400
    # logging.info('ORIGIN: ' + flask.request.origin)
    data = flask.request.get_json()
    playlist = data["playlist"]
    language = data["language"]
    access_token = flask.request.cookies.get("access_token")
    refresh_token = flask.request.cookies.get("refresh_token")

    if not access_token:
        access_token = ""
    if not refresh_token:
        refresh_token = ""

    features_json, access_token = actions.get_playlists_audio_features(
        access_token, refresh_token, playlist
    )
    if help.is_auth_error(features_json):
        logging.info("Auth error.")
        return (
            flask.jsonify(
                {"error": {"message": "Insufficient authentication.", "status": 401,}}
            ),
            401,
        )
    elif help.is_client_error(features_json):
        logging.info("CLIENT ERROR")
        return flask.jsonify({"error": {"message": "Not found.", "status": 404,}}), 404

    if not access_token:
        logging.info("Authentication error.")
        return (
            flask.jsonify(
                {"error": {"message": "Insufficient authentication.", "status": 401,}}
            ),
            401,
        )

    if not playlist or language not in const.subreddits.keys():
        logging.info("Malformed request.")
        return (
            flask.jsonify({"error": {"message": "Bad request.", "status": 404,}}),
            404,
        )

    avg_energy = actions.calc_avg(features_json, "energy")
    avg_tempo = actions.calc_avg(features_json, "tempo")
    avg_danceability = actions.calc_avg(features_json, "danceability")
    avg_acousticness = actions.calc_avg(features_json, "acousticness")
    avg_instrumentalness = actions.calc_avg(features_json, "instrumentalness")
    avg_liveness = actions.calc_avg(features_json, "liveness")
    avg_loudness = actions.calc_avg(features_json, "loudness")
    avg_valence = actions.calc_avg(features_json, "valence")
    avg_mode = actions.calc_avg(features_json, "mode")
    avg_speechiness = actions.calc_avg(features_json, "speechiness")

    target_track_dict = {
        "loudness": avg_loudness,
        "tempo": avg_tempo,
        "danceability": avg_danceability,
        "energy": avg_energy,
        "acousticness": avg_acousticness,
        "instrumentalness": avg_instrumentalness,
        "liveness": avg_liveness,
        "valence": avg_valence,
        "mode": avg_mode,
        "speechiness": avg_speechiness,
    }

    logging.info("=====================")
    logging.info("TARGET: ",)
    logging.info(target_track_dict)

    match_ids = find_closest_matches(language, target_track_dict)
    tracks_stats, access_token = actions.get_tracks_stats(
        access_token, refresh_token, match_ids
    )
    if help.is_auth_error(tracks_stats):
        logging.info("Insufficient auth")
        return (
            flask.jsonify(
                {"error": {"message": "Insufficient authentication.", "status": 401,}}
            ),
            401,
        )
    elif help.is_client_error(tracks_stats):
        logging.info("CLIENT ERROR")
        return flask.jsonify({"error": {"message": "Not found.", "status": 404,}}), 404

    filtered_stats = actions.filter_stats(tracks_stats)
    try:
        image_url = tracks_stats["tracks"][0]["album"]["images"][0]["url"]
    except (KeyError, IndexError):
        logging.error("did not get image")
        image_url = ""
    # logging.debug(tracks_stats["tracks"][]["images"])
    response = {
        "tracks_info": filtered_stats,
        "image_url": image_url,
    }
    return flask.jsonify(response), 200


@app.route("/logout", methods=["GET"])
def logout():
    """Logout and clear the session"""
    response = flask.make_response(flask.redirect("/"))
    response.set_cookie(key="access_token", expires=0)
    response.set_cookie(key="refresh_token", expires=0)
    return response, 302


@app.route("/api/play", methods=["POST"])
def play():
    device_id = flask.request.json["device_id"]
    access_token = flask.request.cookies.get("access_token")
    logging.debug("CCCCCCCC")
    logging.debug(device_id)

    # change playback device
    endpoint = "https://api.spotify.com/v1/me/player"
    headers = {
        "Authorization": "Bearer " + access_token,
        "Content-Type": "application/json",
    }
    req_data = {
        "device_ids": [device_id],
        "play": False,
    }
    logging.debug(req_data)
    # need to send a pause command before switching devices

    # also need to use the "get info about the current playback" endpoint
    # to make sure this actually worked
    response = requests.put(endpoint, headers=headers, json=req_data)
    logging.debug(response.status_code)
    if not response:
        logging.error("no change device, error")

    """Play the song in Spotify."""
    uri = flask.request.json["uri"]
    logging.debug("uri: " + uri)

    endpoint = "http://api.spotify.com/v1/me/player/play"
    headers = {"Authorization": "Bearer " + access_token}
    params = {"device_id": device_id}
    req_data = {"uris": [uri]}
    response = requests.put(endpoint, headers=headers, json=req_data, params=params)

    if not response:
        logging.error("COULD NOT PLAY")
        logging.debug(response.json())
        return (
            flask.jsonify(
                {"error": {"message": "Player does not work idk.", "status": 400,}}
            ),
            400,
        )
    return flask.jsonify({}), 200


@app.route("/api/create", methods=["POST"])
def create():
    """Create a new playlist on the user's Spotify account."""
    uris = flask.request.json["uris"]
    access_token = flask.request.cookies.get("access_token")
    refresh_token = flask.request.cookies.get("refresh_token")
    playlist_name = flask.request.json.get("name")

    if not flask.request.is_json:
        return (
            flask.jsonify({"error": {"message": "Data must be JSON.", "status": 400,}}),
            400,
        )
    if not uris:
        return (
            flask.jsonify({"error": {"message": "Bad request.", "status": 400,}}),
            400,
        )
    if not access_token:
        return (
            flask.jsonify(
                {"error": {"message": "Insufficient authentication.", "status": 401,}}
            ),
            401,
        )
    if not playlist_name:
        playlist_name = "Kabloombox Playlist"

    account_json, access_token = actions.get_account_info(access_token, refresh_token)
    if help.is_auth_error(account_json):
        return (
            flask.jsonify(
                {"error": {"message": "Insufficient authentication.", "status": 401,}}
            ),
            401,
        )
    elif help.is_client_error(account_json):
        return flask.jsonify({"error": {"message": "Not found.", "status": 404,}}), 404
    logging.debug(type(account_json))
    user_id = account_json["id"]
    new_playlist_json = actions.create_playlist(
        access_token, refresh_token, user_id, playlist_name
    )
    if help.is_auth_error(new_playlist_json):
        return (
            flask.jsonify(
                {"error": {"message": "Insufficient authentication.", "status": 401,}}
            ),
            401,
        )
    elif help.is_client_error(new_playlist_json):
        return flask.jsonify({"error": {"message": "Not found.", "status": 404,}}), 404
    new_playlist_id = new_playlist_json["id"]

    add_tracks_json = actions.add_tracks_to_playlist(
        access_token, refresh_token, new_playlist_id, uris
    )
    if help.is_auth_error(add_tracks_json):
        return (
            flask.jsonify(
                {"error": {"message": "Insufficient authentication.", "status": 401,}}
            ),
            401,
        )
    elif help.is_client_error(add_tracks_json):
        logging.error("CLIENT ERROR")
        return flask.jsonify({"error": {"message": "Not found.", "status": 404,}}), 404

    return (
        flask.jsonify({"message": "Successfully created playlist and added tracks."}),
        200,
    )


@app.route("/api/delete", methods=["POST"])
def delete():
    tracks = db.collection("tracks").stream()
    for elem in tracks:
        logging.debug(f"Deleting tracks {elem.id} => {elem.to_dict()}")
        elem.reference.delete()

    track_ids = db.collection("track_ids").stream()
    for elem in track_ids:
        logging.debug(f"Deleting track id {elem.id} => {elem.to_dict()}")
        elem.reference.delete()

    playlist_ids = db.collection("playlist_ids").stream()
    for elem in playlist_ids:
        logging.debug(f"Deleting playlist id {elem.id} => {elem.to_dict()}")
        elem.reference.delete()

    return flask.jsonify({}), 200
