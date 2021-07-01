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

    def get_entries(
            self,
            archive:  bool = None,
            starred: bool = None,
            sort: str = None,
            order: str = None,
            page: int = 1,
            per_page: int = 30,
            tags: Union[list, tuple] = None,
            since: Union[int, datetime.datetime] = None,
            public: bool = None,
            detail: str = "metadata",  # we force it to "metadata" because the API default is "full" but just for backward compatibility
    ):
        path = "/api/entries.json"

        if order and order not in ("asc", "desc"):
            raise ValueError("'order' must be either 'asc' or 'desc'")
        if sort and sort not in ("created", "updated", "archived"):
            raise ValueError("'sort' must be either 'created', 'updated' or 'archived'")
        if detail and detail not in ("metadata", "full"):
            raise ValueError("'detail' must be either 'metadata' or 'full'")

        payload = dict(
            archive=archive,
            starred=starred,
            sort=sort,
            order=order,
            page=page,
            perPage=per_page,
            tags=None if not tags else ",".join(tags),
            since=since,
            public=public,
            detail=detail
        )

        response_dict = self.query(path, "get", payload=payload)

        return [Entry.from_dict(i, wallabag_instance=self) for i in response_dict["_embedded"]["items"]]

    def _build_entry_payload(
        self,
        title: Union[None, str] = None,
        tags: list = None,
        archive: bool = None,
        starred: bool = None,
        content: str = None,
        language: str = None,
        preview_picture: str = None,
        published_at: Union[int, datetime.datetime] = None,
        authors: list = None,
        public: bool = None,
        origin_url: str = None
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

    def get_entry(self, entry_id: int):
        path = f"/api/entries/{entry_id}.json"

        response_dict = self.query(path, "get")

        return Entry.from_dict(response_dict, wallabag_instance=self)

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

        return Entry.from_dict(response_dict, wallabag_instance=self)

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


class Entry:
    __slots__ = [
        "_wb",
        "entry_id",
        "url",
        "title",
        "tags",
        "is_archived",
        "is_starred",
        "content",
        "language",
        "preview_picture",
        "published_at",
        "published_by",
        "is_public",
        "origin_url",
        "annotations",
        "created_at",
        "archived_at",
        "starred_at",
        "updated_at",
        "domain_name",
        "given_url",
        "hashed_given_url",
        "hashed_url",
        "reading_time"
    ]

    PORPERTIES_TO_STRIP = [
        "uid",
        "user_id",
        "user_email",
        "user_name",
        "headers",
        "http_status",
        "mimetype",
        "_links"
    ]

    def __init__(
            self,
            wallabag_instance: Wallabag,
            entry_id: int,
            url: str,
            title: Union[None, str] = None,
            tags: Union[None, str, list] = None,
            is_archived: Union[None, bool] = None,
            is_starred: Union[None, bool] = None,
            content: Union[None, str] = None,
            language: Union[None, str] = None,
            preview_picture: [None, str] = None,
            published_at: Union[None, int, datetime.datetime] = None,
            published_by: Union[None, str, list] = None,
            is_public: Union[None, bool] = None,
            origin_url: Union[None, str] = None,
            annotations: Union[None, list] = None,
            created_at: Union[None, int, datetime.datetime] = None,
            archived_at: Union[None, int, datetime.datetime] = None,
            starred_at: Union[None, int, datetime.datetime] = None,
            updated_at: Union[None, int, datetime.datetime] = None,
            domain_name: Union[None, str] = None,
            given_url: Union[None, str] = None,
            hashed_given_url: Union[None, str] = None,
            hashed_url: Union[None, str] = None,
            reading_time: Union[None, int] = None
    ):
        self._wb = wallabag_instance
        self.entry_id = entry_id
        self.url = url
        self.title = title
        self.tags = self.handle_list(tags, split_on_commas=True)
        self.is_archived = self.handle_bool(is_archived)
        self.is_starred = self.handle_bool(is_starred)
        self.content = content
        self.language = language
        self.preview_picture = preview_picture
        self.published_at = self.handle_date(published_at, tzinfo=self._wb._tzinfo)
        self.published_by = self.handle_list(published_by)
        self.is_public = self.handle_bool(is_public)
        self.origin_url = origin_url
        self.annotations = annotations
        self.created_at = self.handle_date(created_at, tzinfo=self._wb._tzinfo)
        self.archived_at = self.handle_date(archived_at, tzinfo=self._wb._tzinfo)
        self.starred_at = self.handle_date(starred_at, tzinfo=self._wb._tzinfo)
        self.updated_at = self.handle_date(updated_at, tzinfo=self._wb._tzinfo)
        self.domain_name = domain_name
        self.given_url = given_url
        self.hashed_given_url = hashed_given_url
        self.hashed_url = hashed_url
        self.reading_time = reading_time

        if isinstance(self.tags, str):
            if "," in self.tags:
                self.tags = self.tags.split(",")
            else:
                self.tags = [self.tags]

        if isinstance(self.published_by, str):
            if "," in self.published_by:
                self.published_by = self.published_by.split(",")
            else:
                self.published_by = [self.published_by]

    @classmethod
    def from_dict(cls, entry_dict: dict, wallabag_instance: Wallabag):
        entry_dict["entry_id"] = entry_dict.pop("id")

        for k in cls.PORPERTIES_TO_STRIP:
            entry_dict.pop(k, None)

        return cls(**entry_dict, wallabag_instance=wallabag_instance)

    @property
    def entry_url(self):
        return f"{self._wb._host}/view/{self.entry_id}"

    def as_dict(self):
        return {k: getattr(self, k) for k in self.__slots__}

    @staticmethod
    def handle_list(input_list, split_on_commas=False):
        if input_list is not None:
            if isinstance(input_list, str):
                if split_on_commas and "," in input_list:
                    return input_list.split(",")
                else:
                    return [input_list]
            else:
                # remove none values such as ""
                return [i for i in input_list if i]

    @staticmethod
    def handle_date(input_date, tzinfo):
        if input_date is not None:
            if isinstance(input_date, datetime.datetime):
                return to_timestamp(input_date, tzinfo=tzinfo)

    @staticmethod
    def handle_bool(input_bool):
        if input_bool is not None:
            if isinstance(input_bool, bool):
                return input_bool
            else:
                return bool(input_bool)

    def __str__(self):
        return f"Entry<{self.entry_id}>"

    def pprint(self):
        for key in self.__slots__:
            print(f"<Entry>.{key}: {getattr(self, key)}")

    def update_remote(self):
        result_dict = self._wb.edit_entry(
            self.entry_id,
            title=self.title,
            tags=self.tags,
            archive=self.is_archived,
            starred=self.is_starred,
            content=self.content,
            language=self.language,
            preview_picture=self.preview_picture,
            published_at=self.published_at,
            authors=self.published_by,
            public=self.is_public,
            origin_url=self.origin_url
        )

        return self.from_dict(result_dict, wallabag_instance=self._wb)

    def refresh(self):
        remote_entry = self._wb.get_entry(self.entry_id)
        for k in self.__slots__:
            if k.startswith("_"):
                continue

            if getattr(self, k) != getattr(remote_entry, k):
                setattr(self, k, getattr(remote_entry, k))
