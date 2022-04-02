#== repo.py ==#

import aiohttp

from .objects import APIOBJECT, dt_formatter
from . import PartialUser, User
from .. import http

__all__ = (
    'Repository',
    'Issue'
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
        'license',
        )
    def __init__(self, response: dict, session: aiohttp.ClientSession) -> None:
        super().__init__(response, session)
        tmp = self.__slots__ + APIOBJECT.__slots__
        keys = {key: value for key,value in self._response.items() if key in tmp}
        for key, value in keys.items():
            if key == 'owner':
                setattr(self, key, PartialUser(value, session))
                continue

            if key == 'name':
                setattr(self, key, value)
                continue

            if '_at' in key and value is not None:
                setattr(self, key, dt_formatter(value))
                continue

            if 'license' in key and value is None:
                setattr(self, key, None)
                continue

            if 'license' in key and value is not None:
                setattr(self, key, value['name'])
                continue

            else:
                setattr(self, key, value)
                continue

    def __repr__(self) -> str:
        return f'<Repository; id: {self.id}, name: {self.name}, owner: {self.owner}, updated_at: {self.updated_at}, default_branch: {self.default_branch}, license: {self.license}>'

    @classmethod
    async def from_name(cls, session: aiohttp.ClientSession,owner: str, repo_name: str) -> 'Repository':
        """Fetch a repository from its name."""
        response = await http.get_repo_from_name(session, owner, repo_name)
        return Repository(response, session)


class Issue(APIOBJECT):
    __slots__ = (
        'id',
        'title',
        'user',
        'labels',
        'state',
        'created_at',
        'closed_by',
    )

    def __init__(self, response: dict, session: aiohttp.ClientSession) -> None:
        tmp = self.__slots__ + APIOBJECT.__slots__
        keys = {key: value for key,value in response.items() if key in tmp}
        for key, value in keys.items():
            if key == 'user':
                setattr(self, key, PartialUser(value, session))
                continue

            if key == 'labels':
                setattr(self, key, [label['name'] for label in value])
                continue

            if key == 'closed_by':
                setattr(self, key, User(value, session))
                continue

            else:
                setattr(self, key, value)
                continue

    def __repr__(self) -> str:
        return f'<Issue; id: {self.id}, title: {self.title}, user: {self.user}, created_at: {self.created_at}, state: {self.state}>'