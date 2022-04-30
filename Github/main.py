# == main.py ==#
from __future__ import annotations

__all__ = ("GHClient",)

import functools
import aiohttp

from typing import (
    Awaitable,
    Callable,
    Literal,
    Any,
    Coroutine,
    Dict,
    Generator,
    Optional,
    Union,
    List,
    overload,
    TypeVar,
)
from typing_extensions import Self, ParamSpec, Concatenate

from . import exceptions
from .cache import ObjectCache
from .http import http
from .objects import Gist, Issue, Organization, Repository, User, File


T = TypeVar('T')
P = ParamSpec('P')


class GHClient:
    has_started: bool = False

    def __init__(
        self,
        *,
        username: Union[str, None] = None,
        token: Union[str, None] = None,
        user_cache_size: int = 30,
        repo_cache_size: int = 15,
        custom_headers: dict[str, Union[str, int]] = {},
    ):
        """The main client, used to start most use-cases."""
        self._headers = custom_headers

        if username and token:
            self.username = username
            self.token = token
            self._auth = aiohttp.BasicAuth(username, token)
        else:
            self._auth = None
            self.username = None
            self.token = None

        self.http = http(headers=custom_headers, auth=self._auth)

        self._user_cache = ObjectCache[Any, User](user_cache_size)
        self._repo_cache = ObjectCache[Any, Repository](repo_cache_size)

        # Cache manegent
        self._cache(type='user')(self.get_self)  # type: ignore
        self._cache(type='user')(self.get_user)  # type: ignore
        self._cache(type='repo')(self.get_repo)  # type: ignore

    def __call__(self, *args: Any, **kwargs: Any) -> Coroutine[Any, Any, Self]:
        return self.start(*args, **kwargs)

    def __await__(self) -> Generator[Any, Any, Self]:
        return self.start().__await__()

    async def __aenter__(self) -> Self:
        await self.start()
        return self

    async def __aexit__(self, *args: Any, **kwargs: Any) -> None:
        if session := getattr(self.http, 'session', None):
            await session.close()

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} has_auth={bool(self._auth)}>'

    @overload
    def check_limits(self, as_dict: Literal[True] = True) -> Dict[str, Union[str, int]]:
        ...

    @overload
    def check_limits(self, as_dict: Literal[False] = False) -> List[str]:
        ...

    def check_limits(self, as_dict: bool = False) -> Union[Dict[str, Union[str, int]], List[str]]:
        if not self.has_started:
            raise exceptions.NotStarted
        if not as_dict:
            output: List[str] = []
            for key, value in self.http.session._rates._asdict().items():  # type: ignore
                output.append(f"{key} : {value}")

            return output

        return self.http.session._rates  # type: ignore

    async def update_auth(self, username: str, token: str) -> None:
        """Allows you to input auth information after instantiating the client."""
        # check if username and token is valid
        await self.http.update_auth(username=username, token=token)
        try:
            await self.http.get_self()
        except exceptions.InvalidToken as exc:
            raise exceptions.InvalidToken from exc

    async def start(self) -> Self:
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

    def _cache(
        self: Self, *, type: str
    ) -> Callable[
        [Callable[Concatenate[Self, P], Awaitable[T]]],
        Callable[Concatenate[Self, P], Awaitable[Optional[Union[T, User, Repository]]]],
    ]:
        def wrapper(
            func: Callable[Concatenate[Self, P], Awaitable[T]]
        ) -> Callable[Concatenate[Self, P], Awaitable[Optional[Union[T, User, Repository]]]]:
            @functools.wraps(func)
            async def wrapped(self: Self, *args: P.args, **kwargs: P.kwargs) -> Optional[Union[T, User, Repository]]:
                if type == 'user':
                    if obj := self._user_cache.get(kwargs.get('user')):
                        return obj

                    user: User = await func(self, *args, **kwargs)  # type: ignore
                    self._user_cache[kwargs.get("user")] = user
                    return user
                if type == 'repo':
                    if obj := self._repo_cache.get(kwargs.get('repo')):
                        return obj

                    repo: Repository = await func(self, *args, **kwargs)  # type: ignore
                    self._repo_cache[kwargs.get('repo')] = repo
                    return repo

            return wrapped

        return wrapper

    # @_cache(type='User')
    async def get_self(self) -> User:
        """Returns the authenticated User object."""
        if self._auth:
            return User(await self.http.get_self(), self.http)
        else:
            raise exceptions.NoAuthProvided

    async def get_user(self, *, user: str) -> User:
        """Fetch a Github user from their username."""
        return User(await self.http.get_user(user), self.http)

    async def get_repo(self, *, owner: str, repo: str) -> Repository:
        """Fetch a Github repository from it's name."""
        return Repository(await self.http.get_repo(owner, repo), self.http)

    async def get_issue(self, *, owner: str, repo: str, issue: int) -> Issue:
        """Fetch a Github Issue from it's name."""
        return Issue(await self.http.get_repo_issue(owner, repo, issue), self.http)

    async def create_repo(
        self,
        name: str,
        description: str = 'Repository created using Github-Api-Wrapper.',
        public: bool = False,
        gitignore: Optional[str] = None,
        license: Optional[str] = None,
    ) -> Repository:
        return Repository(
            await self.http.create_repo(name, description, public, gitignore, license),
            self.http,
        )

    async def delete_repo(self, repo: str, owner: str) -> Optional[str]:
        """Delete a Github repository, requires authorisation."""
        owner = owner or self.username  # type: ignore
        return await self.http.delete_repo(owner, repo)

    async def get_gist(self, gist: int) -> Gist:
        """Fetch a Github gist from it's id."""
        return Gist(await self.http.get_gist(gist), self.http)

    async def create_gist(self, *, files: List[File], description: str, public: bool) -> Gist:
        """Creates a Gist with the given files, requires authorisation."""
        return Gist(
            await self.http.create_gist(files=files, description=description, public=public),
            self.http,
        )

    async def delete_gist(self, gist: int) -> Optional[str]:
        """Delete a Github gist, requires authorisation."""
        return await self.http.delete_gist(gist)

    async def get_org(self, org: str) -> Organization:
        """Fetch a Github organization from it's name."""
        return Organization(await self.http.get_org(org), self.http)

    async def latency(self) -> float:
        """Returns the latency of the client."""
        return await self.http.latency()
