#== org.py ==#

import aiohttp

from .objects import APIOBJECT, dt_formatter
from . import PartialUser
from .. import http

__all__ = (
    'Organization',
)

class Organization(APIOBJECT):
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

    def __init__(self, response: dict, session: aiohttp.ClientSession) -> None:
        super().__init__(response, session)
        tmp = self.__slots__ + APIOBJECT.__slots__
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
        return f'<Organization; login: {self.login!r}, id: {self.id}, html_url: {self.html_url}, is_verified: {self.is_verified}, public_repos: {self.public_repos}, public_gists: {self.public_gists}, created_at: {self.created_at}>'

    @classmethod
    async def from_name(cls, session: aiohttp.ClientSession, org: str) -> 'Organization':
        """Fetch a repository from its name."""
        response = await http.get_repo_from_name(session, org)
        return Organization(response, session)


