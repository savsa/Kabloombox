import webapp2
import jinja2
import os
import requests
import time
import json
import base64

import praw

import config


from google.appengine.api import users
from google.appengine.ext import ndb

import requests_toolbelt.adapters.appengine
requests_toolbelt.adapters.appengine.monkeypatch()

# Client Keys
CLIENT_ID = config.CLIENT_ID
CLIENT_SECRET = config.CLIENT_SECRET

SPOTIFY_URL = "open.spotify.com/user/"

#Spotify URLs
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE_URL = "https://api.spotify.com"

redirect_uri = "http://localhost:8080/"
scope = "user-library-read user-read-private user-read-email"

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




env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

class HomePage(webapp2.RequestHandler):
    def get(self):

        code = self.request.get("code")

        if code:
            payload = {
                "grant_type" : "authorization_code",
                "code" : code,
                "redirect_uri" : redirect_uri,
            }

            headers = {
                "Authorization" : "Basic " + base64.b64encode(CLIENT_ID + ":" + CLIENT_SECRET)
            }

            response = requests.post(SPOTIFY_TOKEN_URL, data=payload, headers=headers)
            token = response.json()

            if token:
                access_token = token["access_token"]
                refresh_token = token["refresh_token"]

                scan_subreddit(access_token)

        templateVars = {

        }

        template = env.get_template("templates/home.html")
        self.response.write(template.render(templateVars))

    def post(self):
        pass
        # response = json.dumps(post_request)
        #
        # if response:
        #     print("RESPONSE RESPONSE RESPONSE REPONSE: " + response)

def scan_subreddit(access_token):

    #subreddit = self.request.get("subreddit")

    spotify_audio_features_link = "https://api.spotify.com/v1/audio-features/"

    reddit = praw.Reddit("bot1")
    subreddit = reddit.subreddit("thestereo")

    playlist_ids = []

    for comment in subreddit.comments():
        if SPOTIFY_URL in comment.body:
            start = comment.body.find("playlist/") + 9
            end = comment.body.find("playlist/") + 31
            url = comment.body[start:end]
            playlist_ids.append(url)


    track_ids = []

    for id in playlist_ids:
        # get a playlist's tracks
        playlists_tracks_link = "http://api.spotify.com/v1/playlists/{}/tracks".format(id)

        headers = { "Authorization" : "Bearer " + access_token }
        params = { "fields" : "items(track(id))" }

        tracks_response = requests.get(playlists_tracks_link, headers=headers, params=params)
        tracks = tracks_response.json()

    #

    # payload = { "id" : playlist_ids[0] }
    # headers = { "Authorization" : "Bearer " + access_token }
    #
    # features_response = requests.get(spotify_audio_features_link, data=payload, headers=headers)
    # features = features_response.json()
    #
    # print('FEATURES: ')
    # print(features)

    # track = Track(
    #     track_id=playlist_ids[0],
    #     language="german",
    #     loudness=features["loudness"],
    #     tempo=features["tempo"],
    #     danceability=features["danceability"],
    #     energy=features["energy"],
    #     acousticness=features["acousticness"],
    #     instrumentalness=features["instrumentalness"],
    #     liveness=features["liveness"],
    # )

    # for id in spotify_ids:
    #     payload = { "id" : id }
    #     headers = { "Authorization" : "Bearer " + access_token }
    #
    #     features_response = requests.get(spotify_audio_features_link, data=payload, headers=headers)
    #     features = features_response.json()
    #
    #     track = Track(
    #         track_id=id,
    #         language="german",
    #         loudness=features["loudness"],
    #         tempo=features["tempo"],
    #         danceability=features["danceability"],
    #         energy=features["energy"],
    #         acousticness=features["acousticness"],
    #         instrumentalness=features["instrumentalness"],
    #         liveness=features["liveness"],
    #     )






class Login(webapp2.RequestHandler):
    def get(self):

        headers = {
            "client_id" : CLIENT_ID,
            "response_type" : "code",
            "redirect_uri" : redirect_uri,
            "scope" : scope,
        }

        url = """{}?client_id={}&response_type=code&redirect_uri={}&scope={}""".format(SPOTIFY_AUTH_URL, CLIENT_ID,redirect_uri, scope)


        self.redirect(url)

        templateVars = {

        }

        template = env.get_template("templates/login.html")
        self.response.write(template.render(templateVars))


app = webapp2.WSGIApplication([
    ('/', HomePage),
    ('/login', Login),
], debug=True)
