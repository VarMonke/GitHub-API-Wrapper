#== main.py ==#

__all__ = (
    'GHClient',
)

import aiohttp
import asyncio
import functools
from getpass import getpass

from .http import http
from . import exceptions
from .objects import User, PartialUser, Repository, Organization, Issue
from .cache import UserCache, RepoCache

class GHClient:
    _auth = None
    has_started = False
    http: http
    def __init__(
        self,
        *,
        username: str | None = None,
        token: str | None = None,
        user_cache_size: int = 30,
        repo_cache_size: int = 15,
        custom_headers: dict[str, str | int] = {}
    ):
        """The main client, used to start most use-cases."""
        self._headers = custom_headers
        bound = lambda hi, lo, value: max(min(value, hi), lo)
        self._user_cache = UserCache(bound(50, 0, user_cache_size))
        self._repo_cache = RepoCache(bound(50, 0, repo_cache_size))
        if username and token:
            self.username = username
            self.token = token
            self._auth = aiohttp.BasicAuth(username, token)

    def __await__(self) -> 'GHClient':
        return self.start().__await__()

    def __repr__(self) -> str:
        return f'<Github Client; has_auth={bool(self._auth)}>'

    def __del__(self):
        asyncio.create_task(self.http.session.close())

    def check_limits(self, as_dict: bool = False) -> dict[str, str | int] | list[str]:
        if not self.has_started:
            raise exceptions.NotStarted
        if not as_dict:
            output = []
            for key, value in self.http.session._rates._asdict().items():
                output.append(f'{key} : {value}')
            return output
        return self.http.session._rates._asdict()

    async def update_auth(self, username: str, token: str) -> None:
        """Allows you to input auth information after instantiating the client."""
        await self.http.update_auth(username, token)

    async def start(self) -> 'GHClient':
        """Main entry point to the wrapper, this creates the ClientSession."""
        if self.has_started:
            raise exceptions.AlreadyStarted
        if self._auth:
            self.http = await http(auth=self._auth, headers=self._headers)
            try:
                await self.http.get_self()
            except exceptions.InvalidToken as exc:
                raise exceptions.InvalidToken from exc
        else:
            self.http = await http(auth=None, headers=self._headers)
        self.has_started = True
        return self

    def _cache(*args, **kwargs):
        target_type = kwargs.get('type')
        def wrapper(func):
            @functools.wraps(func)
            async def wrapped(self, *args, **kwargs):
                if target_type == 'User':
                    if (obj := self._user_cache.get(kwargs.get('user'))):
                        return obj
                    else:
                        res = await func(self, *args, **kwargs)
                        self._user_cache[kwargs.get('user')] = res
                        return res
                if target_type == 'Repo':
                    if (obj := self._repo_cache.get(kwargs.get('repo'))):
                        return obj
                    else:
                        res = await func(self, *args, **kwargs)
                        self._repo_cache[kwargs.get('repo')] = res
                        return res
            return wrapped
        return wrapper

    @_cache(type='User')
    async def get_self(self) -> User:
        """Returns the authenticated User object."""
        if self._auth:
            return User(await self.http.get_self(), self.http.session)
        else:
            raise exceptions.NoAuthProvided

    @_cache(type='User')
    async def get_user(self, username: str) -> User:
        """Fetch a Github user from their username."""
        return User(await self.http.get_user(username), self.http.session)

    @_cache(type='Repo')
    async def get_repo(self, owner: str, repo: str) -> Repository:
        """Fetch a Github repository from it's name."""
        return Repository(await self.http.get_repo(owner, repo), self.http.session)

    async def get_issue(self, owner: str, repo: str, issue: int) -> Issue:
        """Fetch a Github repository from it's name."""
        return Issue(await self.http.get_repo_issue(owner, repo, issue), self.http.session)

    async def create_repo(self, name: str, description: str, private: bool, gitignore_template: str) -> Repository:
        """Create a new Github repository."""
        return Repository(await self.http.make_repo(name, description, private, gitignore_template), self.http.session)

    async def get_org(self, org: str) -> Organization:
        """Fetch a Github organization from it's name"""
        return Organization(await http.get_org(org), self.http.session)


