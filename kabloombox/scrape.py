import praw
import time
import flask
import logging
import json
import base64
import math

from . import const
from . import helper_funcs as help
from . import models
from . import app, db, client, parent


# @app.route('/get_playlists_track_ids', methods=['POST'])
def get_playlists_track_ids(language, access_token):
    # language, access_token
    """Using the playlist ids, get all of their tracks and track ids."""
    logging.debug('-----------GETTING TRACK IDS-----------')
    track_ids = list(db.collection('track_ids').where(
        'language', '==', language).stream())
    playlist_ids = db.collection('playlist_ids').where(
        'language', '==', language).stream()
    headers = {'Authorization': 'Bearer ' + access_token}
    params = {
        'fields': 'total,items(track(id))',
        'offset': 0,
    }
    logging.debug('1')
    for playlist_id in playlist_ids:
        logging.debug('2')
        id = playlist_id.get('value')
        logging.debug(id)
        playlists_tracks_endpoint = f'http://api.spotify.com/v1/playlists/{id}/tracks'
        tracks_response, _ = help.request_endpoint(
            method='GET', endpoint=playlists_tracks_endpoint,
            access_token=None, headers=headers, params=params)

        if not tracks_response:
            logging.debug(tracks_response.json())
            continue

        logging.debug('3')

        tracks_json = tracks_response.json()

        # Spotify limits to only 100 songs per request, so set starting
        # location in playlist to +100 every loop to eventually get all songs
        logging.debug('A')
        num_tracks = tracks_json['total']
        for _ in range(math.ceil(num_tracks / 100)):
            logging.debug('B')
            try:
                tracks_response, _ = help.request_endpoint(
                    method='GET', endpoint=playlists_tracks_endpoint,
                    access_token=None, headers=headers, params=params)
                if not tracks_response:
                    logging.debug('ERROR')
                    continue
                logging.debug('C')
                tracks_json = tracks_response.json()
                for element in tracks_json['items']:
                    logging.debug('D')
                    # check for repeats
                    if (element['track']['id']
                            and element['track']['id'] not in track_ids):
                        logging.debug('B')
                        trackid = models.TrackID(
                            value=element['track']['id'], language=language)
                        track_ids.append(trackid)
                        db.collection('track_ids').add(trackid.to_dict())
                        logging.debug('MADE TRACK_ID')
                params['offset'] += 100
            except KeyError:  # if no track id is found
                continue


# @app.route('/create_tracks_from_audio_analysis', methods=['POST'])
def create_tracks_from_audio_analysis(language, access_token):
    """Retrieves the track_ids from firestore, uses thoses to get the audio
    analyses of the tracks, then stores that in firestore.
    """
    logging.debug('-----------MAKING TRACKS-----------')

    track_ids = (db.collection('track_ids').where(
        'language', '==', language).stream())

    for track_id in track_ids:
        id = track_id.get('value')
        endpoint = f'http://api.spotify.com/v1/audio-features/{id}'
        headers = {'Authorization': 'Bearer ' + access_token}
        features_response, _ = help.request_endpoint(
            method='GET', endpoint=endpoint, access_token=None,
            headers=headers)
        if not features_response:
            continue
        features = features_response.json()
        logging.debug('making track')
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
        db.collection('tracks').add(track.to_dict())
        logging.debug('MADE TRACK')

    track_model = db.collection('tracks').stream()
    for t in track_model:
        logging.debug(t.to_dict())

    logging.info('-----------DONE MAKING TRACKS-----------')


# @app.route('/find_url_in_comments', methods=['POST'])
def find_url_in_comments(
        new_playlist_ids, playlist_ids, subreddit, language):
    """Finds links to Spotify playlists in the comment section of posts."""
    logging.debug('-----------SCRAPING COMMENTS-----------')

    # try:
    for submission in subreddit.search('spotify'):
        submission.comments.replace_more(limit=None)
        comments = submission.comments.list()
        for comment in comments:
            new_start = 0
            while const.SPOTIFY_URL in comment.body[new_start:]:
                comment_body_find_playlist = comment.body.find(
                    'playlist/', new_start)
                start = comment_body_find_playlist + 9
                end = comment_body_find_playlist + 31
                url = comment.body[start:end]
                if (url not in new_playlist_ids and url not in playlist_ids):
                    new_playlist_ids.append(url)
                    playlistid = models.PlaylistID(
                        value=url, language=language)
                    db.collection('playlist_ids').add(
                        playlistid.to_dict())
                    logging.debug('MADE PLAYLIST ID')
                new_start = end
        # time.sleep(2)

    # except Exception as e:
    #     logging.debug('ERROR ERROR! Code: {c}, Message: {m}'.format(
    #         c=type(e).__name__, m=str(e)))


def scan_subreddit(language, access_token):
    """Scrapes specified subreddit for all Spotify links, and use that data to
    get playlist ids, track ids, and audio analyses of each track.
    """
    logging.debug('-----------SCRAPING-----------')
    reddit = praw.Reddit(
        user_agent=const.USER_AGENT_REDDIT,
        client_id=const.CLIENT_ID_REDDIT,
        client_secret=const.CLIENT_SECRET_REDDIT,
        disable_update_check=True)

    subreddit = reddit.subreddit(const.subreddits[language])
    new_playlist_ids = []
    playlist_ids = list(db.collection('playlist_ids').where(
        'language', '==', language).stream())
    logging.debug(len(playlist_ids))

    # find spotify playlist url in submission
    for submission in subreddit.search('spotify'):
        new_start = 0
        while True:  # loop until all spotify links are found in submission
            if const.SPOTIFY_URL not in submission.selftext[new_start:]:
                break
            submission_text_find_playlist = submission.selftext.find(
                'playlist/', new_start)
            start = submission_text_find_playlist + 9
            end = submission_text_find_playlist + 31
            url = submission.selftext[start:end]
            if (url not in new_playlist_ids
                    and url not in playlist_ids):
                new_playlist_ids.append(url)
                playlistid = models.PlaylistID(value=url, language=language)
                db.collection('playlist_ids').add(playlistid.to_dict())
                logging.debug('MADE PLAYLIST_ID')
            new_start = end

    # find spotify playlist url if submission is only a link
    for submission in subreddit.search('spotify'):
        if const.SPOTIFY_URL in submission.url:
            submission_url_find_playlist = submission.url.find(
                'playlist/', new_start)
            start = submission_url_find_playlist + 9
            end = submission_url_find_playlist + 31
            url = submission.url[start:end]
            if (url not in new_playlist_ids
                    and url not in playlist_ids):
                new_playlist_ids.append(url)
                playlistid = models.PlaylistID(value=url, language=language)
                db.collection('playlist_ids').add(playlistid.to_dict())
                logging.debug('MADE PLAYLIST_ID')

    find_url_in_comments(
        new_playlist_ids, playlist_ids, subreddit, language)
    # return
    get_playlists_track_ids(language, access_token)
    create_tracks_from_audio_analysis(language, access_token)





# import praw
# import time
# import flask
# import logging
# import json
# import base64
#
# from . import const
# from . import helper_funcs as help
# from . import models
# from . import app, db, client, parent
#
#
# @app.route('/get_playlists_track_ids', methods=['POST'])
# def get_playlists_track_ids():
#     # language, access_token
#     """Using the playlist ids, get all of their tracks and track ids."""
#     logging.debug('-----------GETTING TRACK IDS-----------')
#     if flask.request.headers.get('X-Appengine-Taskname') is None:
#         logging.debug('Invalid Task: No X-Appengine-Taskname request header found')
#         return 'Bad Request - Invalid Task', 400
#
#     track_ids = []
#     playlist_ids = (db
#                     .collection('playlist_ids')
#                     .where('language', '==', language)
#                     .stream())
#     for playlist_id in playlist_ids:
#         id = playlist_id.value
#         playlists_tracks_endpoint = f'http://api.spotify.com/v1/playlists/{id}/tracks'
#         headers = {'Authorization': 'Bearer ' + access_token}
#         params = {
#             'fields': 'total,items(track(id))',
#             'offset': 0,
#         }
#         tracks_response = help.request_endpoint(
#             method='GET', endpoint=playlists_tracks_endpoint,
#             access_token=None, headers=headers, params=params)
#
#         if not tracks_response:
#             continue
#
#         tracks_json = tracks_response.json()
#
#         # Spotify limits to only 100 songs per request, so set starting
#         # location in playlist to +100 every loop to eventually get all songs
#         for _ in range((tracks_json['total'] // 100) + 1):
#             try:
#                 tracks_response = help.request_endpoint(
#                     'GET', playlists_tracks_endpoint, None, headers, params)
#                 tracks_json = tracks_response.json()
#                 for element in tracks_json['items']:
#                     track_ids_firestore = (db
#                                            .collection('track_ids')
#                                            .where(
#                                                 'value', '==',
#                                                 element['track']['id'])
#                                            .get())
#                     # check for repeats
#                     if (element['track']['id']
#                             and element['track']['id'] not in track_ids
#                             and not track_ids_firestore):
#                         trackid = models.TrackID(
#                             value=element['track']['id'],
#                             language=language)
#                         track_ids.append(trackid)
#                         db.collection('track_ids').add(trackid.to_dict())
#                 params['offset'] += 100
#             except KeyError:  # if no track id is found
#                 continue
#
#         # if len(track_ids) > 0:
#         #     ndb.put_multi(track_ids)
#
#
# @app.route('/create_tracks_from_audio_analysis', methods=['POST'])
# def create_tracks_from_audio_analysis():
#     # language, access_token
#     """Retrieves the track_ids from firestore, uses thoses to get the audio
#     analyses of the tracks, then stores that in firestore.
#     """
#     logging.debug('-----------MAKING TRACKS-----------')
#     if flask.request.headers.get('X-Appengine-Taskname') is None:
#         logging.error('Invalid Task: No X-Appengine-Taskname request header found')
#         return 'Bad Request - Invalid Task', 400
#
#     track_ids = (db
#                  .collection('track_ids')
#                  .where('language', '==', language)
#                  .stream())
#
#     for track_id in track_ids:
#         id = track_id.value
#         endpoint = f'http://api.spotify.com/v1/audio-features/{id}'
#         headers = {'Authorization': 'Bearer ' + access_token}
#         features_response = help.request_endpoint(
#             method='GET', endpoint=endpoint, access_token=None,
#             headers=headers)
#         features = features_response.json()
#         if features:
#             logging.debug('making track')
#             track = models.Track(
#                 track_id=id,
#                 language=language,
#                 loudness=features['loudness'],
#                 tempo=features['tempo'],
#                 danceability=features['danceability'],
#                 energy=features['energy'],
#                 acousticness=features['acousticness'],
#                 instrumentalness=features['instrumentalness'],
#                 liveness=features['liveness'],
#                 valence=features['valence'],
#                 mode=features['mode'],
#                 speechiness=features['speechiness'])
#             # tracks.append(track)
#             db.collection('tracks').add(track.to_dict())
#
#     logging.info('-----------DONE MAKING TRACKS-----------')
#
#
# @app.route('/find_url_in_comments', methods=['POST'])
# def find_url_in_comments():
#     # playlist_ids_local, playlist_ids_firestore, subreddit, language
#     """Finds links to Spotify playlists in the comment section of posts."""
#     logging.debug('-----------SCRAPING COMMENTS-----------')
#     if flask.request.headers.get('X-Appengine-Taskname') is None:
#         logging.error('Invalid Task: No X-Appengine-Taskname request '
#                       'header found')
#         return 'Bad Request - Invalid Task', 400
#
#     # try:
#     playlist_id_objects = []
#     subreddit = reddit.subreddit(const.subreddits[language])
#     for submission in subreddit.search('spotify'):
#         submission.comments.replace_more(limit=None)
#         comments = submission.comments.list()
#         for comment in comments:
#             new_start = 0
#             while True:  # loop over all comments
#                 if const.SPOTIFY_URL in comment.body[new_start:]:
#                     comment_body_find_playlist = comment.body.find(
#                         'playlist/', new_start)
#                     start = comment_body_find_playlist + 9
#                     end = comment_body_find_playlist + 31
#                     url = comment.body[start:end]
#                     if (url not in playlist_ids_local
#                             and url not in playlist_ids_firestore):
#                         playlist_ids_local.append(url)
#                         playlistid = models.PlaylistID(
#                             value=url, language=language)
#                         (db
#                          .collection('playlist_ids')
#                          .add(playlistid.to_dict()))
#                     new_start = end
#                 else:
#                     break
#         # time.sleep(2)
#
#     # except Exception as e:
#     #     logging.debug('ERROR ERROR! Code: {c}, Message: {m}'.format(
#     #         c=type(e).__name__, m=str(e)))
#
#
# def scan_subreddit(language, access_token):
#     """Scrapes specified subreddit for all Spotify links, and use that data to
#     get playlist ids, track ids, and audio analyses of each track.
#     """
#     logging.debug('-----------SCRAPING-----------')
#     reddit = praw.Reddit(
#         user_agent=const.USER_AGENT_REDDIT,
#         client_id=const.CLIENT_ID_REDDIT,
#         client_secret=const.CLIENT_SECRET_REDDIT,
#         disable_update_check=True)
#
#     subreddit = reddit.subreddit(const.subreddits[language])
#     playlist_ids_local = []
#     playlist_ids_firestore = []
#     filtered_playlist_ids = (db
#                              .collection('playlist_ids')
#                              .where('language', '==', language)
#                              .stream())
#     logging.debug(len(list(filtered_playlist_ids)))
#     for playlist_id in filtered_playlist_ids:
#         playlist_ids_firestore.append(playlist_id.value)
#
#     # find spotify playlist url in submission
#     for submission in subreddit.search('spotify'):
#         new_start = 0
#         while True:  # loop until all spotify links are found in submission
#             if const.SPOTIFY_URL in submission.selftext[new_start:]:
#                 submission_text_find_playlist = submission.selftext.find(
#                     'playlist/', new_start)
#                 start = submission_text_find_playlist + 9
#                 end = submission_text_find_playlist + 31
#                 url = submission.selftext[start:end]
#                 if (url not in playlist_ids_local
#                         and url not in playlist_ids_firestore):
#                     playlist_ids_local.append(url)
#                     playlistid = models.PlaylistID(
#                         value=url, language=language)
#                     db.collection('playlist_ids').add(playlistid.to_dict())
#                 new_start = end
#             else:
#                 break
#
#     # find spotify playlist url if submission is only a link
#     for submission in subreddit.search('spotify'):
#         if const.SPOTIFY_URL in submission.url:
#             submission_url_find_playlist = submission.url.find(
#                 'playlist/', new_start)
#             start = submission_url_find_playlist + 9
#             end = submission_url_find_playlist + 31
#             url = submission.url[start:end]
#             if (url not in playlist_ids_local
#                     and url not in playlist_ids_firestore):
#                 playlist_ids_local.append(url)
#                 playlistid = models.PlaylistID(value=url, language=language)
#                 # playlistid.put()
#                 db.collection('playlist_ids').add(playlistid.to_dict())
#
#     # schedule find_url_in_comments()
#     payload = {
#         'language': playlist_ids_local,
#         'access_token': playlist_ids_firestore,
#         'language': language,
#     }
#     payload_str = json.dumps(payload)
#     payload_encoded = base64.b64encode(payload_str.encode('utf-8'))
#     task = {
#         'app_engine_http_request': {
#             'http_method': 'POST',
#             'relative_uri': '/find_url_in_comments',
#             'body': payload_encoded,
#         }
#     }
#     response = client.create_task(parent, task)
#     logging.info('Created task {}'.format(response.name))
#
#     # schedule get_playlists_track_ids()
#     payload = {
#         'language': language,
#         'access_token': access_token,
#     }
#     payload_str = json.dumps(payload)
#     payload_encoded = base64.b64encode(payload_str.encode('utf-8'))
#     task = {
#         'app_engine_http_request': {  # Specify the type of request.
#             'http_method': 'POST',
#             'relative_uri': '/get_playlists_track_ids',
#             'body': payload_encoded,
#         }
#     }
#     response = client.create_task(parent, task)
#     logging.info('Created task {}'.format(response.name))
#
#     # schedule create_tracks_from_audio_analysis()
#     payload = {
#         'language': language,
#         'access_token': access_token,
#     }
#     payload_str = json.dumps(payload)
#     payload_encoded = base64.b64encode(payload_str.encode('utf-8'))
#     task = {
#         'app_engine_http_request': {  # Specify the type of request.
#             'http_method': 'POST',
#             'relative_uri': '/create_tracks_from_audio_analysis',
#             'body': payload_encoded,
#         }
#     }
#     response = client.create_task(parent, task)
#     logging.info('Created task {}'.format(response.name))
