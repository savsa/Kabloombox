import requests_toolbelt.adapters.appengine as appengine
import webapp2

import kabloombox.api as api
import kabloombox.config as config
import kabloombox.views as views


appengine.monkeypatch()

config_sessions = {}
config_sessions['webapp2_extras.sessions'] = {
    'secret_key': config.SESSIONS_KEY,
}

app = webapp2.WSGIApplication([
    ### Frontend
    ('/', views.HomeAndLoginPage),
    ('/playlist', views.Playlist),
    ('/about', views.About),
    ('/error', views.Error),
    ### Backend
    ('/login', views.Login),
    ('/redirect', views.Redirect),
    ('/scrape', views.Scrape),
    ### POST requests
    ('/start-analysis', api.StartAnalysis),
    ('/logout', api.Logout),
    ('/play', api.Play),
], debug=True, config=config_sessions)