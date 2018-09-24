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

from google.appengine.api import users
from google.appengine.ext import deferred
from google.appengine.ext import ndb

import requests_toolbelt.adapters.appengine
requests_toolbelt.adapters.appengine.monkeypatch()

# TODO:
# - work with spotify link in main post and on wiki, not just in comments
# X make sure no repeats in songs
# X works if multiple links in comment
# X make sure works if invalid spotify link
# X make sure works with replies to comments
# X works with shortened text url (video *here*)
# X make sure works if self uploaded spotify song

# Client Keys
CLIENT_ID = config.CLIENT_ID
CLIENT_SECRET = config.CLIENT_SECRET

# Spotify URLs
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

class TrackID(ndb.Model):
    value = ndb.StringProperty()
    language = ndb.StringProperty()

class PlaylistID(ndb.Model):
    value = ndb.StringProperty()
    language = ndb.StringProperty()

# Functions

# Using the playlist ids, get all of their tracks and track_ids
def get_playlists_track_ids(language, access_token):
    track_ids = []
    playlist_ids = PlaylistID.query().filter(PlaylistID.language == language)
    for playlist_id in playlist_ids:
        id = playlist_id.value
        playlists_tracks_link = "http://api.spotify.com/v1/playlists/{}/tracks".format(id)
        headers = { "Authorization" : "Bearer " + access_token }
        params = {
            "fields" : "total,items(track(id))",
            "offset" : 0,
        }

        tracks_response = requests.get(playlists_tracks_link, headers=headers, params=params)
        tracks_json = tracks_response.json()

        # Spotify limits to only 100 songs per request, so set starting location
        # in playlist to +100 every loop to eventually get all songs
        if len(tracks_json) > 1: # if valid playlist URL
            for i in range((tracks_json["total"] / 100) + 1):
                try:
                    tracks_response = requests.get(playlists_tracks_link, headers=headers, params=params)
                    tracks_json = tracks_response.json()
                    for element in tracks_json["items"]:
                        track_ids_datastore = TrackID.query().filter(TrackID.value == element["track"]["id"]).get()
                        if (element["track"]["id"] and element["track"]["id"] not in track_ids
                            and not track_ids_datastore): # make sure no repeats
                            # track_ids.append(element["track"]["id"])
                            trackid = TrackID(value=element["track"]["id"], language=language)
                            track_ids.append(trackid)
                            if len(track_ids) >= 100:
                                ndb.put_multi(track_ids)
                                track_ids = []

                            # trackid.put()
                    params["offset"] += 100
                except KeyError: # if no track id is found
                    continue

            if len(track_ids) > 0:
                ndb.put_multi(track_ids)


# Retrieves the track_ids from Datastore and uses it to get the audio analyses
# of the tracks and store that once again in Datastore
def create_tracks_from_audio_analysis(language, access_token):
    tracks = []
    track_ids = TrackID.query().filter(TrackID.language == language)
    for track_id in track_ids:
        id = track_id.value
        spotify_audio_features_link = "http://api.spotify.com/v1/audio-features/{}".format(id)
        headers = { "Authorization" : "Bearer " + access_token }
        features_response = requests.get(spotify_audio_features_link, headers=headers)
        features = features_response.json()
        if features:
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
            # add tracks in bulk as to not get Error 429: too many requests
            if len(tracks) >= 100:
                ndb.put_multi(tracks)
                tracks = []

        time.sleep(1.4)

    # put any remaining tracks
    if len(tracks) > 0:
        ndb.put_multi(tracks)


def find_url_in_comments(playlist_ids_local, playlist_ids_datastore, subreddit, language):
    playlist_id_objects = []
    for submission in subreddit.search("spotify"):
        submission.comments.replace_more(limit=None)
        comments = submission.comments.list()
        for comment in comments:
            new_start = 0
            while True: # loop until all spotify links are found in comment
                if SPOTIFY_URL in comment.body[new_start:]:
                    comment_body_find_playlist = comment.body.find("playlist/", new_start)
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


# Scrape specified subreddit for all Spotify links, and use that data to get
# playlist ids, track ids, and audio analyses of each track
def scan_subreddit(language, access_token):
    reddit = praw.Reddit("bot1")
    subreddit = reddit.subreddit(language)
    playlist_ids_local = []
    playlist_ids_datastore = []
    for playlist_id in PlaylistID.query().filter(PlaylistID.language == language):
        playlist_ids_datastore.append(playlist_id.value)

    # find spotify playlist url in submission
    for submission in subreddit.search("spotify"):
        new_start = 0
        while True: # loop until all spotify links are found in submission
            if SPOTIFY_URL in submission.selftext[new_start:]:
                submission_text_find_playlist = submission.selftext.find("playlist/", new_start)
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
    for submission in subreddit.search("spotify"):
        if SPOTIFY_URL in submission.url:
            submission_url_find_playlist = submission.url.find("playlist/", new_start)
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
    logging.debug("Tracks got")


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

                scan_subreddit(language, access_token)

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
