#== http.py ==#

import aiohttp
from types import SimpleNamespace

from .exceptions import *
from .urls import *

# aiohttp request tracking / checking bits
async def on_req_start(
    session: aiohttp.ClientSession,
    ctx: SimpleNamespace,
    params: aiohttp.TraceRequestStartParams
) -> None:
    """Before-request hook to make sure we don't overrun the ratelimit."""
    print(repr(session), repr(ctx), repr(params))

async def on_req_end(
    session: aiohttp.ClientSession,
    ctx: SimpleNamespace,
    params: aiohttp.TraceRequestEndParams
) -> None:
    """After-request hook to adjust remaining requests on this time frame."""
    print(repr(session), repr(ctx), repr(params))

trace_config = aiohttp.TraceConfig()
trace_config.on_request_start.append(on_req_start)
trace_config.on_request_end.append(on_req_end)

async def make_session(*, headers: dict[str, str]) -> aiohttp.ClientSession:
    """This makes the ClientSession, attaching the trace config and ensuring a UA header is present."""
    if not headers.get('User-Agent'):
        headers['User-Agent'] = 'Github-API-Wrapper'

    session = aiohttp.ClientSession(
        headers=headers,
        trace_configs=[trace_config]
    )
    return session

# user-related functions / utils
GitHubUserData = dict[str, str|int]

async def get_user(session: aiohttp.ClientSession, *, _username: str) -> GitHubUserData:
    """Returns a user's public data in JSON format."""
    result = await session.get(USERS_URL.format(_username))
    if result.status == 200:
        return await result.json()
    raise UserNotFound()

