#== http.py ==#


import aiohttp
from collections import namedtuple
from datetime import datetime
from types import SimpleNamespace
import re

from .exceptions import *
from .objects import *
from .urls import *

__all__ = (
    'make_session',
    'Paginator',
    'get_user',
)


LINK_PARSING_RE = re.compile(r"<(\S+(\S))>; rel=\"(\S+)\"")
Rates = namedtuple('Rates', ('remaining', 'used', 'total', 'reset_when', 'last_request'))

# aiohttp request tracking / checking bits
async def on_req_start(
    session: aiohttp.ClientSession,
    ctx: SimpleNamespace,
    params: aiohttp.TraceRequestStartParams
) -> None:
    """Before-request hook to make sure we don't overrun the ratelimit."""
    #print(repr(session), repr(ctx), repr(params))
    pass

async def on_req_end(
    session: aiohttp.ClientSession,
    ctx: SimpleNamespace,
    params: aiohttp.TraceRequestEndParams
) -> None:
    """After-request hook to adjust remaining requests on this time frame."""
    headers = params.response.headers

    remaining   = headers['X-RateLimit-Remaining']
    used        = headers['X-RateLimit-Used']
    total       = headers['X-RateLimit-Limit']
    reset_when  = datetime.fromtimestamp(int(headers['X-RateLimit-Reset']))
    last_req    = datetime.utcnow()

    session._rates = Rates(remaining, used, total, reset_when, last_req)

trace_config = aiohttp.TraceConfig()
trace_config.on_request_start.append(on_req_start)
trace_config.on_request_end.append(on_req_end)

async def make_session(*, headers: dict[str, str], authorization: aiohttp.BasicAuth | None) -> aiohttp.ClientSession:
    """This makes the ClientSession, attaching the trace config and ensuring a UA header is present."""
    if not headers.get('User-Agent'):
        headers['User-Agent'] = 'Github-API-Wrapper'

    session = aiohttp.ClientSession(
        auth=authorization,
        headers=headers,
        trace_configs=[trace_config]
    )
    session._rates = Rates('', '' , '', '', '')
    return session

# pagination
class Paginator:
    """This class handles pagination for objects like Repos and Orgs."""
    def __init__(self, session: aiohttp.ClientSession, response: aiohttp.ClientResponse, target_type: str):
        self.session = session
        self.response = response
        self.should_paginate = bool(self.response.headers.get('Link', False))
        types: dict[str, APIOBJECT] = {
            'user': User,
        }
        self.target_type = types[target_type]
        self.pages = {}
        self.is_exhausted = False
        self.current_page = 1
        self.next_page = self.current_page + 1
        self.parse_header(response)

    async def fetch_page(self, link) -> dict[str, str | int]:
        """Fetches a specific page and returns the JSON."""
        return await (await self.session.get(link)).json()

    async def early_return(self) -> list[APIOBJECT]:
        # I don't rightly remember what this does differently, may have a good ol redesign later
        return [self.target_type(data, self.session) for data in await self.response.json()]

    async def exhaust(self) -> list[APIOBJECT]:
        """Iterates through all of the pages for the relevant object and creates them."""
        if self.should_paginate:
            return await self.early_return()
        out = []
        for page in range(1, self.max_page+1):
            result = await self.session.get(self.bare_link + str(page))
            out.extend([self.target_type(item, self.session) for item in await result.json()])
        self.is_exhausted = True
        return out

    def parse_header(self, response: aiohttp.ClientResponse) -> None:
        """Predicts wether a call will exceed the ratelimit ahead of the call."""
        header = response.headers.get('Link')
        groups = LINK_PARSING_RE.findall(header)
        self.max_page = int(groups[1][1])
        if int(response.headers['X-RateLimit-Remaining']) < self.max_page:
            raise WillExceedRatelimit(response, self.max_page)
        self.bare_link = groups[0][0][:-1]

# user-related functions / utils
GitHubUserData = dict[str, str | int]

async def get_user(session: aiohttp.ClientSession, username: str) -> GitHubUserData:
    """Returns a user's public data in JSON format."""
    result = await session.get(USERS_URL.format(username))
    if result.status == 200:
        return await result.json()
    raise UserNotFound