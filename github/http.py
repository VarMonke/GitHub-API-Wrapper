# == http.py ==#

from __future__ import annotations

import json
import platform
import re
from datetime import datetime
from types import SimpleNamespace
from typing import Any, Dict, List, NamedTuple, Optional, Tuple, Type, Union

import aiohttp
from typing_extensions import TypeAlias

from . import __version__
from .exceptions import *
from .objects import File, Gist, Repository, User, bytes_to_b64
from .urls import *

__all__: Tuple[str, ...] = (
    'Paginator',
    'http',
)


LINK_PARSING_RE = re.compile(r"<(\S+(\S))>; rel=\"(\S+)\"")


class Rates(NamedTuple):
    remaining: str
    used: str
    total: str
    reset_when: Union[datetime, str]
    last_request: Union[datetime, str]


# aiohttp request tracking / checking bits
async def on_req_start(
    session: aiohttp.ClientSession, ctx: SimpleNamespace, params: aiohttp.TraceRequestStartParams
) -> None:
    """Before-request hook to make sure we don't overrun the ratelimit."""
    # print(repr(session), repr(ctx), repr(params))
    if session._rates.remaining in ('0', '1'):  # type: ignore
        raise Exception('Ratelimit exceeded')


async def on_req_end(session: aiohttp.ClientSession, ctx: SimpleNamespace, params: aiohttp.TraceRequestEndParams) -> None:
    """After-request hook to adjust remaining requests on this time frame."""
    headers = params.response.headers

    remaining = headers['X-RateLimit-Remaining']
    used = headers['X-RateLimit-Used']
    total = headers['X-RateLimit-Limit']
    reset_when = datetime.fromtimestamp(int(headers['X-RateLimit-Reset']))
    last_req = datetime.utcnow()

    session._rates = Rates(remaining, used, total, reset_when, last_req)


trace_config = aiohttp.TraceConfig()
trace_config.on_request_start.append(on_req_start)
trace_config.on_request_end.append(on_req_end)

APIType: TypeAlias = Union[User, Gist, Repository]


async def make_session(*, headers: Dict[str, str], authorization: Union[aiohttp.BasicAuth, None]) -> aiohttp.ClientSession:
    """This makes the ClientSession, attaching the trace config and ensuring a UA header is present."""
    if not headers.get('User-Agent'):
        headers['User-Agent'] = (
            f'Github-API-Wrapper (https://github.com/VarMonke/Github-Api-Wrapper) @ {__version__} Python'
            f' {platform.python_version()} aiohttp {aiohttp.__version__}'
        )

    session = aiohttp.ClientSession(auth=authorization, headers=headers, trace_configs=[trace_config])
    session._rates = Rates('', '', '', '', '')
    return session


# pagination
class Paginator:
    """This class handles pagination for objects like Repos and Orgs."""

    def __init__(self, session: aiohttp.ClientSession, response: aiohttp.ClientResponse, target_type: str):
        self.session = session
        self.response = response
        self.should_paginate = bool(self.response.headers.get('Link', False))
        types: Dict[str, Type[APIType]] = {  # note: the type checker doesnt see subclasses like that
            'user': User,
            'gist': Gist,
            'repo': Repository,
        }
        self.target_type: Type[APIType] = types[target_type]
        self.pages = {}
        self.is_exhausted = False
        self.current_page = 1
        self.next_page = self.current_page + 1
        self.parse_header(response)

    async def fetch_page(self, link: str) -> Dict[str, Union[str, int]]:
        """Fetches a specific page and returns the JSON."""
        return await (await self.session.get(link)).json()

    async def early_return(self) -> List[APIType]:
        # I don't rightly remember what this does differently, may have a good ol redesign later
        return [self.target_type(data, self) for data in await self.response.json()]  # type: ignore

    async def exhaust(self) -> List[APIType]:
        """Iterates through all of the pages for the relevant object and creates them."""
        if self.should_paginate:
            return await self.early_return()

        out: List[APIType] = []
        for page in range(1, self.max_page + 1):
            result = await self.session.get(self.bare_link + str(page))
            out.extend([self.target_type(item, self) for item in await result.json()])  # type: ignore

        self.is_exhausted = True
        return out

    def parse_header(self, response: aiohttp.ClientResponse) -> None:
        """Predicts wether a call will exceed the ratelimit ahead of the call."""
        header = response.headers['Link']
        groups = LINK_PARSING_RE.findall(header)
        self.max_page = int(groups[1][1])
        if int(response.headers['X-RateLimit-Remaining']) < self.max_page:
            raise WillExceedRatelimit(response, self.max_page)
        self.bare_link = groups[0][0][:-1]


# GithubUserData = GithubRepoData = GithubIssueData = GithubOrgData = GithubGistData = Dict[str, Union [str, int]]
# Commentnig this out for now, consider using TypeDict's instead in the future <3


class http:
    def __init__(self, headers: Dict[str, Union[str, int]], auth: Union[aiohttp.BasicAuth, None]) -> None:
        if not headers.get('User-Agent'):
            headers['User-Agent'] = (
                'Github-API-Wrapper (https://github.com/VarMonke/Github-Api-Wrapper) @'
                f' {__version__} Python/{platform.python_version()} aiohttp/{aiohttp.__version__}'
            )

        self._rates = Rates('', '', '', '', '')
        self.headers = headers
        self.auth = auth

    def __await__(self):
        return self.start().__await__()

    async def start(self):
        self.session = aiohttp.ClientSession(
            headers=self.headers,  # type: ignore
            auth=self.auth,
            trace_configs=[trace_config],
        )
        if not hasattr(self.session, "_rates"):
            self.session._rates = Rates('', '', '', '', '')
        return self

    def update_headers(self, *, flush: bool = False, new_headers: Dict[str, Union[str, int]]):
        if flush:
            from multidict import CIMultiDict

            self.session._default_headers = CIMultiDict(**new_headers)  # type: ignore
        else:
            self.session._default_headers = {**self.session.headers, **new_headers}  # type: ignore

    async def update_auth(self, *, username: str, token: str):
        auth = aiohttp.BasicAuth(username, token)
        headers = self.session.headers
        config = self.session.trace_configs
        await self.session.close()
        self.session = aiohttp.ClientSession(headers=headers, auth=auth, trace_configs=config)

    def data(self):
        # return session headers and auth
        headers = {**self.session.headers}
        return {'headers': headers, 'auth': self.auth}

    async def latency(self):
        """Returns the latency of the current session."""
        start = datetime.utcnow()
        await self.session.get(BASE_URL)
        return (datetime.utcnow() - start).total_seconds()

    async def get_self(self) -> Dict[str, Union[str, int]]:
        """Returns the authenticated User's data"""
        result = await self.session.get(SELF_URL)
        if 200 <= result.status <= 299:
            return await result.json()
        raise InvalidToken

    async def get_user(self, username: str) -> Dict[str, Union[str, int]]:
        """Returns a user's public data in JSON format."""
        result = await self.session.get(USERS_URL.format(username))
        if 200 <= result.status <= 299:
            return await result.json()
        raise UserNotFound

    async def get_user_repos(self, _user: User) -> List[Dict[str, Union[str, int]]]:
        result = await self.session.get(USER_REPOS_URL.format(_user.login))
        if 200 <= result.status <= 299:
            return await result.json()

        print('This shouldn\'t be reachable')
        return []

    async def get_user_gists(self, _user: User) -> List[Dict[str, Union[str, int]]]:
        result = await self.session.get(USER_GISTS_URL.format(_user.login))
        if 200 <= result.status <= 299:
            return await result.json()

        print('This shouldn\'t be reachable')
        return []

    async def get_user_orgs(self, _user: User) -> List[Dict[str, Union[str, int]]]:
        result = await self.session.get(USER_ORGS_URL.format(_user.login))
        if 200 <= result.status <= 299:
            return await result.json()

        print('This shouldn\'t be reachable')
        return []

    async def get_repo(self, owner: str, repo_name: str) -> Optional[Dict[str, Union[str, int]]]:
        """Returns a Repo's raw JSON from the given owner and repo name."""
        result = await self.session.get(REPO_URL.format(owner, repo_name))
        if 200 <= result.status <= 299:
            return await result.json()
        raise RepositoryNotFound

    async def get_repo_issue(self, owner: str, repo_name: str, issue_number: int) -> Optional[Dict[str, Any]]:
        """Returns a single issue's JSON from the given owner and repo name."""
        result = await self.session.get(REPO_ISSUE_URL.format(owner, repo_name, issue_number))
        if 200 <= result.status <= 299:
            return await result.json()
        raise IssueNotFound

    async def delete_repo(self, owner: Optional[str], repo_name: str) -> Optional[str]:
        """Deletes a Repo from the given owner and repo name."""
        result = await self.session.delete(REPO_URL.format(owner, repo_name))
        if 204 <= result.status <= 299:
            return 'Successfully deleted repository.'
        if result.status == 403:  # type: ignore
            raise MissingPermissions
        raise RepositoryNotFound

    async def delete_gist(self, gist_id: Union[str, int]) -> Optional[str]:
        """Deletes a Gist from the given gist id."""
        result = await self.session.delete(GIST_URL.format(gist_id))
        if result.status == 204:
            return 'Successfully deleted gist.'
        if result.status == 403:
            raise MissingPermissions
        raise GistNotFound

    async def get_org(self, org_name: str) -> Dict[str, Union[str, int]]:
        """Returns an org's public data in JSON format."""  # type: ignore
        result = await self.session.get(ORG_URL.format(org_name))
        if 200 <= result.status <= 299:
            return await result.json()
        raise OrganizationNotFound

    async def get_gist(self, gist_id: str) -> Dict[str, Union[str, int]]:
        """Returns a gist's raw JSON from the given gist id."""
        result = await self.session.get(GIST_URL.format(gist_id))
        if 200 <= result.status <= 299:
            return await result.json()
        raise GistNotFound

    async def create_gist(
        self, *, files: List['File'] = [], description: str = 'Default description', public: bool = False
    ) -> Dict[str, Union[str, int]]:
        data = {}
        data['description'] = description
        data['public'] = public
        data['files'] = {}
        for file in files:
            data['files'][file.filename] = {'filename': file.filename, 'content': file.read()}  # helps editing the file
        data = json.dumps(data)
        _headers = dict(self.session.headers)
        result = await self.session.post(CREATE_GIST_URL, data=data, headers=_headers)
        if 201 == result.status:
            return await result.json()
        raise InvalidToken

    async def create_repo(
        self, name: str, description: str, public: bool, gitignore: Optional[str], license: Optional[str]
    ) -> Dict[str, Union[str, int]]:
        """Creates a repo for you with given data"""
        data = {
            'name': name,
            'description': description,
            'public': public,
            'gitignore_template': gitignore,
            'license': license,
        }
        result = await self.session.post(CREATE_REPO_URL, data=json.dumps(data))
        if 200 <= result.status <= 299:
            return await result.json()
        if result.status == 401:
            raise NoAuthProvided
        raise RepositoryAlreadyExists

    async def add_file(self, owner: str, repo_name: str, filename: str, content: str, message: str, branch: str):
        """Adds a file to the given repo."""

        data = {
            'content': bytes_to_b64(content=content),
            'message': message,
            'branch': branch,
        }

        result = await self.session.put(ADD_FILE_URL.format(owner, repo_name, filename), data=json.dumps(data))
        if 200 <= result.status <= 299:
            return await result.json()
        if result.status == 401:
            raise NoAuthProvided
        if result.status == 409:
            raise FileAlreadyExists
        if result.status == 422:
            raise FileAlreadyExists('This file exists, and can only be edited.')
        return await result.json(), result.status
