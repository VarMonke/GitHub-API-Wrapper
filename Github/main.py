#== main.py ==#

__all__ = (
    'Github',
)

import aiohttp

from . import http

class Github:
    async def start(self):
        """Main entry point to the wrapper, this creates the ClientSession."""
        headers = {}
        self._session = http.make_session(headers=headers)