import requests
from webapp2_extras import sessions

import auth

def request_endpoint(endpoint, session, headers, params={}):
    """Make GET request to the endpoint. Check for expired access_token."""
    response = requests.get(endpoint, headers=headers, params=params)
    if response.status_code == 401 and session:
        refresh_token = session.get('refresh_token')
        new_access_token = auth.get_access_from_refresh_token(refresh_token)
        headers = { 'Authorization' : 'Bearer ' + new_access_token }
        response = requests.get(endpoint, headers=headers, params=params)
        print(response.json())
        if response:
            session['access_token'] = new_access_token
        else:
            raise Exception('GETTING NEW ACCESS TOKEN DIDN\'T WORK')
    elif not response and session:
        # failed in some other way that wasn't an expired token
        sessions.clear()
    return response