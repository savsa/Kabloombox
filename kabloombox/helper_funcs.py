import requests

import auth

def request_endpoint(endpoint, session, headers, params={}):
    """Make GET request to the endpoint. Check for expired access_token."""
    response = requests.get(endpoint, headers=headers, params=params)
    print('status code: ', response.status_code)

    if response.status_code == 401 and session:
        # unauthorized. try getting another access token
        print('inside')
        refresh_token = session.get('refresh_token')
        new_access_token = auth.get_access_from_refresh_token(refresh_token)
        if not new_access_token:
            return None
        print(new_access_token, refresh_token)
        headers = { 'Authorization' : 'Bearer ' + new_access_token }
        response = requests.get(endpoint, headers=headers, params=params)
        print(response.content)
        if response:
            session['access_token'] = new_access_token
        else:
            print('GETTING NEW ACCESS TOKEN DIDN\'T WORK')
            return response
    return response

def is_auth_error(res_json):
    try:
        if 'error' in res_json:
            return res_json['error']['status'] == 401
        return False
    except KeyError:
        return True
    except TypeError:
        return True

def is_client_error(res_json):
    try:
        return res_json['error']['status'] != requests.codes.ok
    except KeyError:
        return False
    except TypeError:
        return False
