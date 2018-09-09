import webapp2
import jinja2
import requests
import json
import base64
import os
import time

import praw
import config

from google.appengine.api import users
from google.appengine.ext import ndb

import requests_toolbelt.adapters.appengine
requests_toolbelt.adapters.appengine.monkeypatch()

# Client Keys
CLIENT_ID = config.CLIENT_ID
CLIENT_SECRET = config.CLIENT_SECRET


#Spotify URLs
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE_URL = "https://api.spotify.com"
SPOTIFY_URL = "open.spotify.com/user/"


redirect_uri = "http://localhost:8080/search"
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
        template = env.get_template("templates/home.html")
        self.response.write(template.render())


class Search(webapp2.RequestHandler):
    def get(self):

        code = self.request.get("code")
        print('code code code ' + code)

        template_vars = {
            "code" : code,
        }

        template = env.get_template("templates/search.html")
        self.response.write(template.render(template_vars))




    def post(self):
        code = self.request.get("code")
        language = self.request.get("language")

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

                tracks = scan_subreddit(access_token, language)
                print(tracks)



        template = env.get_template("templates/search.html")
        self.response.write(template.render())



def get_playlists_track_ids(playlist_ids, access_token, ):


def scan_subreddit(access_token, language):

    #subreddit = self.request.get("subreddit")

    reddit = praw.Reddit("bot1")
    subreddit = reddit.subreddit(language)

    playlist_ids = []

    for comment in subreddit.comments():
        if SPOTIFY_URL in comment.body:
            start = comment.body.find("playlist/") + 9
            end = comment.body.find("playlist/") + 31
            url = comment.body[start:end]
            playlist_ids.append(url)


    # get a playlist's tracks
    #track_ids = []

    track_ids = get_playlists_track_ids()

    for id in playlist_ids:

        playlists_tracks_link = "http://api.spotify.com/v1/playlists/{}/tracks".format(id)

        headers = { "Authorization" : "Bearer " + access_token }
        params = { "fields" : "items(track(id))" }

        tracks_response = requests.get(playlists_tracks_link, headers=headers, params=params)
        tracks_json = tracks_response.json()

        track_ids = [element["track"]["id"] for element in tracks_json["items"]]



    # get analysis of each track
    tracks = []

    for id in track_ids:

        spotify_audio_features_link = "http://api.spotify.com/v1/audio-features/{}".format(id)

        headers = { "Authorization" : "Bearer " + access_token }

        features_response = requests.get(spotify_audio_features_link, headers=headers)
        features = features_response.json()

        if features:

            track = Track(
                track_id=id,
                language=subreddit,
                loudness=features["loudness"],
                tempo=features["tempo"],
                danceability=features["danceability"],
                energy=features["energy"],
                acousticness=features["acousticness"],
                instrumentalness=features["instrumentalness"],
                liveness=features["liveness"],
            )

            tracks.append(track)

        time.sleep(.2)

    print(tracks)

    return tracks




class Login(webapp2.RequestHandler):
    def get(self):

        headers = {
            "client_id" : CLIENT_ID,
            "response_type" : "code",
            "redirect_uri" : redirect_uri,
            "scope" : scope,
        }

        url = "{}?client_id={}" \
                "&response_type=code" \
                "&redirect_uri={}" \
                "&scope={}".format(SPOTIFY_AUTH_URL, CLIENT_ID, redirect_uri, scope)


        self.redirect(url)

        template = env.get_template("templates/login.html")
        self.response.write(template.render())


app = webapp2.WSGIApplication([
    ('/', HomePage),
    ('/login', Login),
    ('/search', Search),
], debug=True)
