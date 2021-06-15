import datetime
import json

import requests
from requests.exceptions import BaseHTTPError


class Wallabag:
    BASE_URL = "https://app.wallabag.it"

    def __init__(self, host, username, password, client_id, client_secret):
        self._host = host
        self._username = username
        self._password = password
        self._client_id = client_id
        self._client_secret = client_secret

        self._access_token = None
        self._refresh_token = None
        self._access_token_expires_at = None

        self._requests_session = requests.Session()

    def query(self, path, method="get", payload=None, skip_access_token_refresh=False):
        method = method.lower()
        if not path.startswith("/"):
            path = f"/{path}"

        url = f"{self._host}{path}"
        payload = payload or {}

        # only set Bearer header if we have an access token
        headers = {'Authorization': 'Bearer ' + self._access_token} if self._access_token else {}

        if not skip_access_token_refresh and datetime.datetime.utcnow() > self._access_token_expires_at:
            self.refresh_token()

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

    def refresh_token(self):
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

