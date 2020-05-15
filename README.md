
# Kabloombox

Kabloombox translates your music taste into a foreign language  to help you find your new favorite songs and artists.

Kabloombox uses user-generated content (scraped from language-learning subreddits) to recommend new foreign-language songs to you. The scraper looks for Spotify links in specific subreddits and stores all the songs' data from each of the playlists inside the database. Kabloombox then uses the song data to calculate a similar playlist for the user with similar traits (such as tempo, energy, danceability, etc).


## Requirements

Install the necessary libraries using this command:

    pip3 install -r requirements.txt

## Initialize Firestore

Instructions [here](https://cloud.google.com/firestore/docs/quickstart-servers#cloud-console).

## Create a Spotify developer project

Head to the [Spotify for Developers page](https://developer.spotify.com/dashboard) and create a new app. Note the `CLIENT ID` and `CLIENT SECRET`.


## Create a Reddit developer project

Head to your [Reddit apps page](https://www.reddit.com/prefs/apps) and create a new app. Note the `CLIENT ID`, `CLIENT_SECRET`, AND `USERS AGENT`.

The `praw` module requires a `praw.ini` file with your Reddit credentials. Create that file in the `kabloombox` folder and subsitute your information in:

    [DEFAULT]

    # Object to kind mappings
    comment_kind=t1
    message_kind=t4
    redditor_kind=t2
    submission_kind=t3
    subreddit_kind=t5

    # The URL prefix for OAuth-related requests.
    oauth_url=https://oauth.reddit.com

    # The URL prefix for regular requests.
    reddit_url=https://www.reddit.com

    # The URL prefix for short URLs.
    short_url=https://redd.it

    [bot]
    client_id=
    client_secret=
    username=
    password=
    user_agent=

## Create and initialize the AppEngine project
Go to the [Google Cloud console](https://console.cloud.google.com/home/dashboard) and create a new project

Make sure you have the [Google Cloud SDK](https://cloud.google.com/sdk/) installed.

Then in Terminal enter:

    gcloud init
    gcloud auth login
    gcloud config set project <PROJECT_ID>

Log in with your Google account and select the appropriate project from the list.


## Make a config file with all the secret keys

Create a `config.py` file in the `kabloombox` folder and insert all of your secret keys:

    CLIENT_ID_SPOTIFY =
    CLIENT_SECRET_SPOTIFY =

    CLIENT_ID_REDDIT =
    CLIENT_SECRET_REDDIT =
    USER_AGENT_REDDIT =

    FLASK_SESSIONS_KEY =

    AE_PROJECT_NAME =
    AE_QUEUE =
    AE_SERVER_LOCATION =




## Running the emulator

    python3 run.py

`CTRL-C` to exit.

By default, the app runs locally at `localhost:8080`.

Set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable.

    export GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/credentials-key.json


This script also allows you to run tests (it asks you at the beginning).


## Localhost logging

The project's logging level with Flask is **DEBUG**, so use this line for logging:

    logging.debug("logging text")

`print()` will not work.




## Useful links

- [See Firestore docs here](https://cloud.google.com/firestore/docs/manage-data/add-data)
- [See Flask docs here](https://flask.palletsprojects.com/en/1.1.x)
- [See Spotify Web API here](https://developer.spotify.com/documentation/web-api)
- [See Praw (Reddit API) doc here](https://praw.readthedocs.io/en/latest/)