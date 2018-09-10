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

# TODO:
# - work with spotify link in main post and on wiki, not just in comments
# - make sure no repeats in songs
# X make sure works if invalid spotify link
# X make sure works with replies to comments
# X works with shortened text url (video *here*)
# X make sure works if self uploaded spotify song

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

# Functions
def get_playlists_track_ids(playlist_ids, access_token):
    track_ids = []
    for id in playlist_ids:
        playlists_tracks_link = "http://api.spotify.com/v1/playlists/{}/tracks".format(id)
        headers = { "Authorization" : "Bearer " + access_token }
        params = {
            "fields" : "total,items(track(id))",
            "offset" : 0,
        }

        tracks_response = requests.get(playlists_tracks_link, headers=headers, params=params)
        tracks_json = tracks_response.json()

        if len(tracks_json) > 1: # valid playlist URL
            for i in range((tracks_json["total"] / 100) + 1):
                try:
                    tracks_response = requests.get(playlists_tracks_link, headers=headers, params=params)
                    tracks_json = tracks_response.json()
                    for element in tracks_json["items"]:
                        if element["track"]["id"] and element["track"]["id"] not in track_ids: # make sure no repeats
                            track_ids.append(element["track"]["id"])
                    params["offset"] += 100
                except KeyError:
                    continue

    return track_ids


def create_tracks_from_audio_analysis(track_ids, language, access_token):
    tracks = []

    for id in track_ids:
        print("---------TRACK ID: " + id + "---------")
        spotify_audio_features_link = "http://api.spotify.com/v1/audio-features/{}".format(id)
        headers = { "Authorization" : "Bearer " + access_token }
        features_response = requests.get(spotify_audio_features_link, headers=headers)
        features = features_response.json()

        if features:
            print(features)
            track = Track(
                track_id=id,
                language=language,
                loudness=features["loudness"],
                tempo=features["tempo"],
                danceability=features["danceability"],
                energy=features["energy"],
                acousticness=features["acousticness"],
                instrumentalness=features["instrumentalness"],
                liveness=features["liveness"],
                valence=features["valence"],
                mode=features["mode"])
            tracks.append(track)

        time.sleep(.8)

    return tracks


def scan_subreddit(language, access_token):
    reddit = praw.Reddit("bot1")
    subreddit = reddit.subreddit(language)

    playlist_ids = []
    for submission in subreddit.search("spotify"):
        print(submission.title.encode("utf-8"))

        # find spotify playlist url in submission
        if SPOTIFY_URL in submission.selftext:
            start = submission.selftext.find("playlist/") + 9
            end = submission.selftext.find("playlist/") + 31
            url = submission.selftext[start:end]
            playlist_ids.append(url)
            print(url)

        # find spotify playlist url if submission is only a link
        if SPOTIFY_URL in submission.url:
            start = submission.url.find("playlist/") + 9
            end = submission.url.find("playlist/") + 31
            url = submission.url[start:end]
            playlist_ids.append(url)
            print("URL------------")
            print(url)

        # find spotify playlist url in submission's comments
        submission.comments.replace_more(limit=None)
        comments = submission.comments.list()
        for comment in comments:
            if SPOTIFY_URL in comment.body:
                start = comment.body.find("playlist/") + 9
                end = comment.body.find("playlist/") + 31
                url = comment.body[start:end]
                playlist_ids.append(url)
                print(url)
        time.sleep(3)

    # get a playlist's tracks
    track_ids = get_playlists_track_ids(playlist_ids, access_token)
    # get analysis of each track using the tracks' ids
    tracks = create_tracks_from_audio_analysis(track_ids, language, access_token)

    return tracks


# Pages
class HomePage(webapp2.RequestHandler):
    def get(self):
        template = env.get_template("templates/home.html")
        self.response.write(template.render())


class Search(webapp2.RequestHandler):
    def get(self):
        code = self.request.get("code")

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

            headers = { "Authorization" : "Basic " + base64.b64encode(CLIENT_ID + ":" + CLIENT_SECRET) }

            response = requests.post(SPOTIFY_TOKEN_URL, data=payload, headers=headers)
            token = response.json()

            if token:
                access_token = token["access_token"]
                refresh_token = token["refresh_token"]

                tracks = scan_subreddit(language, access_token)
                print('alkadjflkdfj')
                print("LENGTH OF TRACKS: " + str(len(tracks)))

        template = env.get_template("templates/search.html")
        self.response.write(template.render())


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
