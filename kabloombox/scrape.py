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
from . import app, db


# @app.route('/get_playlists_track_ids', methods=['POST'])
def get_playlists_track_ids(language, access_token):
    # language, access_token
    """Using the playlist ids, get all of their tracks and track ids."""
    logging.debug("-----------GETTING TRACK IDS-----------")
    track_ids = list(
        db.collection("track_ids").where("language", "==", language).stream()
    )
    playlist_ids = (
        db.collection("playlist_ids").where("language", "==", language).stream()
    )
    headers = {"Authorization": "Bearer " + access_token}
    params = {
        "fields": "total,items(track(id))",
        "offset": 0,
    }

    for playlist_id in playlist_ids:
        logging.debug("2")
        id = playlist_id.get("value")
        logging.debug(id)
        playlists_tracks_endpoint = f"http://api.spotify.com/v1/playlists/{id}/tracks"
        tracks_response, _ = help.request_endpoint(
            method="GET",
            endpoint=playlists_tracks_endpoint,
            access_token=None,
            headers=headers,
            params=params,
        )

        if not tracks_response:
            logging.debug(tracks_response.json())
            continue

        tracks_json = tracks_response.json()

        # Spotify limits to only 100 songs per request, so set starting
        # location in playlist to +100 every loop to eventually get all songs
        logging.debug("A")
        num_tracks = tracks_json["total"]
        for _ in range(math.ceil(num_tracks / 100)):
            logging.debug("B")
            try:
                tracks_response, _ = help.request_endpoint(
                    method="GET",
                    endpoint=playlists_tracks_endpoint,
                    access_token=None,
                    headers=headers,
                    params=params,
                )
                if not tracks_response:
                    logging.debug("ERROR")
                    continue
                tracks_json = tracks_response.json()
                for element in tracks_json["items"]:
                    # check for repeats
                    if (
                        element["track"]["id"]
                        and element["track"]["id"] not in track_ids
                    ):
                        logging.debug("B")
                        trackid = models.TrackID(
                            value=element["track"]["id"], language=language
                        )
                        track_ids.append(trackid)
                        db.collection("track_ids").add(trackid.to_dict())
                        logging.debug("MADE TRACK_ID")
                params["offset"] += 100
            except KeyError:  # if no track id is found
                continue


# @app.route('/create_tracks_from_audio_analysis', methods=['POST'])
def create_tracks_from_audio_analysis(language, access_token):
    """Retrieves the track_ids from firestore, uses thoses to get the audio
    analyses of the tracks, then stores that in firestore.
    """
    logging.debug("-----------MAKING TRACKS-----------")

    track_ids = db.collection("track_ids").where("language", "==", language).stream()

    ids = []
    for track_id in track_ids:
        endpoint = f"http://api.spotify.com/v1/audio-features/{id}"
        headers = {"Authorization": "Bearer " + access_token}
        features_response, _ = help.request_endpoint(
            method="GET", endpoint=endpoint, access_token=None, headers=headers
        )
        if not features_response:
            continue
        ids.append(track_id)
        features = features_response.json()
        logging.debug("making track")
        track = models.Track(
            track_id=track_id.get("value"),
            language=language,
            loudness=features["loudness"],
            tempo=features["tempo"],
            danceability=features["danceability"],
            energy=features["energy"],
            acousticness=features["acousticness"],
            instrumentalness=features["instrumentalness"],
            liveness=features["liveness"],
            valence=features["valence"],
            mode=features["mode"],
            speechiness=features["speechiness"],
        )
        db.collection("tracks").add(track.to_dict())
        logging.debug("MADE TRACK")
    logging.debug(ids)

    track_model = db.collection("tracks").stream()
    arr = []
    arr = [t.to_dict() for t in track_model]
    logging.debug(arr)
    # for t in track_model:
    # logging.debug(t.to_dict())

    logging.info("-----------DONE MAKING TRACKS-----------")


# @app.route('/find_url_in_comments', methods=['POST'])
def find_url_in_comments(new_playlist_ids, playlist_ids, subreddit, language):
    """Finds links to Spotify playlists in the comment section of posts."""
    logging.debug("-----------SCRAPING COMMENTS-----------")

    # try:
    for submission in subreddit.search("spotify"):
        submission.comments.replace_more(limit=None)
        comments = submission.comments.list()
        for comment in comments:
            new_start = 0
            while const.SPOTIFY_URL in comment.body[new_start:]:
                comment_body_find_playlist = comment.body.find("playlist/", new_start)
                start = comment_body_find_playlist + 9
                end = comment_body_find_playlist + 31
                url = comment.body[start:end]
                if url not in new_playlist_ids and url not in playlist_ids:
                    new_playlist_ids.append(url)
                    playlistid = models.PlaylistID(value=url, language=language)
                    db.collection("playlist_ids").add(playlistid.to_dict())
                    logging.debug("MADE PLAYLIST ID")
                new_start = end


def scan_subreddit(language, access_token):
    """Scrapes specified subreddit for all Spotify links, and use that data to
    get playlist ids, track ids, and audio analyses of each track.
    """
    logging.debug("-----------SCRAPING-----------")
    reddit = praw.Reddit(
        user_agent=const.USER_AGENT_REDDIT,
        client_id=const.CLIENT_ID_REDDIT,
        client_secret=const.CLIENT_SECRET_REDDIT,
        disable_update_check=True,
    )

    subreddit = reddit.subreddit(const.subreddits[language])
    new_playlist_ids = []
    playlist_ids = list(
        db.collection("playlist_ids").where("language", "==", language).stream()
    )
    logging.debug(len(playlist_ids))

    # find spotify playlist url in submission
    for submission in subreddit.search("spotify"):
        new_start = 0
        while True:  # loop until all spotify links are found in submission
            if const.SPOTIFY_URL not in submission.selftext[new_start:]:
                break
            submission_text_find_playlist = submission.selftext.find(
                "playlist/", new_start
            )
            start = submission_text_find_playlist + 9
            end = submission_text_find_playlist + 31
            url = submission.selftext[start:end]
            if url not in new_playlist_ids and url not in playlist_ids:
                new_playlist_ids.append(url)
                playlistid = models.PlaylistID(value=url, language=language)
                db.collection("playlist_ids").add(playlistid.to_dict())
                logging.debug("MADE PLAYLIST_ID")
            new_start = end

    # find spotify playlist url if submission is only a link
    for submission in subreddit.search("spotify"):
        if const.SPOTIFY_URL in submission.url:
            submission_url_find_playlist = submission.url.find("playlist/", new_start)
            start = submission_url_find_playlist + 9
            end = submission_url_find_playlist + 31
            url = submission.url[start:end]
            if url not in new_playlist_ids and url not in playlist_ids:
                new_playlist_ids.append(url)
                playlistid = models.PlaylistID(value=url, language=language)
                db.collection("playlist_ids").add(playlistid.to_dict())
                logging.debug("MADE PLAYLIST_ID")

    find_url_in_comments(new_playlist_ids, playlist_ids, subreddit, language)
    # return
    get_playlists_track_ids(language, access_token)
    create_tracks_from_audio_analysis(language, access_token)


def scan_subreddit_debug():
    logging.debug("scanning debug")
    with open("tracks.txt") as f:
        data = json.load(f)

    for features in data["tracks"]:
        track = models.Track(
            track_id=features["track_id"],
            language="german",
            loudness=features["loudness"],
            tempo=features["tempo"],
            danceability=features["danceability"],
            energy=features["energy"],
            acousticness=features["acousticness"],
            instrumentalness=features["instrumentalness"],
            liveness=features["liveness"],
            valence=features["valence"],
            mode=features["mode"],
            speechiness=features["speechiness"],
        )
        db.collection("tracks").add(track.to_dict())
        logging.debug("MADE TRACK")
