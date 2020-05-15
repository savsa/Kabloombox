from . import config

# Spotify URLs
SPOTIFY_AUTH_URL = 'https://accounts.spotify.com/authorize'
SPOTIFY_TOKEN_URL = 'https://accounts.spotify.com/api/token'
SPOTIFY_API_BASE_URL = 'https://api.spotify.com'
SPOTIFY_URL = 'open.spotify.com/user/'

REDIRECT_URI = 'http://localhost:8080/redirect'

SCOPE = ('user-library-read user-read-private user-read-email '
         'playlist-read-private user-modify-playback-state '
         'playlist-modify-public playlist-modify-private ')

# Client Keys
CLIENT_ID_SPOTIFY = config.CLIENT_ID_SPOTIFY
CLIENT_SECRET_SPOTIFY = config.CLIENT_SECRET_SPOTIFY

CLIENT_ID_REDDIT = config.CLIENT_ID_REDDIT
CLIENT_SECRET_REDDIT = config.CLIENT_SECRET_REDDIT
USER_AGENT_REDDIT = config.USER_AGENT_REDDIT

AE_PROJECT_NAME = config.AE_PROJECT_NAME
AE_QUEUE = config.AE_QUEUE
AE_SERVER_LOCATION = config.AE_SERVER_LOCATION

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
