import datetime
import json

import requests
from requests.exceptions import BaseHTTPError


class Wallabag:
    def __init__(self, host, username, password, client_id, client_secret, get_access_token=False):
        """Wallabag API interface

        :param host: wallabag instance url
        :param username: username
        :param password: password
        :param client_id: client id
        :param client_secret: client secret
        :param get_access_token: if True, the client access token will be fetched when the istance is initialized.
        Otherwise, it will be fecthed when the first request is fired
        """
        self._host = host
        self._username = username
        self._password = password
        self._client_id = client_id
        self._client_secret = client_secret

        self._access_token = None
        self._refresh_token = None
        self._access_token_expires_at = datetime.datetime.utcnow()  # trigger token refresh at the first request

        self._requests_session = requests.Session()

        if get_access_token:
            self._refresh_access_token()

    def query(self, path, method, payload=None, skip_access_token_refresh=False):
        method = method.lower()
        if not path.startswith("/"):
            path = f"/{path}"

        url = f"{self._host}{path}"
        payload = payload or {}

        # only set Bearer header if we have an access token
        # no need to do this because the "Authorization" header is set at session level
        # headers = {'Authorization': 'Bearer ' + self._access_token} if self._access_token else {}
        headers = {}

        if not skip_access_token_refresh and datetime.datetime.utcnow() > self._access_token_expires_at:
            self._refresh_access_token()

        if method == "get":
            response = self._requests_session.get(url, params=payload, headers=headers)
        elif method == "post":
            response = self._requests_session.post(url, data=payload, headers=headers)
        elif method == "patch":
            response = self._requests_session.patch(url, data=payload, headers=headers)
        elif method == "delete":
            response = self._requests_session.delete(url, params=payload, headers=headers)
        elif method == "put":
            response = self._requests_session.put(url, data=payload, headers=headers)
        else:
            raise ValueError(f"unknown http method \"{method}\"")

        if response.status_code != 200:
            print(response.json())
        else:
            response_dict = response.json()
            return response_dict

    def _refresh_access_token(self):
        path = "/oauth/v2/token"

        payload = dict(
            grant_type="password",
            username=self._username,
            password=self._password,
            client_id=self._client_id,
            client_secret=self._client_secret
        )

        response_dict = self.query(path, "post", payload=payload, skip_access_token_refresh=True)

        self._access_token = response_dict["access_token"]
        self._refresh_token = response_dict["refresh_token"]

        # these headers are kept for the whole session's life
        # sending a request with a new "headers" dict will add the keys to "Authorization"
        self._requests_session.headers.update({"Authorization": "Bearer " + self._access_token})

        self._access_token_expires_at = datetime.datetime.utcnow() + datetime.timedelta(0, response_dict["expires_in"])

    def get_entries(self):
        path = "/api/entries.json"

        payload = dict(
            page=1,
            perPage=1,
            order="asc"
        )

        response_dict = self.query(path, "get", payload=payload)

        # print(response_dict["_embedded"]["items"][0])
        print(json.dumps(response_dict["_embedded"]["items"][0], indent=2))

    def save_enrty(self, url: str, tags: [None, list] = None):
        path = "/api/entries.json"

        if tags:
            tags = ",".join(tags)

        payload = dict(
            url=url,
            tags=tags
        )

        response_dict = self.query(path, "post", payload=payload)

        return response_dict


