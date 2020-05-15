import requests
import heapq
import math
import json
import flask
import logging

from . import const
from . import helper_funcs as help
from . import interactions as actions
from . import models
from . import app, db


def track_delta(track_features_dict, target_track_dict):
    deltas = [math.pow(value - track_features_dict[key], 2)
              for key, value in target_track_dict.items()]
    return math.sqrt(sum(deltas))


def find_closest_matches(language, target_dict):
    track_model = db.collection('tracks').where(
        'language', '==', language).stream()
    # track_model = db.collection('tracks').stream()
    tracks = [track.to_dict() for track in track_model]
    logging.debug(tracks)

    closest_matches = heapq.nsmallest(
        10,
        tracks,
        key=lambda features_dict: track_delta(features_dict, target_dict))
    # for c in closest_matches:
    #     logging.debug(c)
    track_match_ids = [closest_match['track_id']
                       for closest_match in closest_matches]
    # logging.debug(track_match_ids)
    # logging.debug('CLOSEST MATCHES:', closest_matches)
    return track_match_ids


@app.route('/start-analysis', methods=['POST'])
def start_analysis():
    """Calculate the best possible matches to the user's playlist.
    """
    if not flask.request.is_json:
        return flask.jsonify({
            'error': {
                'message': 'Data must be JSON.',
                'status': 400,
            }
        }), 400
    # if not flask.request.is_secure:
    #     return flask.jsonify({
    #         'error': {
    #             'message': 'Unsecure request.',
    #             'status': 400,
    #         }
    #     }), 400
    # logging.info('ORIGIN: ' + flask.request.origin)
    data = flask.request.get_json()
    playlist = data['playlist']
    language = data['language']
    access_token = flask.request.cookies.get('access_token')
    refresh_token = flask.request.cookies.get('refresh_token')

    if not access_token or not refresh_token:
        return flask.jsonify({
            'error': {
                'message': 'Insufficient authentication.',
                'status': 401,
            }
        }), 401

    if not playlist or language not in const.subreddits.keys():
        return flask.jsonify({
            'error': {
                'message': 'Bad request.',
                'status': 400,
            }
        }), 400

    features_json, access_token = actions.get_playlists_audio_features(
        access_token, refresh_token, playlist)
    if help.is_auth_error(features_json):
        return flask.jsonify({
            'error': {
                'message': 'Insufficient authentication.',
                'status': 401,
            }
        }), 401
    elif help.is_client_error(features_json):
        logging.error('CLIENT ERROR')
        return flask.jsonify({
            'error': {
                'message': 'Not found.',
                'status': 404,
            }
        }), 404

    avg_energy = actions.calc_avg(features_json, 'energy')
    avg_tempo = actions.calc_avg(features_json, 'tempo')
    avg_danceability = actions.calc_avg(features_json, 'danceability')
    avg_acousticness = actions.calc_avg(features_json, 'acousticness')
    avg_instrumentalness = actions.calc_avg(features_json, 'instrumentalness')
    avg_liveness = actions.calc_avg(features_json, 'liveness')
    avg_loudness = actions.calc_avg(features_json, 'loudness')
    avg_valence = actions.calc_avg(features_json, 'valence')
    avg_mode = actions.calc_avg(features_json, 'mode')
    avg_speechiness = actions.calc_avg(features_json, 'speechiness')

    target_track_dict = {
        'loudness': avg_loudness,
        'tempo': avg_tempo,
        'danceability': avg_danceability,
        'energy': avg_energy,
        'acousticness': avg_acousticness,
        'instrumentalness': avg_instrumentalness,
        'liveness': avg_liveness,
        'valence': avg_valence,
        'mode': avg_mode,
        'speechiness': avg_speechiness
    }

    logging.info('=====================')
    logging.info('TARGET: ', )
    logging.info(target_track_dict)

    match_ids = find_closest_matches(language, target_track_dict)
    logging.debug(match_ids)
    tracks_stats, access_token = actions.get_tracks_stats(
        access_token, refresh_token, match_ids)
    if help.is_auth_error(tracks_stats):
        return flask.jsonify({
            'error': {
                'message': 'Insufficient authentication.',
                'status': 401,
            }
        }), 401
    elif help.is_client_error(tracks_stats):
        logging.error('CLIENT ERROR')
        return flask.jsonify({
            'error': {
                'message': 'Not found.',
                'status': 404,
            }
        }), 404

    filtered_stats = actions.filter_stats(tracks_stats)
    return flask.jsonify(filtered_stats), 200


@app.route('/logout', methods=['GET'])
def logout():
    """Logout and clear the session"""
    response = flask.make_response(flask.redirect('/'))
    response.set_cookie(key='access_token', expires=0)
    response.set_cookie(key='refresh_token', expires=0)
    return response, 302


@app.route('/play', methods=['POST'])
def play():
    """Play the song in Spotify."""
    data = flask.request.json
    uri = data['uri']
    access_token = flask.session.get('access_token')

    play_endpoint = 'http://api.spotify.com/v1/me/player/play'
    headers = {'Authorization': 'Bearer ' + access_token}
    data = {"uris": [uri]}
    print(data)
    play_response = requests.put(play_endpoint, headers=headers, data=data)
    if response.status_code != 204:
        print(response.text)


@app.route('/create', methods=['POST'])
def create():
    """Create a new playlist on the user's Spotify account."""
    data = flask.request.get_json()
    uris = data['uris']
    access_token = flask.request.cookies.get('access_token')
    refresh_token = flask.request.cookies.get('refresh_token')

    if not flask.request.is_json:
        return flask.jsonify({
            'error': {
                'message': 'Data must be JSON.',
                'status': 400,
            }
        }), 400
    if not uris:
        return flask.jsonify({
            'error': {
                'message': 'Bad request.',
                'status': 400,
            }
        }), 400
    if not access_token:
        return flask.jsonify({
            'error': {
                'message': 'Insufficient authentication.',
                'status': 401,
            }
        }), 401

    user_id, access_token = actions.get_account_info(
        access_token, refresh_token)['id']
    new_playlist_json = actions.create_playlist(
        access_token, refresh_token, user_id)
    if help.is_auth_error(new_playlist_json):
        return flask.jsonify({
            'error': {
                'message': 'Insufficient authentication.',
                'status': 401,
            }
        }), 401
    elif help.is_client_error(new_playlist_json):
        return flask.jsonify({
            'error': {
                'message': 'Not found.',
                'status': 404,
            }
        }), 404
    new_playlist_id = new_playlist_json['id']

    add_tracks_json = actions.add_tracks_to_playlist(
        access_token, refresh, new_playlist_id, uris)
    if help.is_auth_error(tracks_stats):
        return flask.jsonify({
            'error': {
                'message': 'Insufficient authentication.',
                'status': 401,
            }
        }), 401
    elif help.is_client_error(tracks_stats):
        logging.error('CLIENT ERROR')
        return flask.jsonify({
            'error': {
                'message': 'Not found.',
                'status': 404,
            }
        }), 404

    return flask.jsonify({
        'message': 'Successfully created playlist and added tracks.'
    }), 200


@app.route('/delete', methods=['POST'])
def delete():
    tracks = db.collection('tracks').stream()
    for elem in tracks:
        logging.debug(
            f'Deleting tracks {elem.id} => {elem.to_dict()}')
        elem.reference.delete()

    track_ids = db.collection('track_ids').stream()
    for elem in track_ids:
        logging.debug(
            f'Deleting track id {elem.id} => {elem.to_dict()}')
        elem.reference.delete()

    playlist_ids = db.collection('playlist_ids').stream()
    for elem in playlist_ids:
        logging.debug(
            f'Deleting playlist id {elem.id} => {elem.to_dict()}')
        elem.reference.delete()

    return flask.jsonify({}), 200
