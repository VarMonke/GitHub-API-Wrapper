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

    async def start(self):
        """Main entry point to the wrapper, this creates the ClientSession."""
        self.session = await http.make_session(headers=self._headers, authorization=self._auth)

    async def get_user(self, username: str):
        """Fetch a Github user from their username."""
        return User(await http.get_user(self.session, username), self.session)