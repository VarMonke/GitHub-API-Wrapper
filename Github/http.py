#== http.py ==#

import aiohttp
from collections import namedtuple
from datetime import datetime
from types import SimpleNamespace
import re
import json

from .exceptions import *
from .exceptions import RepositoryAlreadyExists
from .objects import *
from .urls import *

__all__ = (
    'Paginator',
    'http',
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

GithubUserData = GithubRepoData = GithubIssueData = GithubOrgData = dict[str, str | int]

class http:
    def __init__(self, headers: dict[str, str | int], auth: aiohttp.BasicAuth | None):
        if not headers.get('User-Agent'):
            headers['User-Agent'] = 'Github-API-Wrapper'
        self._rates = Rates('', '', '', '', '')
        self.headers = headers
        self.auth = auth

    def __await__(self):
        return self.start().__await__()

    async def start(self):
        self.session = aiohttp.ClientSession(
            headers=self.headers,
            auth=self.auth,
            trace_configs=[trace_config],
        )
        return self

    def update_headers(self, *, flush: bool = False, new_headers: dict[str, str | int]):
        if flush:
            from multidict import CIMultiDict
            self.session.headers = CIMultiDict(**new_headers)
        else:
            self.session.headers = {**self.session.headers, **new_headers}

    async def update_auth(self, *, username: str, token: str):
        auth = aiohttp.BasicAuth(username, token)
        headers = self.session.headers
        config = self.session.trace_configs
        await self.session.close()
        self.session = aiohttp.ClientSession(
            headers=headers,
            auth=auth,
            trace_configs=config
        )

    async def get_self(self) -> GithubUserData:
        """Returns the authenticated User's data"""
        result = await self.session.get(SELF_URL)
        if 200 <= result.status <= 299:
            return await result.json()
        raise InvalidToken

    async def get_user(self, username: str) -> GithubUserData:
        """Returns a user's public data in JSON format."""
        result = await self.session.get(USERS_URL.format(username))
        if 200 <= result.status <= 299:
            return await result.json()
        raise UserNotFound

    async def get_repo(self, owner: str, repo_name: str) -> GithubRepoData:
        """Returns a Repo's raw JSON from the given owner and repo name."""
        result = await self.session.get(REPO_URL.format(owner, repo_name))
        if 200 <= result.status <= 299:
            return await result.json()
        raise RepositoryNotFound
    
    async def get_repo_issue(self, owner: str, repo_name: str, issue_number: int) -> GithubIssueData:
        """Returns a single issue's JSON from the given owner and repo name."""
        result = await self.session.get(REPO_ISSUE_URL.format(owner, repo_name, issue_number))
        if 200 <= result.status <= 299:
            return await result.json()
        raise IssueNotFound

    async def create_repo(self, **kwargs: dict[str, str | bool]) -> GithubRepoData:
        """Creates a repo for you with given data"""
        data = {
            'name': kwargs.get('name'),
            'description': kwargs.get('description'),
            'private': kwargs.get('private', True),
            'gitignore_template': kwargs.get('gitignore'),
            'license': kwargs.get('license'),
        }
        result = await self.session.post(CREATE_REPO_URL, data=json.dumps(data))
        if 200 <= result.status <= 299:
            return await result.json()
        if result.status == 401:
            raise NoAuthProvided
        raise RepositoryAlreadyExists

    async def get_org(self, org_name: str) -> GithubOrgData:
        """Returns an org's public data in JSON format."""
        result = await self.session.get(ORG_URL.format(org_name))
        if 200 <= result.status <= 299:
            return await result.json()
        raise OrganizationNotFound
