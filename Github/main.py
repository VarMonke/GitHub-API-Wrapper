#== main.py ==#

__all__ = (
    'Github',
)

from getpass import getpass
import aiohttp

from . import http
from .objects import User

class Github:
    _auth = None
    session = aiohttp.ClientSession
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
            auth_token = getpass.getpass('Enter your token: ')
            self._auth = aiohttp.BasicAuth(username, auth_token)

    def __repr__(self) -> str:
        return f'<Github Client; has_auth={bool(self._auth)}>'

    def update_auth(self) -> None:
        """Allows you to input auth information after instantiating the client."""
        username = input('Enter your username: ')
        token = getpass('Enter your token: ')
        self._auth = aiohttp.BasicAuth(username, token)

    async def start(self) -> None:
        """Main entry point to the wrapper, this creates the ClientSession."""
        self.session = await http.make_session(headers=self._headers, authorization=self._auth)

    async def get_user(self, username: str) -> User:
        """Fetch a Github user from their username."""
        return User(await http.get_user(self.session, username), self.session)

    async def get_repo(self, repo_name: str) -> 'Repo':
        """Fetch a Github repository from it's name."""
        pass

    async def get_org(self, org_name: str) -> 'Org':
        """Fetch a Github organization from it's name"""
        pass

