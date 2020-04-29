from google.appengine.ext import ndb

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

class Token:
    def __init__(self, access_token, refresh_token):
        self.access_token = access_token
        self.refresh_token = refresh_token