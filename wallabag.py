import datetime
import json
from typing import Union, Optional

import pytz
import requests
from requests.exceptions import BaseHTTPError

from datetime_helpers import to_timestamp


class Wallabag:
    def __init__(self, host, username, password, client_id, client_secret, handle_access_token_refreshes=True):
        """Wallabag API interface

        :param host: wallabag instance url
        :param username: username
        :param password: password
        :param client_id: client id
        :param client_secret: client secret
        :param handle_access_token_refreshes:
        """
        self._host = host
        self._username = username
        self._password = password
        self._client_id = client_id
        self._client_secret = client_secret

        self._tzinfo: pytz.BaseTzInfo = pytz.utc

        self._access_token = None
        self._refresh_token = None
        self._access_token_expires_at = datetime.datetime.utcnow()  # trigger token refresh at the first request

        self._requests_session = requests.Session()

        self.auto_access_token_refresh = handle_access_token_refreshes
        if self.auto_access_token_refresh:
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

        if not skip_access_token_refresh and self.auto_access_token_refresh and datetime.datetime.utcnow() >= self._access_token_expires_at:
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

    def _build_entry_payload(
        self,
        title: Union[None, str] = None,
        tags: Union[None, list] = None,
        archive: Union[None, bool] = None,
        starred: Union[None, bool] = None,
        content: Union[None, str] = None,
        language: Union[None, str] = None,
        preview_picture: [None, str] = None,
        published_at: Union[int, datetime.datetime] = None,
        authors: Union[None, list] = None,
        public: Union[None, bool] = None,
        origin_url: Union[None, str] = None
    ):
        if content is not None and title is None:
            raise ValueError("if `content` is provided, `title` must be non-empty")

        if tags:
            tags = ",".join(tags)
        if authors:
            authors = ",".join(authors)
        if published_at is not None:
            if isinstance(published_at, datetime.datetime):
                published_at = to_timestamp(
                    published_at, tzinfo=self._tzinfo if self._tzinfo else None
                )

        payload = dict(
            title=title,
            tags=tags,
            archive=int(archive) if archive is not None else None,
            starred=int(starred) if starred is not None else None,
            content=content,
            language=language,
            preview_picture=preview_picture,
            published_at=published_at,
            authors=authors,
            public=int(public) if public is not None else None,
            origin_url=origin_url
        )

        return payload

    def save_entry(
        self,
        url: str,
        title: Union[None, str] = None,
        tags: Union[None, list] = None,
        archive: Union[None, bool] = None,
        starred: Union[None, bool] = None,
        content: Union[None, str] = None,
        language: Union[None, str] = None,
        preview_picture: [None, str] = None,
        published_at: Union[None, int, datetime.datetime] = None,
        authors: Union[None, list] = None,
        public: Union[None, bool] = None,
        origin_url: Union[None, str] = None
    ):
        path = "/api/entries.json"

        payload = self._build_entry_payload(title, tags, archive, starred, content, language, preview_picture,
                                            published_at, authors, public, origin_url)

        payload["url"] = url

        response_dict = self.query(path, "post", payload=payload)

        return response_dict

    def edit_entry(
        self,
        entry_id: int,
        title: Union[None, str] = None,
        tags: Union[None, list] = None,
        archive: Union[None, bool] = None,
        starred: Union[None, bool] = None,
        content: Union[None, str] = None,
        language: Union[None, str] = None,
        preview_picture: [None, str] = None,
        published_at: Union[int, datetime.datetime] = None,
        authors: Union[None, list] = None,
        public: Union[None, bool] = None,
        origin_url: Union[None, str] = None
    ):
        path = f"/api/entries/{entry_id}.json"

        payload = self._build_entry_payload(title, tags, archive, starred, content, language, preview_picture,
                                            published_at, authors, public, origin_url)

        response_dict = self.query(path, "patch", payload=payload)

        return response_dict


