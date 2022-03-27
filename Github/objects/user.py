#== user.py ==#

import aiohttp

from .objects import APIOBJECT, dt_formatter
from .. import http

__all__ = (
    'User',
    'PartialUser'
)

class _BaseUser(APIOBJECT):
    __slots__ = (
        'login',
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
        'following',
        'created_at',
        )
    def __init__(self, response: dict, session: aiohttp.ClientSession) -> None:
        super().__init__(response, session)
        tmp = self.__slots__ + _BaseUser.__slots__
        keys = {key: value for key,value in self._response.items() if key in tmp}
        for key, value in keys.items():
            if '_at' in key and value is not None:
                setattr(self, key, dt_formatter(value))
                continue
            else:
                setattr(self, key, value)
                continue

            setattr(self, key, value)

    def __repr__(self):
        return f'<User; login: {self.login}, id: {self.id}, created_at: {dt_formatter(self.created_at)}>'

    @classmethod
    async def get_user(cls, session: aiohttp.ClientSession, username: str) -> 'User':
        """Returns a User object from the username, with the mentions slots."""
        response = await http.get_user(session, username)
        return User(response, session)

class PartialUser(_BaseUser):
    __slots__ = (
        'site_admin',
        'html_url',
        'created_at',
        ) + _BaseUser.__slots__

    def __init__(self, response: dict, session: aiohttp.ClientSession) -> None:
        super().__init__(response, session)
        self.site_admin = response.get('site_admin')
        self.html_url = response.get('html_url')
        self.avatar_url = response.get('avatar_url')


    def __repr__(self):
        return f'<PartialUser; login: {self.login}, id: {self.id}, site_admin: {self.site_admin}, html_url: {self.html_url}, created_at: {dt_formatter(self.created_at)}>'

    async def _get_user(self):
        """Upgrades the PartialUser to a User object.""" 
        response = await http.get_user(self.session, self.login)
        return User(response, self.session)