import jinja2
import os
import webapp2
from base_handler import BaseHandler
from webapp2_extras import sessions

import auth
import const
import helper_funcs as help
import interactions as actions
import scrape

env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), '..')),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

class HomeAndLoginPage(BaseHandler):
    def get(self):
        try:
            code = self.session['code']
        except KeyError:
            code = ''

        template_vars = {}

        access_token = self.session.get('access_token')
        refresh_token = self.session.get('refresh_token')
        if access_token:
            # user is already logged in and has an access token
            profile_json = actions.get_account_info(access_token, self.session)
            if help.is_auth_error(profile_json):
                self.session.clear()
                self.redirect('/')
            elif help.is_client_error(profile_json):
                self.redirect('/error')

            playlists_json = actions.get_users_playlists(access_token, self.session)
            if help.is_auth_error(playlists_json):
                self.session.clear()
                self.redirect('/')
            elif help.is_client_error(playlists_json):
                self.redirect('/error')

            template_vars['profile_photo'] = actions.get_profile_photo_url(profile_json)
            template_vars['profile_name'] = actions.get_profile_name(profile_json)
            template_vars['playlists_json'] = playlists_json
            template_vars['access_token'] = access_token
        elif code:
            # user isn't logged in yet. get the neccessary tokens and store
            # them in the session
            token = auth.get_token(code)
            if token:
                access_token = token.access_token
                refresh_token = token.refresh_token
                self.session['access_token'] = access_token
                self.session['refresh_token'] = refresh_token

                profile_json = actions.get_account_info(access_token, self.session)
                if help.is_auth_error(profile_json):
                    self.session.clear()
                    self.redirect('/')
                elif help.is_client_error(profile_json):
                    self.redirect('/error')

                playlists_json = actions.get_users_playlists(access_token, self.session)
                if help.is_auth_error(playlists_json):
                    self.session.clear()
                    self.redirect('/')
                elif help.is_client_error(playlists_json):
                    self.redirect('/error')

                template_vars['profile_photo'] = actions.get_profile_photo_url(profile_json)
                template_vars['profile_name'] = actions.get_profile_name(profile_json)
                template_vars['playlists_json'] = playlists_json
                template_vars['access_token'] = token.access_token
            else:
                print('COULDN\'T GET ACCESS TOKEN FROM CODE')
                self.session.clear()
                self.redirect('/error')

        template = env.get_template('templates/homeAndLoginPage.html')
        self.response.write(template.render(template_vars))

class Playlist(webapp2.RequestHandler):
    def get(self):
        template = env.get_template('templates/playlist.html')
        self.response.write(template.render())

class About(webapp2.RequestHandler):
    def get(self):
        template = env.get_template('templates/about.html')
        self.response.write(template.render())

class Error(webapp2.RequestHandler):
    def get(self):
        template = env.get_template('templates/error.html')
        self.response.write(template.render())

###################

class Login(webapp2.RequestHandler):
    def get(self):
        url = '{}?client_id={}' \
                '&response_type=code' \
                '&redirect_uri={}' \
                '&scope={}'.format(const.SPOTIFY_AUTH_URL, const.CLIENT_ID_SPOTIFY, const.REDIRECT_URI, const.SCOPE)
        self.redirect(url)

class Scrape(BaseHandler):
    def get(self):
        template = env.get_template('templates/search.html')
        self.response.write(template.render())

    def post(self):
        language = self.request.get('language')
        code = self.session['code']
        if code:
            token = auth.get_token(code)
            print('TOKEN:', token)
            assert token
            if token:
                self.session['access_token'] = token.access_token
                self.session['refresh_token'] = token.refresh_token
                scrape.scan_subreddit(language, token.access_token)

class Redirect(BaseHandler):
    """Gets the code after getting redirected from the Spotify login page"""
    def get(self):
        code = self.request.get('code')
        if not code:
            print('----COULD NOT GET CODE----')
            self.redirect('/error')
        self.session['code'] = code
        self.redirect('/')
        # self.redirect('/scrape')