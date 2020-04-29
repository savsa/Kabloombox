import requests

import interactions as actions
import models
from base_handler import BaseHandler

class StartAnalysis(BaseHandler):
    """POST request to the server to calculate the best possible matches for songs."""
    def post(self):
        playlist = self.request.get('playlist')
        language = self.request.get('language')
        access_token = self.session.get('access_token')

        # if not access_token:
        #     global code_global
        #     token = get_token(code_global)
        #     access_token = token.access_token

        print(playlist)
        print(language)
        print(access_token)
        # to make sure that the user visiting this page is logged in
        if playlist and language in const.subreddits.keys() and access_token:
            # spotify_user_id = get_users_account_id(access_token, self.session)['id']
            template_vars = { 'access_token' : access_token }

            audio_features_json = get_playlists_audio_features(access_token, language, playlist, self.session)

            avg_energy = round(actions.calculate_average(audio_features_json, 'energy'), 3)
            avg_tempo = round(actions.calculate_average(audio_features_json, 'tempo'), 3)
            avg_danceability = round(actions.calculate_average(audio_features_json, 'danceability'), 3)
            avg_energy = round(actions.calculate_average(audio_features_json, 'acousticness'), 3)
            avg_instrumentalness = round(actions.calculate_average(audio_features_json, 'instrumentalness'), 3)
            avg_liveness = round(actions.calculate_average(audio_features_json, 'liveness'), 3)

            # first, run the 'energy' filter
            matches = []
            matches = models.Track.query().filter(models.Track.energy >= (avg_energy - .1))
            # first_matches_len = matches.count()

            # if there are too many matches, run the 'danceability' filter
            # second_matches = []
            # if matches.count() > 20:
            #     second_matches = matches.filter(Track.danceability >= (avg_danceability - .1),
            #                                     Track.danceability <= (avg_danceability + .1))
            # second_matches_len = matches.count()
            # if 20 - first_matches_len < 20 - second_matches_len:
            #     matches = first_matches
            # else:
            #     matches = second_matches

            #
            # matches = matches.filter(Track.instrumentalness >= (avg_instrumentalness - .1),
            #                          Track.instrumentalness <= (avg_instrumentalness + .1))

            match_ids = [match.track_id for match in matches]
            tracks_stats = actions.get_tracks_stats(access_token, match_ids, self.session)
            self.response.write(tracks_stats)
            print(tracks_stats)
        else:
            self.response.status_int = 400
            json_error = json.dumps({'error' : 'Bad request.'})
            self.response.write(json_error)

class Logout(BaseHandler):
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
    def post(self):
        user_id = actions.get_account_info(access_token, self.session)['id']
        playlist_id = actions.create_playlist(user_id)
        actions.add_tracks_to_playlist(playlist_id)