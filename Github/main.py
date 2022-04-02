#== main.py ==#

__all__ = (
    'GHClient',
)

import aiohttp
import asyncio
import functools
from getpass import getpass

from . import http
from . import exceptions
from .objects import User, PartialUser, Repository, Organization, Issue
from .cache import UserCache, RepoCache

class GHClient:
    _auth = None
    has_started = False
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
            self._auth = aiohttp.BasicAuth(username, token)

    def __await__(self) -> 'GHClient':
        return self.start().__await__()

    def __repr__(self) -> str:
        return f'<Github Client; has_auth={bool(self._auth)}>'

    def __del__(self):
        asyncio.create_task(self.session.close())

    def check_limits(self, as_dict: bool = False) -> dict[str, str | int] | list[str]:
        if not self.has_started:
            raise exceptions.NotStarted
        if not as_dict:
            output = []
            for key, value in self.session._rates._asdict().items():
                output.append(f'{key} : {value}')
            return output
        return self.session._rates._asdict()

    def update_auth(self) -> None:
        """Allows you to input auth information after instantiating the client."""
        username = input('Enter your username: ')
        token = getpass('Enter your token: ')
        self._auth = aiohttp.BasicAuth(username, token)

    async def start(self) -> 'GHClient':
        """Main entry point to the wrapper, this creates the ClientSession."""
        if self.has_started:
            raise exceptions.AlreadyStarted
        if self._auth:
            try:
                await self.get_self()
            except exceptions.InvalidToken as exc:
                raise exceptions.InvalidToken from exc
        self.session = await http.make_session(headers=self._headers, authorization=self._auth)
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

    async def get_self(self) -> User:
        """Returns the authenticated User object."""
        if self._auth:
            return await http.get_self(self.session)
        else:
            raise exceptions.NoAuthProvided

    @_cache(type='User')
    async def get_user(self, **kwargs) -> User:
        """Fetch a Github user from their username."""
        username = kwargs.get('user')
        return await http.get_user(self.session, username)

    @_cache(type='Repo')
    async def get_repo(self, **kwargs) -> Repository:
        """Fetch a Github repository from it's name."""
        owner = kwargs.get('owner')
        repo_name = kwargs.get('repo')
        return Repository(await http.get_repo_from_name(self.session, owner, repo_name), self.session)

    async def get_repo_issue(self, **kwargs) -> Issue:
        """Fetch a Github repository from it's name."""
        owner = kwargs.get('owner')
        repo_name = kwargs.get('repo')
        issue_number = kwargs.get('issue')
        return Issue(await http.get_repo_issue(self.session, owner, repo_name, issue_number), self.session)

    async def get_org(self, **kwargs) -> Organization:
        """Fetch a Github organization from it's name"""
        org_name = kwargs.get('org')
        return Organization(await http.get_org(self.session, org_name), self.session)


