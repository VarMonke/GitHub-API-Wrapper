#== objects.py ==#

from collections import namedtuple
from datetime import datetime

import aiohttp

from . import http

__all__ = (
    'User',
)

def dt_formatter(time_str):
    if time_str is not None:
        return datetime.strptime(time_str, r"%Y-%m-%dT%H:%M:%SZ")
    return None

def repr_dt(time_str):
    return time_str.strftime(r'%d-%m-%Y, %H:%M:%S')

class APIOBJECT:
    __slots__ = (
        '_response',
        'session'
    )

    def __init__(self, response: dict[str, str | int], session: aiohttp.ClientSession) -> None:
        self._response = response
        self.session = session


    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}>'

class _BaseUser(APIOBJECT):
    __slots__ = (
        'name',
        'id',
        )
    def __init__(self, response: dict, session: aiohttp.ClientSession) -> None:
        super().__init__(response, session)
        self.login = response.get('login')
        self.id = response.get('id')

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}; id = {self.id}, login = {self.login}>'

class User(_BaseUser): 
    __slots__ = (
        'login',
        'id',
        'avatar_url',
        'html_url',
        'public_repos',
        'public_gists',
        'followers',
        'following'
        'created_at',
        )
    def __init__(self, response: dict, session: aiohttp.ClientSession) -> None:
        super().__init__(response, session)
        tmp = self.__slots__
        keys = {key: value for key,value in self.response.items() if key in tmp}
        for key, value in key.items():
            if key == 'login':
                self.login = value
                return

            if '_at' in key and value is not None:
                setattr(self, key, dt_formatter(value))
                return

            setattr(self, key, value)

    def __repr__(self):
        return f'<User; login: {self.login}, id: {self.id}, created_at: {repr_dt(self.created_at)}>'

    @classmethod
    async def get_user(self, session: aiohttp.ClientSession, username: str) -> 'User':
        """Returns a User object from the username, with the mentions slots."""
        response = await http.get_user(session, username)
        return User(response, session)    