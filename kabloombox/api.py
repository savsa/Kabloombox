import requests
import heapq
import math
import json

import const
import helper_funcs as help
import interactions as actions
import models
from base_handler import BaseHandler

def track_delta(track_features_dict, target_track_dict):
    # deltas = [abs(value - track_features_dict[key]) for key, value in target_track_dict.items()]
    deltas = [math.pow(value - track_features_dict[key], 2) for key, value in target_track_dict.items()]
    return math.sqrt(sum(deltas))

def find_closest_matches(language, target_track_dict):
    tracks_model = models.Track.query().filter(models.Track.language == language)
    tracks = [track.to_dict() for track in tracks_model]
    # print(tracks)

    closest_matches = heapq.nsmallest(10, tracks, key=lambda track_features_dict: track_delta(track_features_dict, target_track_dict))
    track_match_ids = [closest_match['track_id'] for closest_match in closest_matches]
    # print(track_match_ids)
    print('CLOSEST MATCHES:', closest_matches)
    return track_match_ids

class StartAnalysis(BaseHandler):
    """POST request to the server to calculate the best possible matches for songs."""
    def post(self):
        access_token = self.session.get('access_token')
        data = json.loads(self.request.body)
        playlist = data['playlist']
        language = data['language']

        self.response.headers['Content-Type'] = 'application/json'

        if self.request.headers.get('Content_type') != 'application/json':
            self.response.status_int = 400
            json_error = json.dumps({'error': 'Data must be JSON.'})
            self.response.write(json_error)

        # to make sure that the user visiting this page is logged in
        if playlist and language in const.subreddits.keys() and access_token:
            audio_features_json = actions.get_playlists_audio_features(access_token, playlist, self.session)
            if help.is_auth_error(audio_features_json):
                self.response.status_int = 401
                json_error = json.dumps({'error': 'Insufficient authentication.'})
                self.response.write(json_error)
                return
            elif help.is_client_error(audio_features_json):
                self.response.status_int = 404
                json_error = json.dumps({'error': 'Not found.'})
                self.response.write(json_error)
                return

            avg_energy = actions.calculate_average(audio_features_json, 'energy')
            avg_tempo = actions.calculate_average(audio_features_json, 'tempo')
            avg_danceability = actions.calculate_average(audio_features_json, 'danceability')
            avg_acousticness = actions.calculate_average(audio_features_json, 'acousticness')
            avg_instrumentalness = actions.calculate_average(audio_features_json, 'instrumentalness')
            avg_liveness = actions.calculate_average(audio_features_json, 'liveness')
            avg_loudness = actions.calculate_average(audio_features_json, 'loudness')
            avg_valence = actions.calculate_average(audio_features_json, 'valence')
            avg_mode = actions.calculate_average(audio_features_json, 'mode')
            avg_speechiness = actions.calculate_average(audio_features_json, 'speechiness')
            # no mode
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
                # 'speechiness': avg_speechiness
            }

            print('================')
            print('TARGET: ', target_track_dict)
            print()

            match_ids = find_closest_matches(language, target_track_dict)
            tracks_stats = actions.get_tracks_stats(access_token, match_ids, self.session)
            self.response.headers['Content-Type'] = 'application/json'
            self.response.write(json.dumps(tracks_stats))
        else:
            self.response.status_int = 400
            json_error = json.dumps({'error': 'Bad request.'})
            self.response.write(json_error)

class Logout(BaseHandler):
    """Logout and clear the session"""
    def get(self):
        if self.session:
            actions.logout(self.session)
        self.redirect('/')

class Play(BaseHandler):
    def post(self):
        uri = self.request.get('uri')
        access_token = self.session.get('access_token')

        play_endpoint = 'http://api.spotify.com/v1/me/player/play'
        headers = { 'Authorization' : 'Bearer ' + access_token }
        data = { "uris": [uri] }
        print(data)
        response = requests.put(play_endpoint, headers=headers, data=data)
        if response.status_code != 204:
            print(response.text)

class Create(BaseHandler):
    """Create a new playlist."""
    def post(self):
        user_id = actions.get_account_info(access_token, self.session)['id']
        playlist_id = actions.create_playlist(user_id)
        actions.add_tracks_to_playlist(playlist_id)