#== gists.py ==#

import aiohttp

from .objects import APIOBJECT, dt_formatter
from . import PartialUser, User
from .. import http

__all__ = (
    'Gist',
    )

class Gist(APIOBJECT):
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
    def __init__(self, response: dict, session: aiohttp.ClientSession) -> None:
        super().__init__(response, session)
        tmp = self.__slots__ + APIOBJECT.__slots__
        keys = {key: value for key,value in self._response.items() if key in tmp}
        for key, value in keys.items():
            if key == 'owner':
                setattr(self, key, PartialUser(value, session))
                continue
            if key == 'created_at':
                setattr(self, key, dt_formatter(value))
                continue
            else:
                setattr(self, key, value)

    def __repr__(self) -> str:
        return f'<Gist; id: {self.id}, owner: {self.owner}, created_at: {self.created_at}>'