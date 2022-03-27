#== main.py ==#

__all__ = (
    'GHClient',
)

from getpass import getpass
import aiohttp
import asyncio

from . import http
from . import exceptions
from .objects import User, Repository

class GHClient:
    _auth = None
    has_started = False
    def __init__(
        self,
        *,
        using_auth: bool = False,
        custom_headers: dict[str, str | int] = {}
    ):
        """The main client, used to start most use-cases."""
        self._headers = custom_headers
        if using_auth:
            username = input('Enter your username: ') #these two lines are blocking, but it's probably not a problem
            auth_token = getpass('Enter your token: ')
            self._auth = aiohttp.BasicAuth(username, auth_token)

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
        self.session = await http.make_session(headers=self._headers, authorization=self._auth)
        self.has_started = True
        return self

    def _cache(func, cache_type: str):
        async def wrapper(self: 'GHClient', name: str):
            if cache_type == 'user':
                if (user := self._user_cache.get(name)):
                    return user
                else:
                    return await func(self, name)
            if cache_type == 'repo':
                if (repo := self._repo_cache.get(name)):
                    return repo
                else:
                    return await func(self, name)
        return wrapper

    async def get_user(self, username: str) -> User:
        """Fetch a Github user from their username."""
        return User(await http.get_user(self.session, username), self.session)

    async def get_repo(self, repo_name: str) -> Repository:
        """Fetch a Github repository from it's name."""
        pass

    async def get_org(self, org_name: str) -> 'Org':
        """Fetch a Github organization from it's name"""
        pass

