import praw
import time
from google.appengine.ext import deferred
from google.appengine.ext import ndb

import const
import helper_funcs as help
import models

def get_playlists_track_ids(language, access_token):
    """Using the playlist ids, get all of their tracks and track ids."""
    print('-----------GETTING TRACK IDS-----------')
    track_ids = []
    playlist_ids = models.PlaylistID.query().filter(models.PlaylistID.language == language)
    for playlist_id in playlist_ids:
        id = playlist_id.value
        playlists_tracks_endpoint = 'http://api.spotify.com/v1/playlists/{}/tracks'.format(id)
        headers = { 'Authorization' : 'Bearer ' + access_token }
        params = {
            'fields': 'total,items(track(id))',
            'offset': 0,
        }
        tracks_response = help.request_endpoint(playlists_tracks_endpoint, None, headers, params)
        tracks_json = tracks_response.json()

        # Spotify limits to only 100 songs per request, so set starting location
        # in playlist to +100 every loop to eventually get all songs
        if len(tracks_json) > 1: # if valid playlist URL
            for i in range((tracks_json['total'] / 100) + 1):
                try:
                    tracks_response = help.request_endpoint(playlists_tracks_endpoint, None, headers, params)
                    tracks_json = tracks_response.json()
                    for element in tracks_json['items']:
                        track_ids_datastore = models.TrackID.query().filter(models.TrackID.value == element['track']['id']).get()
                        if (element['track']['id'] and element['track']['id'] not in track_ids
                            and not track_ids_datastore): # make sure no repeats
                            trackid = models.TrackID(value=element['track']['id'], language=language)
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
    print('-----------MAKING TRACKS-----------')
    tracks = []
    track_ids = models.TrackID.query().filter(models.TrackID.language == language)

    for track_id in track_ids:
        id = track_id.value
        spotify_audio_features_endpoint = 'http://api.spotify.com/v1/audio-features/{}'.format(id)
        headers = { 'Authorization' : 'Bearer ' + access_token }
        features_response = help.request_endpoint(spotify_audio_features_endpoint, None, headers)
        features = features_response.json()
        if features:
            print('making track')
            track = models.Track(
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
                mode=features['mode'],
                speechiness=features['speechiness'])
            tracks.append(track)
            # add tracks in bulk as to not get Error 429: too many requests
            if len(tracks) >= 100:
                print('put tracks')
                ndb.put_multi(tracks)
                tracks = []
        time.sleep(1.4)

    # put any remaining tracks
    if len(tracks) > 0:
        ndb.put_multi(tracks)

    print('-----------DONE MAKING TRACKS-----------')

def find_url_in_comments(playlist_ids_local, playlist_ids_datastore, subreddit, language):
    """Finds links to Spotify playlists in the comment section of posts."""
    print('-----------SCRAPING COMMENTS-----------')
    try:
        playlist_id_objects = []
        for submission in subreddit.search('spotify'):
            submission.comments.replace_more(limit=None)
            comments = submission.comments.list()
            for comment in comments:
                new_start = 0
                while True: # loop until all spotify links are found in comment
                    if const.SPOTIFY_URL in comment.body[new_start:]:
                        comment_body_find_playlist = comment.body.find('playlist/', new_start)
                        start = comment_body_find_playlist + 9
                        end = comment_body_find_playlist + 31
                        url = comment.body[start:end]
                        if url not in playlist_ids_local and url not in playlist_ids_datastore:
                            playlist_ids_local.append(url)
                            playlistid = models.PlaylistID(value=url, language=language)
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
    except Exception as e:
        print('ERROR ERROR! Code: {c}, Message: {m}'.format(c = type(e).__name__, m = str(e)))


def scan_subreddit(language, access_token):
    """Scrapes specified subreddit for all Spotify links, and use that data to get
    playlist ids, track ids, and audio analyses of each track.
    """
    print('-----------SCRAPING-----------')
    reddit = praw.Reddit(user_agent=const.USER_AGENT_REDDIT,
                         client_id=const.CLIENT_ID_REDDIT,
                         client_secret=const.CLIENT_SECRET_REDDIT,
                         disable_update_check=True)
    subreddit = reddit.subreddit(const.subreddits[language])
    playlist_ids_local = []
    playlist_ids_datastore = []
    for playlist_id in models.PlaylistID.query().filter(models.PlaylistID.language == language):
        playlist_ids_datastore.append(playlist_id.value)

    # find spotify playlist url in submission
    for submission in subreddit.search('spotify'):
        new_start = 0
        while True: # loop until all spotify links are found in submission
            if const.SPOTIFY_URL in submission.selftext[new_start:]:
                submission_text_find_playlist = submission.selftext.find('playlist/', new_start)
                start = submission_text_find_playlist + 9
                end = submission_text_find_playlist + 31
                url = submission.selftext[start:end]
                if url not in playlist_ids_local and url not in playlist_ids_datastore:
                    playlist_ids_local.append(url)
                    playlistid = models.PlaylistID(value=url, language=language)
                    playlistid.put()
                new_start = end
            else:
                break

    # find spotify playlist url if submission is only a link
    for submission in subreddit.search('spotify'):
        if const.SPOTIFY_URL in submission.url:
            submission_url_find_playlist = submission.url.find('playlist/', new_start)
            start = submission_url_find_playlist + 9
            end = submission_url_find_playlist + 31
            url = submission.url[start:end]
            if url not in playlist_ids_local and url not in playlist_ids_datastore:
                playlist_ids_local.append(url)
                playlistid = models.PlaylistID(value=url, language=language)
                playlistid.put()

    # find spotify playlist url in comments of all submissions
    deferred.defer(find_url_in_comments, playlist_ids_local, playlist_ids_datastore, subreddit, language)
    # get a playlist's tracks
    deferred.defer(get_playlists_track_ids, language, access_token)
    # get analysis of each track using the tracks' ids
    deferred.defer(create_tracks_from_audio_analysis, language, access_token)