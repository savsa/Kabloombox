import requests
import json
import logging

from . import auth


def request_endpoint(
    method,
    endpoint,
    headers,
    access_token,
    refresh_token=None,
    params=None,
    json_params=None,
):
    """Make a GET or POST request to the endpoint. Check for expired access
    token and refresh it if neccessary. The default method is GET.
    """
    if method == "POST":
        response = requests.post(
            endpoint, headers=headers, params=params, json=json_params
        )
    else:
        response = requests.get(
            endpoint, headers=headers, params=params, json=json_params
        )

    if response.status_code == 401 and refresh_token:
        new_access_token = auth.get_access_from_refresh_token(refresh_token)
        if not new_access_token:
            return None
        print(new_access_token, refresh_token)
        headers = {"Authorization": "Bearer " + new_access_token}
        response = requests.get(
            endpoint, headers=headers, params=params, json=json_params
        )
        if not response:
            logging.error("Could not get new access token")
        access_token = new_access_token
    return response, access_token


def is_auth_error(res_json):
    try:
        if "error" in res_json:
            return res_json["error"]["status"] == 401
        return False
    except KeyError:
        return True
    except TypeError:
        return True


def is_client_error(res_json):
    try:
        status_code = res_json["error"]["status"]
        return status_code != 200 and status_code != 201
    except KeyError:
        return False
    except TypeError:
        return False


def check_error(res_json, response):
    if is_auth_error(res_json):
        response.status_int = 401
        json_error = json.dumps({"error": "Insufficient authentication."})
        response.write(json_error)
        return True
    elif is_client_error(res_json):
        response.status_int = 404
        json_error = json.dumps({"error": "Not found."})
        response.write(json_error)
        return True
    return False
