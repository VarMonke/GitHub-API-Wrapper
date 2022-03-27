#== repo.py ==#

import aiohttp

from .objects import APIOBJECT, dt_formatter
from . import PartialUser
from .. import http

__all__ = (
    'Repository',
)

class Repository(APIOBJECT):
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
        'license'
        )
    def __init__(self, response: dict, session: aiohttp.ClientSession) -> None:
        super().__init__(response, session)
        tmp = self.__slots__ + APIOBJECT.__slots__
        keys = {key: value for key,value in self.response.items() if key in tmp}
        for key, value in key.items():
            if key == 'owner':
                self.owner = PartialUser(value, self.session)
                return

            if '_at' in key and value is not None:
                setattr(self, key, dt_formatter(value))
                return

            setattr(self, key, value)

    def __repr__(self) -> str:
        return f'<Repository; id: {self.id}, name: {self.name}, owner: {self.owner}, created_at: {dt_formatter(self.created_at)}, default_branch: {self.default_branch}, license: {self.license}, >'
