#== objects.py ==#
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .http import http

from datetime import datetime
import io
import os
from contextlib import nullcontext

__all__ = (
    'APIObject',
    'dt_formatter',
    'repr_dt',
    'PartialUser',
    'User',
    'Repository',
    'Issue',
    'File',
    'Gist',
    'Organization',
)

def dt_formatter(time_str: str) -> datetime:
    if time_str is not None:
        return datetime.strptime(time_str, r"%Y-%m-%dT%H:%M:%SZ")
    return None

def repr_dt(_datetime: datetime) -> str:
    return _datetime.strftime(r'%d-%m-%Y, %H:%M:%S')

class APIObject:
    __slots__ = (
        '_response',
        '_http'
    )

    def __init__(self, response: dict[str, str | int | dict[str, str | int]], _http: http) -> None:
        self._http = _http
        self._response = response

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}>'


#=== User stuff ===#

class _BaseUser(APIObject):
    __slots__ = (
        'login',
        'id',
        )
    def __init__(self, response: dict, _http: http) -> None:
        super().__init__(response, _http)
        self._http = _http
        self.login = response.get('login')
        self.id = response.get('id')

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}; id = {self.id}, login = {self.login!r}>'

    async def repos(self) -> list[Repository]:
        results = await self._http.get_user_repos(self)
        return [Repository(data, self._http) for data in results]

    async def gists(self) -> list[Gist]:
        results = await self._http.get_user_gists(self)
        return [Gist(data, self._http) for data in results]

    async def orgs(self) -> list[Organization]:
        results = await self._http.get_user_orgs(self)
        return [Organization(data, self._http) for data in results]


class User(_BaseUser): 
    __slots__ = (
        'login',
        'id',
        'avatar_url',
        'html_url',
        'public_repos',
        'public_gists',
        'followers',
        'following',
        'created_at',
        )
    def __init__(self, response: dict, _http: http) -> None:
        super().__init__(response, _http)
        tmp = self.__slots__ + _BaseUser.__slots__
        keys = {key: value for key,value in self._response.items() if key in tmp}
        for key, value in keys.items():
            if '_at' in key and value is not None:
                setattr(self, key, dt_formatter(value))
                continue
            else:
                setattr(self, key, value)
                continue

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}; login: {self.login!r}, id: {self.id}, created_at: {self.created_at}>'


class PartialUser(_BaseUser):
    __slots__ = (
        'site_admin',
        'html_url',
        'avatar_url',
        ) + _BaseUser.__slots__

    def __init__(self, response: dict, _http: http) -> None:
        super().__init__(response, _http)
        self.site_admin = response.get('site_admin')
        self.html_url = response.get('html_url')
        self.avatar_url = response.get('avatar_url')

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}; login: {self.login!r}, id: {self.id}, site_admin: {self.site_admin}, html_url: {self.html_url}>'

    async def _get_user(self) -> User:
        """Upgrades the PartialUser to a User object.""" 
        response = await self._http.get_user(self.login)
        return User(response, self._http)


#=== Repository stuff ===#

class Repository(APIObject):
    __slots__ = (
        'id',
        'name',
        'owner',
        'size'
        'created_at',
        'url',
        'html_url',
        'archived',
        'disabled',
        'updated_at',
        'open_issues_count',
        'default_branch',
        'clone_url',
        'stargazers_count',
        'watchers_count',
        'forks',
        'license',
        )
    def __init__(self, response: dict, _http: http) -> None:
        super().__init__(response, _http)
        tmp = self.__slots__ + APIObject.__slots__
        keys = {key: value for key,value in self._response.items() if key in tmp}
        for key, value in keys.items():
            if key == 'owner':
                setattr(self, key, PartialUser(value, self._http))
                continue

            if key == 'name':
                setattr(self, key, value)
                continue

            if '_at' in key and value is not None:
                setattr(self, key, dt_formatter(value))
                continue

            if 'license' in key:
                if value is None:
                    setattr(self, key,None)
                setattr(self, key, value['name'])
                continue

            else:
                setattr(self, key, value)
                continue

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}; id: {self.id}, name: {self.name!r}, owner: {self.owner!r}>'

class Issue(APIObject):
    __slots__ = (
        'id',
        'title',
        'user',
        'labels',
        'state',
        'created_at',
        'closed_by',
    )

    def __init__(self, response: dict, _http: http) -> None:
        super().__init__(response, _http)
        tmp = self.__slots__ + APIObject.__slots__
        keys = {key: value for key,value in self._response.items() if key in tmp}
        for key, value in keys.items():
            if key == 'user':
                setattr(self, key, PartialUser(value, self._http))
                continue

            if key == 'labels':
                setattr(self, key, [label['name'] for label in value])
                continue

            if key == 'closed_by':
                setattr(self, key, User(value, self._http))
                continue

            else:
                setattr(self, key, value)
                continue

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}; id: {self.id}, title: {self.title}, user: {self.user}, created_at: {self.created_at}, state: {self.state}>'


#=== Gist stuff ===#

class File:
    def __init__(self, fp: str | io.StringIO, filename: str = 'DefaultFilename.txt'):
        self.fp = fp
        self.filename = filename

    def read(self) -> str:
        if isinstance(self.fp, str):
            if os.path.exists(self.fp):
                with open(self.fp) as fp:
                    data = fp.read()
                return data
            return self.fp
        elif isinstance(self.fp, io.BytesIO):
            return self.fp.read().decode('utf-8')
        elif isinstance(self.fp, io.StringIO):
            return self.fp.getvalue()
        else:
          raise TypeError(f'Expected str, io.StringIO, or io.BytesIO, got {type(self.fp)}')

class Gist(APIObject):
    __slots__ = (
        'id',
        'description',
        'html_url',
        'node_id',
        'files',
        'public',
        'owner',
        'created_at',
        'comments',
        'truncated',
        )
    def __init__(self, response: dict, _http: http) -> None:
        super().__init__(response, _http)
        tmp = self.__slots__ + APIObject.__slots__
        keys = {key: value for key,value in self._response.items() if key in tmp}
        for key, value in keys.items():
            if key == 'owner':
                setattr(self, key, PartialUser(value, self._http))
                continue
            if key == 'created_at':
                setattr(self, key, dt_formatter(value))
                continue
            else:
                setattr(self, key, value)

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}; id: {self.id}, owner: {self.owner}, created_at: {self.created_at}>'


#=== Organization stuff ===#

class Organization(APIObject):
    __slots__ = (
    'login',
    'id',
    'html_url',
    'is_verified',
    'public_repos',
    'public_gists',
    'followers',
    'following',
    'created_at',
    'avatar_url',
    )

    def __init__(self, response: dict, _http: http) -> None:
        super().__init__(response, _http)
        tmp = self.__slots__ + APIObject.__slots__
        keys = {key: value for key,value in self._response.items() if key in tmp}
        for key, value in keys.items():
            if key == 'login':
                setattr(self, key, value)
                continue
            if '_at' in key and value is not None:
                setattr(self, key, dt_formatter(value))
                continue

            else:
                setattr(self, key, value)
                continue

    def __repr__(self):
        return f'<{self.__class__.__name__}; login: {self.login!r}, id: {self.id}, html_url: {self.html_url}, is_verified: {self.is_verified}, public_repos: {self.public_repos}, public_gists: {self.public_gists}, created_at: {self.created_at}>'
