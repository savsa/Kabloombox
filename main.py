import webapp2
import jinja2
import requests
import json
import base64
import os
import time
import logging

import praw
import config

from google.appengine.ext import deferred
from google.appengine.ext import ndb

import requests_toolbelt.adapters.appengine
requests_toolbelt.adapters.appengine.monkeypatch()

# TODO:
# - work with spotify link in main post and on wiki, not just in comments

# Client Keys
CLIENT_ID_SPOTIFY = config.CLIENT_ID_SPOTIFY
CLIENT_SECRET_SPOTIFY = config.CLIENT_SECRET_SPOTIFY

CLIENT_ID_REDDIT = config.CLIENT_ID_REDDIT
CLIENT_SECRET_REDDIT = config.CLIENT_SECRET_REDDIT
USER_AGENT_REDDIT = config.USER_AGENT_REDDIT

# Spotify URLs
SPOTIFY_AUTH_URL = 'https://accounts.spotify.com/authorize'
SPOTIFY_TOKEN_URL = 'https://accounts.spotify.com/api/token'
SPOTIFY_API_BASE_URL = 'https://api.spotify.com'
SPOTIFY_URL = 'open.spotify.com/user/'

# redirect_uri = 'http://localhost:8080/search'
redirect_uri = 'http://localhost:8080/redirect'
# redirect_uri = 'https://kabloombox-219016.appspot.com/search'
scope = 'user-library-read user-read-private user-read-email playlist-read-private'

access_token_global = ''
refresh_token_global = ''
code_global = ''

env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

# Models

class Track(ndb.Model):
    track_id = ndb.StringProperty()
    language = ndb.StringProperty()
    loudness = ndb.FloatProperty()
    tempo = ndb.FloatProperty()
    danceability = ndb.FloatProperty()
    energy = ndb.FloatProperty()
    acousticness = ndb.FloatProperty()
    instrumentalness = ndb.FloatProperty()
    liveness = ndb.FloatProperty()
    valence = ndb.FloatProperty()
    mode = ndb.IntegerProperty()

class TrackID(ndb.Model):
    value = ndb.StringProperty()
    language = ndb.StringProperty()

class PlaylistID(ndb.Model):
    value = ndb.StringProperty()
    language = ndb.StringProperty()

class AuthToken(ndb.Model):
    access_token = ndb.StringProperty()
    refresh_token = ndb.StringProperty()
    spotify_user_id = ndb.StringProperty()


# Functions

def get_playlists_track_ids(language, access_token):
    """Using the playlist ids, get all of their tracks and track ids."""
    track_ids = []
    playlist_ids = PlaylistID.query().filter(PlaylistID.language == language)
    for playlist_id in playlist_ids:
        id = playlist_id.value
        playlists_tracks_link = 'http://api.spotify.com/v1/playlists/{}/tracks'.format(id)
        headers = { 'Authorization' : 'Bearer ' + access_token }
        params = {
            'fields': 'total,items(track(id))',
            'offset': 0,
        }
        tracks_response = requests.get(playlists_tracks_link, headers=headers, params=params)
        tracks_json = tracks_response.json()

        # Spotify limits to only 100 songs per request, so set starting location
        # in playlist to +100 every loop to eventually get all songs
        if len(tracks_json) > 1: # if valid playlist URL
            for i in range((tracks_json['total'] / 100) + 1):
                try:
                    tracks_response = requests.get(playlists_tracks_link, headers=headers, params=params)
                    tracks_json = tracks_response.json()
                    for element in tracks_json['items']:
                        track_ids_datastore = TrackID.query().filter(TrackID.value == element['track']['id']).get()
                        if (element['track']['id'] and element['track']['id'] not in track_ids
                            and not track_ids_datastore): # make sure no repeats
                            trackid = TrackID(value=element['track']['id'], language=language)
                            track_ids.append(trackid)
                            if len(track_ids) >= 100:
                                ndb.put_multi(track_ids)
                                track_ids = []
                    params['offset'] += 100
                except KeyError: # if no track id is found
                    continue

            if len(track_ids) > 0:
                ndb.put_multi(track_ids)


def create_tracks_from_audio_analysis(language, access_token):
    """Retrieves the track_ids from Datastore, uses thoses to get the audio
    analyses of the tracks, then stores that in Datastore.
    """
    tracks = []
    track_ids = TrackID.query().filter(TrackID.language == language)

    for track_id in track_ids:
        id = track_id.value
        spotify_audio_features_link = 'http://api.spotify.com/v1/audio-features/{}'.format(id)
        headers = { 'Authorization' : 'Bearer ' + access_token }
        features_response = requests.get(spotify_audio_features_link, headers=headers)
        features = features_response.json()
        if features:
            track = Track(
                track_id=id,
                language=language,
                loudness=features['loudness'],
                tempo=features['tempo'],
                danceability=features['danceability'],
                energy=features['energy'],
                acousticness=features['acousticness'],
                instrumentalness=features['instrumentalness'],
                liveness=features['liveness'],
                valence=features['valence'],
                mode=features['mode'])
            tracks.append(track)
            # add tracks in bulk as to not get Error 429: too many requests
            if len(tracks) >= 100:
                ndb.put_multi(tracks)
                tracks = []
        time.sleep(1.4)

    # put any remaining tracks
    if len(tracks) > 0:
        ndb.put_multi(tracks)


def find_url_in_comments(playlist_ids_local, playlist_ids_datastore, subreddit, language):
    """Finds links to Spotify playlists in the comment section of posts."""
    playlist_id_objects = []
    for submission in subreddit.search('spotify'):
        submission.comments.replace_more(limit=None)
        comments = submission.comments.list()
        for comment in comments:
            new_start = 0
            while True: # loop until all spotify links are found in comment
                if SPOTIFY_URL in comment.body[new_start:]:
                    comment_body_find_playlist = comment.body.find('playlist/', new_start)
                    start = comment_body_find_playlist + 9
                    end = comment_body_find_playlist + 31
                    url = comment.body[start:end]
                    if url not in playlist_ids_local and url not in playlist_ids_datastore:
                        playlist_ids_local.append(url)
                        playlistid = PlaylistID(value=url, language=language)
                        playlist_id_objects.append(playlistid)
                        if (playlist_id_objects >= 10):
                            ndb.put_multi(playlist_id_objects)
                            playlist_ids_objects = []
                    new_start = end
                else:
                    break
        time.sleep(2)

    if len(playlist_id_objects) > 0:
        ndb.put_multi(playlist_id_objects)


def scan_subreddit(language, access_token):
    """Scrapes specified subreddit for all Spotify links, and use that data to get
    playlist ids, track ids, and audio analyses of each track.
    """
    subreddits = {
        'german': 'German',
        'french': 'french',
        'spanish': 'learnspanish',
        'italian': 'italianlearning',
        'polish': 'learnpolish',
        'portuguese': 'portuguese',
        'russian': 'russian',
        'cantonese': 'Cantonese',
        'chinese': 'chineselanguage',
        'finnish': 'LearnFinnish',
        'japanese': 'LearnJapanese',
    }
    reddit = praw.Reddit(user_agent=USER_AGENT_REDDIT,
                         client_id=CLIENT_ID_REDDIT,
                         client_secret=CLIENT_SECRET_REDDIT,
                         disable_update_check=True)
    subreddit = reddit.subreddit(subreddits[language])
    playlist_ids_local = []
    playlist_ids_datastore = []
    for playlist_id in PlaylistID.query().filter(PlaylistID.language == language):
        playlist_ids_datastore.append(playlist_id.value)

    # find spotify playlist url in submission
    for submission in subreddit.search('spotify'):
        new_start = 0
        while True: # loop until all spotify links are found in submission
            if SPOTIFY_URL in submission.selftext[new_start:]:
                submission_text_find_playlist = submission.selftext.find('playlist/', new_start)
                start = submission_text_find_playlist + 9
                end = submission_text_find_playlist + 31
                url = submission.selftext[start:end]
                if url not in playlist_ids_local and url not in playlist_ids_datastore:
                    playlist_ids_local.append(url)
                    playlistid = PlaylistID(value=url, language=language)
                    playlistid.put()
                new_start = end
            else:
                break

    # find spotify playlist url if submission is only a link
    for submission in subreddit.search('spotify'):
        if SPOTIFY_URL in submission.url:
            submission_url_find_playlist = submission.url.find('playlist/', new_start)
            start = submission_url_find_playlist + 9
            end = submission_url_find_playlist + 31
            url = submission.url[start:end]
            if url not in playlist_ids_local and url not in playlist_ids_datastore:
                playlist_ids_local.append(url)
                playlistid = PlaylistID(value=url, language=language)
                playlistid.put()

    # find spotify playlist url in comments of all submissions
    deferred.defer(find_url_in_comments, playlist_ids_local, playlist_ids_datastore, subreddit, language)
    # get a playlist's tracks
    deferred.defer(get_playlists_track_ids, language, access_token)
    # get analysis of each track using the tracks' ids
    deferred.defer(create_tracks_from_audio_analysis, language, access_token)
    logging.debug('Tracks got')


def get_users_playlists(access_token):
    """get the current user's playlists to display them on the page"""
    playlists_endpoint = 'https://api.spotify.com/v1/me/playlists'
    headers = { 'Authorization' : 'Bearer ' + access_token }
    params = { 'offset' : 0 }
    playlists_response = requests.get(playlists_endpoint, headers=headers, params=params)
    playlists_json = playlists_response.json()
    return playlists_json['items']


def get_playlists_audio_features(access_token, language, playlist_id):
    # get playlists track ids
    playlists_tracks_link = 'http://api.spotify.com/v1/playlists/{}/tracks'.format(playlist_id)
    headers = { 'Authorization' : 'Bearer ' + access_token }
    params = {
        'fields' : 'total,items(track(id))',
        'offset' : 0,
    }
    tracks_response = requests.get(playlists_tracks_link, headers=headers, params=params)
    tracks_json = tracks_response.json()
    track_ids = [track['track']['id'] for track in tracks_json['items'] if track['track']['id'] is not None]
    track_ids_string = ','.join(track_ids)

    # get audio features of each of the tracks
    tracks_features_endpoint = 'https://api.spotify.com/v1/audio-features'
    headers = { 'Authorization' : 'Bearer ' + access_token }
    params = { 'ids' : track_ids_string }
    features_response = requests.get(tracks_features_endpoint, headers=headers, params=params)
    features_json = features_response.json()
    return features_json


def get_users_account_id(access_token):
    user_account_endpoint = 'https://api.spotify.com/v1/me'
    headers = { 'Authorization' : 'Bearer ' + access_token }
    user_account_response = requests.get(user_account_endpoint, headers=headers)
    user_account_json = user_account_response.json()
    return user_account_json['id']


def calculate_average_energy(features_json):
    if len(features_json) == 0: return -1
    total_energy = 0
    for feature in features_json['audio_features']:
        total_energy += feature['energy']
    avg_energy = total_energy / len(features_json['audio_features'])
    return avg_energy


def calculate_average_acousticness(features_json):
    if len(features_json) == 0: return -1
    total_acousticness = 0
    for feature in features_json['audio_features']:
        total_acousticness += feature['acousticness']
    avg_acousticness = total_acousticness / len(features_json['audio_features'])
    return avg_acousticness


def calculate_average_danceability(features_json):
    if len(features_json) == 0: return -1
    total_danceability = 0
    for feature in features_json['audio_features']:
        total_danceability += feature['danceability']
    avg_danceability = total_danceability / len(features_json['audio_features'])
    return avg_danceability


def calculate_average_instrumentalness(features_json):
    if len(features_json) == 0: return -1
    total_instrumentalness = 0
    for feature in features_json['audio_features']:
        total_instrumentalness += feature['instrumentalness']
    avg_instrumentalness = total_instrumentalness / len(features_json['audio_features'])
    return avg_instrumentalness


def calculate_average_liveness(features_json):
    if len(features_json) == 0: return -1
    total_liveness = 0
    for feature in features_json['audio_features']:
        total_liveness += feature['liveness']
    avg_liveness = total_liveness / len(features_json['audio_features'])
    return avg_liveness


def calculate_average_valence(features_json):
    if len(features_json) == 0: return -1
    total_valence = 0
    for feature in features_json['audio_features']:
        total_valence += feature['valence']
    avg_valence = total_valence / len(features_json['audio_features'])
    return avg_valence


def calculate_average_tempo(features_json):
    if len(features_json) == 0: return -1
    total_tempo = 0
    for feature in features_json['audio_features']:
        total_tempo += feature['tempo']
    avg_tempo = total_tempo / len(features_json['audio_features'])
    return avg_tempo


def calculate_average_loudness(features_json):
    if len(features_json) == 0: return -1
    total_loudness = 0
    for feature in features_json['audio_features']:
        total_loudness += feature['loudness']
    avg_loudness = total_loudness / len(features_json['audio_features'])
    return avg_loudness


# TODO: Implement 'mode'?


# Pages for adding songs to the database

class AddSongs(webapp2.RequestHandler):
    def get(self):
        template = env.get_template('templates/home.html')
        self.response.write(template.render())


class Search(webapp2.RequestHandler):
    def get(self):
        code = self.request.get('code')
        template_vars = { 'code' : code }

        template = env.get_template('templates/search.html')
        self.response.write(template.render(template_vars))

    def post(self):
        code = self.request.get('code')
        language = self.request.get('language')

        if code:
            payload = {
                'grant_type' : 'authorization_code',
                'code' : code,
                'redirect_uri' : redirect_uri,
            }
            headers = { 'Authorization' : 'Basic ' + base64.b64encode(CLIENT_ID_SPOTIFY + ':' + CLIENT_SECRET_SPOTIFY) }
            response = requests.post(SPOTIFY_TOKEN_URL, data=payload, headers=headers)
            token = response.json()

            if token:
                access_token = token['access_token']
                refresh_token = token['refresh_token']

                scan_subreddit(language, access_token)

        template = env.get_template('templates/search.html')
        self.response.write(template.render())


class Login(webapp2.RequestHandler):
    def get(self):
        headers = {
            'client_id' : CLIENT_ID_SPOTIFY,
            'response_type' : 'code',
            'redirect_uri' : redirect_uri,
            'scope' : scope,
        }

        url = '{}?client_id={}' \
                '&response_type=code' \
                '&redirect_uri={}' \
                '&scope={}'.format(SPOTIFY_AUTH_URL, CLIENT_ID_SPOTIFY, redirect_uri, scope)

        self.redirect(url)

        template = env.get_template('templates/login.html')
        self.response.write(template.render())


# Pages for the main website

class HomeAndLoginPage(webapp2.RequestHandler):
    def get(self):
        global code_global
        template_vars = { 'code' : code_global }

        # if not logged in, html page will just show log-in page
        # if logged in, then continue to core functionality of the app
        if code_global or access_token_global:
            payload = {
                'grant_type' : 'authorization_code',
                'code' : code_global,
                'redirect_uri' : redirect_uri,
            }

            headers = { 'Authorization' : 'Basic ' + base64.b64encode(CLIENT_ID_SPOTIFY + ':' + CLIENT_SECRET_SPOTIFY) }
            response = requests.post(SPOTIFY_TOKEN_URL, data=payload, headers=headers)
            token = response.json()

            # if there's a valid token
            try:
                access_token = token['access_token']
                refresh_token = token['refresh_token']

                global access_token_global
                global refresh_token_global
                access_token_global = token['access_token']
                refresh_token_global = token['refresh_token']

                spotify_user_id = get_users_account_id(access_token_global)

                playlists_json = get_users_playlists(access_token)
                template_vars['playlists_json'] = playlists_json
                template_vars['access_token'] = access_token
            except KeyError:
                # KeyError appears when reloading the page
                # if that happens, reset everything and log the user out
                code_global = ''
                access_token_global = ''
                refresh_token_global = ''
                self.redirect('/')

        template = env.get_template('templates/homeAndLoginPage.html')
        self.response.write(template.render(template_vars))


class StartAnalysis(webapp2.RequestHandler):
    """POST request to the server to calculate the best possible matches for songs."""
    def post(self):
        playlist = self.request.get('playlist')
        language = self.request.get('language')
        # to make sure that the user visiting this page is logged in
        if playlist and access_token_global:
            spotify_user_id = get_users_account_id(access_token_global)
            template_vars = { 'access_token' : access_token_global }

            audio_features_json = get_playlists_audio_features(access_token_global, language, playlist)

            avg_energy = round(calculate_average_energy(audio_features_json), 3)
            avg_tempo = round(calculate_average_tempo(audio_features_json), 3)
            avg_danceability = round(calculate_average_danceability(audio_features_json), 3)
            avg_energy = round(calculate_average_acousticness(audio_features_json), 3)
            avg_instrumentalness = round(calculate_average_instrumentalness(audio_features_json), 3)
            avg_liveness = round(calculate_average_liveness(audio_features_json), 3)

            matches = []

            # first, run the 'energy' filter
            first_matches = Track.query().filter(Track.energy >= (avg_energy - .1),
                                                 Track.energy <= (avg_energy + .1))
            first_matches_len = len(matches)
            print(first_matches_len)

            # if there are too many matches, run the 'danceability' filter
            second_matches = 0
            if len(matches) > 20:
                second_matches = matches.filter(Track.danceability >= (avg_danceability - .1),
                                                Track.danceability <= (avg_danceability + .1))
            second_matches_len = len(matches)
            print(len(second_matches_len))
            if 20 - first_matches_len < 20 - second_matches_len:
                matches = first_matches
            else:
                matches = second_matches


            # matches = matches.filter(Track.instrumentalness >= (avg_instrumentalness - .1),
            #                          Track.instrumentalness <= (avg_instrumentalness + .1))


            match_ids = [match.track_id for match in matches]
            self.response.write(match_ids)

    # loudness = ndb.FloatProperty()
    # tempo = ndb.FloatProperty()
    # danceability = ndb.FloatProperty()
    # energy = ndb.FloatProperty()
    # acousticness = ndb.FloatProperty()
    # instrumentalness = ndb.FloatProperty()
    # liveness = ndb.FloatProperty()
    # valence = ndb.FloatProperty()
    # mode = ndb.IntegerProperty()


class Redirect(webapp2.RequestHandler):
    """Gets the code after getting redirected from the Spotify login page"""
    def get(self):
        global code_global
        code_global = self.request.get('code')
        self.redirect('/')

        template = env.get_template('templates/success.html')
        self.response.write(template.render())


class Login2(webapp2.RequestHandler):
    def get(self):
        template = env.get_template('templates/loginPage2.html')
        self.response.write(template.render())

class Playlist(webapp2.RequestHandler):
    def get(self):
        template = env.get_template('templates/playlist.html')
        self.response.write(template.render())


app = webapp2.WSGIApplication([
    ### Frontend
    ('/', Playlist),
    # ('/', HomeAndLoginPage),
    ('/start-analysis', StartAnalysis),
    ### Backend
    ('/add', AddSongs),
    ('/login', Login),
    ('/search', Search),
    ('/redirect', Redirect),
], debug=True)
