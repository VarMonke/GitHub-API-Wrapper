# == main.py ==#
from __future__ import annotations

import functools
from typing import (
    Any,
    Awaitable,
    Callable,
    Coroutine,
    Dict,
    Generator,
    List,
    Literal,
    Optional,
    Tuple,
    TypeVar,
    Union,
    overload,
)

import aiohttp
from typing_extensions import Concatenate, ParamSpec, Self

from . import exceptions
from .cache import ObjectCache
from .http import http
from .objects import File, Gist, Issue, Organization, Repository, User

__all__: Tuple[str, ...] = ('GHClient', 'Client')

T = TypeVar('T')
P = ParamSpec('P')


class GHClient:
    """The main client, used to start most use-cases.

    Parameters
    ----------
    username: Optional[:class:`str`]
        An optional username to be provided along with a token to make authenticated API calls.
        If you provide a username, the token must be provided as well.
    user_cache_size: Optional[:class:`int`]
        Determines the maximum number of User objects that will be cached in memory.
        Defaults to 30, must be between 30 and 0 inclusive.
    repo_cache_size: Optional[:class:`int`]
        Determines the maximum number of Repository objects that will be cached in memory.
        Defaults to 15, must be between 30 and 0 inclusive.
    custom_headers: Optional[:class:`dict`]
        A way to pass custom headers into the client session that drives the client, eg. a user-agent.

    Attributes
    ----------
    username: Optional[:class:`str`]
        The authenticated Client's username, if applicable.
    __token: Optional[:class:`str`]
        The authenticated Client's token, if applicable.
    """

    has_started: bool = False

    def __init__(
        self,
        *,
        username: Optional[str] = None,
        token: Optional[str] = None,
        user_cache_size: int = 30,
        repo_cache_size: int = 15,
        custom_headers: Dict[str, Union[str, int]] = {},
    ):
        self._headers = custom_headers

        if username and token:
            self.username = username
            self.__token = token
            self.__auth = aiohttp.BasicAuth(username, token)
        else:
            self.__auth = None
            self.username = None
            self.__token = None

        self.http = http(headers=custom_headers, auth=self.__auth)

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
        try:
            session = self.http.session
            await session.close()
        except Exception as exc:
            raise Exception('HTTP Session doesn\'t exist') from exc

    def __repr__(self) -> str:
        return f'<Client has_auth={bool(self.__auth)}>'

    @overload
    def check_limits(self, as_dict: Literal[True] = True) -> Dict[str, Union[str, int]]:
        ...

    @overload
    def check_limits(self, as_dict: Literal[False] = False) -> List[str]:
        ...

    def check_limits(self, as_dict: bool = False) -> Union[Dict[str, Union[str, int]], List[str]]:
        """Returns the remaining number of API calls per timeframe.

        Parameters
        ----------
        as_dict: Optional[:class:`bool`]
            Set to True to return the remaining calls in a dictionary.
            Set to False to return the remaining calls in a list.
            Defaults to False
        """
        if not self.has_started:
            raise exceptions.NotStarted
        if not as_dict:
            output: List[str] = []
            for key, value in self.http.session._rates._asdict().items():  # type: ignore
                output.append(f"{key} : {value}")

            return output

        return self.http.session._rates  # type: ignore

    async def update_auth(self, *, username: str, token: str) -> None:
        """Allows you to input auth information after instantiating the client.

        Parameters
        ----------
        username: :class:`str`
            The username to update the authentication to.
            Must also be provided with the valid token.
        token: :class:`str`
            The token to update the authentication to.
            Must also be providede with the valid username.
        """
        # check if username and token is valid
        await self.http.update_auth(username=username, token=token)
        try:
            await self.http.get_self()
        except exceptions.InvalidToken as exc:
            raise exceptions.InvalidToken from exc

    async def start(self) -> Self:
        """Main entry point to the wrapper, this creates the ClientSession.

        Parameters
        ----------
        """
        if self.has_started:
            raise exceptions.AlreadyStarted
        if self.__auth:
            self.http = await http(auth=self.__auth, headers=self._headers)
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
                    obj = self._user_cache.get(kwargs.get('user'))
                    if obj:
                        return obj

                    user: User = await func(self, *args, **kwargs)  # type: ignore
                    self._user_cache[kwargs.get("user")] = user
                    return user
                if type == 'repo':
                    obj = self._repo_cache.get(kwargs.get('repo'))
                    if obj:
                        return obj

                    repo: Repository = await func(self, *args, **kwargs)  # type: ignore
                    self._repo_cache[kwargs.get('repo')] = repo
                    return repo

            return wrapped

        return wrapper

    # @_cache(type='User')
    async def get_self(self) -> User:
        """:class:`User`: Returns the authenticated User object."""
        if self.__auth:
            return User(await self.http.get_self(), self.http)
        else:
            raise exceptions.NoAuthProvided

    async def get_user(self, *, user: str) -> User:
        """:class:`User`: Fetch a Github user from their username.

        Parameters
        ----------
        user: :class:`str`
            The name of the user to fetch.
        """
        return User(await self.http.get_user(user), self.http)

    async def get_repo(self, *, owner: str, repo: str) -> Repository:
        """:class:`Repository`: Fetch a Github repository from it's name.

        Parameters
        ----------
        owner: :class:`str`
            The name of the owner of a given reposiory.
        repo: :class:`str`
            The name of the repository to fetch.
        """
        return Repository(await self.http.get_repo(owner, repo), self.http)  # type: ignore

    async def get_issue(self, *, owner: str, repo: str, issue: int) -> Issue:
        """:class:`Issue`: Fetch a Github Issue from it's name.

        Parameters
        ----------
        owner: :class:`str`
            The name of the owner of the repository for which the issue relates to.
        repo: :class:`str`
            The name of the repository to which the issue is related to.
        issue: :class:`int`
            The ID of the issue to fetch.
        """
        return Issue(await self.http.get_repo_issue(owner, repo, issue), self.http)  # type: ignore #fwiw, this shouldn't error but pyright <3

    async def create_repo(
        self,
        name: str,
        description: str = 'Repository created using Github-Api-Wrapper.',
        public: bool = False,
        gitignore: Optional[str] = None,
        license: Optional[str] = None,
    ) -> Repository:
        """Creates a Repository with supplied data.
        Requires API authentication.

        Parameters
        ----------
        name: :class:`str`
            The name of the repository to be created.
        description: :class:`str`
            A description of the repository to be created.
        public: :class:`bool`
            Determines whether only the repository will be visible to the public.
            Defaults to False (private repository).
        gitignore: Optional[:class:`str`]
            .gitignore template to use.
            See https://github.com/github/gitignore for GitHub's own templates.
            Defaults to None.
        license: Optional[:class:`str`]
            TODO: Document this.

        Returns
        -------
        :class:`Repository`
        """
        return Repository(
            await self.http.create_repo(name, description, public, gitignore, license),
            self.http,
        )

    async def delete_repo(self, repo: str) -> Optional[str]:
        """Delete a Github repository, requires authorisation.

        Parameters
        ----------
        repo: :class:`str`
            The name of the repository to delete.

        Returns
        -------
        Optional[:class:`str`]
        """
        return await self.http.delete_repo(self.username, repo)

    async def get_gist(self, gist: str) -> Gist:
        """Fetch a Github gist from it's id.

        Parameters
        ----------
        gist: :class:`str`
            The id of the gist to fetch.

        Returns
        -------
        :class:`Gist`
        """
        return Gist(await self.http.get_gist(gist), self.http)

    async def create_gist(
        self, *, files: List[File], description: str = 'Gist from Github-Api-Wrapper', public: bool = True
    ) -> Gist:
        """Creates a Gist with the given files, requires authorisation.

        Parameters
        ----------
        files: List[:class:`File`]
            A list of File objects to upload to the gist.
        description: :class:`str`
            A description of the gist.
        public: :class:`bool`
            Determines whether the gist will be visible to the public.
            Defaults to False (private).

        Returns
        -------
        :class:`Gist`
        """
        return Gist(
            await self.http.create_gist(files=files, description=description, public=public),
            self.http,
        )

    async def delete_gist(self, gist: int) -> Optional[str]:
        """Delete a Github gist, requires authorisation.

        Parameters
        ----------
        gist: :class:`int`
            The ID of the gist to delete.

        Returns
        -------
        Optional[:class:`str`]
        """
        return await self.http.delete_gist(gist)

    async def get_org(self, org: str) -> Organization:
        """Fetch a Github organization from it's name.

        Parameters
        ----------
        org: :class:`str`
            The name of the organization to fetch.

        Returns
        -------
        :class:`Organization`
        """
        return Organization(await self.http.get_org(org), self.http)

    async def latency(self) -> float:
        """:class:`float`: Returns the latency of the client."""
        return await self.http.latency()

    async def close(self) -> None:
        """Close the session."""
        await self.http.session.close()


class Client(GHClient):
    pass
