# == objects.py ==#
from __future__ import annotations

from base64 import b64encode
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union

if TYPE_CHECKING:
    from .http import http

import io
import os
from datetime import datetime

__all__: Tuple[str, ...] = (
    'APIObject',
    'dt_formatter',
    'repr_dt',
    'PartialUser',
    'User',
    'Repository',
    'Issue',
    'File',
    'Gist',
    'Organization',
)


def dt_formatter(time_str: Optional[str]) -> Optional[datetime]:
    if time_str is not None:
        return datetime.strptime(time_str, r"%Y-%m-%dT%H:%M:%SZ")

    return None


def repr_dt(_datetime: datetime) -> str:
    return _datetime.strftime(r'%d-%m-%Y, %H:%M:%S')


def bytes_to_b64(content) -> str:
    return b64encode(content.encode('utf-8')).decode('ascii')


class APIObject:
    """Top level class for objects created from the API"""

    __slots__: Tuple[str, ...] = ('_response', '_http')

    def __init__(self, response: Dict[str, Any], _http: http) -> None:
        self._http = _http
        self._response = response

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}>'


# === User stuff ===#


class _BaseUser(APIObject):
    __slots__ = (
        'login',
        'id',
    )

    def __init__(self, response: Dict[str, Any], _http: http) -> None:
        super().__init__(response, _http)
        self._http = _http
        self.login = response.get('login')
        self.id = response.get('id')

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} id = {self.id}, login = {self.login!r}>'

    async def repos(self) -> List[Repository]:
        """List[:class:`Repository`]: Returns a list of public repositories under the user."""
        results = await self._http.get_user_repos(self)  # type: ignore
        return [Repository(data, self._http) for data in results]

    async def gists(self) -> List[Gist]:
        """List[:class:`Gist`]: Returns a list of public gists under the user."""
        results = await self._http.get_user_gists(self)  # type: ignore
        return [Gist(data, self._http) for data in results]

    async def orgs(self) -> List[Organization]:
        """List[:class:`Organization`]: Returns a list of public orgs under the user."""
        results = await self._http.get_user_orgs(self)  # type: ignore
        return [Organization(data, self._http) for data in results]

    @property
    def name(self):
        """Optional[str]: The name of the user, if available."""
        return self._response.get('login')


class User(_BaseUser):
    """Representation of a user object on Github.

    Attributes
    ----------
    login: :class:`str`
        The API name of the user.
    id: :class:`int`
        The ID of the user.
    avatar_url: :class:`str`
        The url of the user's Github avatar.
    html_url: :class:`str`
        The url of the user's Github page.
    created_at: :class:`datetime.datetime`
        The time of creation of the user.
    """

    __slots__ = (
        'login',
        'id',
        'avatar_url',
        'html_url',
        'public_repos',
        'public_gists',
        'followers',
        'following',
        'created_at',
    )

    def __init__(self, response: Dict[str, Any], _http: http) -> None:
        super().__init__(response, _http)
        tmp = self.__slots__ + _BaseUser.__slots__
        keys = {key: value for key, value in self._response.items() if key in tmp}
        for key, value in keys.items():
            if '_at' in key and value is not None:
                setattr(self, key, dt_formatter(value))
                continue
            else:
                setattr(self, key, value)
                continue

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} login: {self.login!r}, id: {self.id}, created_at: {self.created_at}>'


class PartialUser(_BaseUser):
    __slots__ = (
        'site_admin',
        'html_url',
        'avatar_url',
    ) + _BaseUser.__slots__

    def __init__(self, response: Dict[str, Any], _http: http) -> None:
        super().__init__(response, _http)
        self.site_admin: Optional[str] = response.get('site_admin')
        self.html_url: Optional[str] = response.get('html_url')
        self.avatar_url: Optional[str] = response.get('avatar_url')

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} login: {self.login!r}, id: {self.id}, site_admin: {self.site_admin}'

    async def _get_user(self) -> User:
        """Upgrades the PartialUser to a User object."""
        response = await self._http.get_user(self.login)
        return User(response, self._http)


# === Repository stuff ===#


class Repository(APIObject):
    """Representation of a repository on Github.

    Attributes
    ----------
    id: :class:`int`
        The ID of the repository in the API.
    name: :class:`str`
        The name of the repository in the API.
    owner: :class:`User`
        The owner of the repository.
    created_at: :class:`datetime.datetime`
        The time the repository was created at.
    updated_at: :class:`datetime.datetime`
        The time the repository was last updated.
    url: :class:`str`
        The API url for the repository.
    html_url: :class:`str`
        The human-url of the repository.
    archived: :class:`bool`
        Whether the repository is archived or live.
    open_issues_count: :class:`int`
        The number of the open issues on the repository.
    default_branch: :class:`str`
        The name of the default branch of the repository.
    """

    if TYPE_CHECKING:
        id: int
        name: str
        owner: str

    __slots__ = (
        'id',
        'name',
        'owner',
        'sizecreated_at',
        'url',
        'html_url',
        'archived',
        'disabled',
        'updated_at',
        'open_issues_count',
        'clone_url',
        'stargazers_count',
        'watchers_count',
        'license',
    )

    def __init__(self, response: Dict[str, Any], _http: http) -> None:
        super().__init__(response, _http)
        tmp = self.__slots__ + APIObject.__slots__
        keys = {key: value for key, value in self._response.items() if key in tmp}
        for key, value in keys.items():
            if key == 'owner':
                setattr(self, key, PartialUser(value, self._http))
                continue

            if key == 'name':
                setattr(self, key, value)
                continue

            if '_at' in key and value is not None:
                setattr(self, key, dt_formatter(value))
                continue

            if 'license' in key:
                if value is not None:
                    setattr(self, key, value.get('name'))
                    continue
                setattr(self, key, None)

            else:
                setattr(self, key, value)
                continue

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} id: {self.id}, name: {self.name!r}, owner: {self.owner!r}>'

    @property
    def is_fork(self) -> bool:
        """:class:`bool`: Whether the repository is a fork."""
        return self._response.get('fork')

    @property
    def language(self) -> str:
        """:class:`str`: Primary language of the repository."""
        return self._response.get('language')

    @property
    def open_issues(self) -> int:
        """:class:`int`: The number of open issues on the repository."""
        return self._response.get('open_issues')

    @property
    def forks(self) -> int:
        """:class:`int`: The number of forks of the repository."""
        return self._response.get('forks')

    @property
    def default_branch(self) -> str:
        """:class:`str`: The default branch of the repository."""
        return self._response.get('default_branch')

    async def delete(self) -> None:
        """Deletes the repository."""
        return await self._http.delete_repo(
            self.owner.name,  # type: ignore this shit is not my fault
            self.name,
        )  # type: ignore

    async def add_file(self, filename: str, message: str, content: str, branch: Optional[str] = None) -> None:
        """Adds a file to the repository.

        Parameters
        ----------
        filename: :class:`str` The name of the file.
        message: :class:`str` The commit message.
        content: :class:`str` The content of the file.
        branch: :class:`str` The branch to add the file to, defaults to the default branch.
        """

        if branch is None:
            branch = self.default_branch

        return await self._http.add_file(owner=self.owner.name, repo_name=self.name, filename=filename, content=content, message=message, branch=branch)  # type: ignore


class Issue(APIObject):
    """Representation of an issue on Github.

    Attributes
    ----------
    id: :class:`int`
        The ID of the issue in the API.
    title: :class:`str`
        The title of the issue in the API.
    user: :class:`User`
        The user who opened the issue.
    labels: List[:class:`str`]
        TODO: document this.
    state: :class:`str`
        The current state of the issue.
    created_at: :class:`datetime.datetime`
        The time the issue was created.
    closed_by: Optional[Union[:class:`PartialUser`, :class:`User`]]
        The user the issue was closed by, if applicable.
    """

    __slots__ = (
        'id',
        'title',
        'user',
        'labels',
        'state',
        'created_at',
        'closed_by',
    )

    def __init__(self, response: Dict[str, Any], _http: http) -> None:
        super().__init__(response, _http)
        tmp = self.__slots__ + APIObject.__slots__
        keys = {key: value for key, value in self._response.items() if key in tmp}
        for key, value in keys.items():
            if key == 'user':
                setattr(self, key, PartialUser(value, self._http))
                continue

            if key == 'labels':
                setattr(self, key, [label['name'] for label in value])
                continue

            if key == 'closed_by':
                setattr(self, key, User(value, self._http))
                continue

            else:
                setattr(self, key, value)
                continue

    def __repr__(self) -> str:
        return (
            f'<{self.__class__.__name__} id: {self.id}, title: {self.title}, user: {self.user}, created_at:'
            f' {self.created_at}, state: {self.state}>'
        )

    @property
    def updated_at(self) -> Optional[datetime]:
        """Optional[:class:`datetime.datetime`]: The time the issue was last updated, if applicable."""
        return dt_formatter(self._response.get('updated_at'))

    @property
    def html_url(self) -> str:
        """:class:`str`: The human-friendly url of the issue."""
        return self._response.get('html_url')


# === Gist stuff ===#


class File:
    """A wrapper around files and in-memory file-like objects.

    Parameters
    ----------
    fp: Union[:class:`str`, :class:`io.StringIO`, :class:`io.BytesIO`]
        The filepath or StringIO representing a file to upload.
        If providing a StringIO instance, a filename shuold also be provided to the file.
    filename: :class:`str`
        An override to the file's name, encouraged to provide this if using a StringIO instance.
    """

    def __init__(self, fp: Union[str, io.StringIO, io.BytesIO], filename: str = 'DefaultFilename.txt') -> None:
        self.fp = fp
        self.filename = filename

    def read(self) -> str:
        if isinstance(self.fp, str):
            if os.path.exists(self.fp):
                with open(self.fp) as fp:
                    data = fp.read()
                return data
            return self.fp
        elif isinstance(self.fp, io.BytesIO):
            return self.fp.read().decode('utf-8')
        elif isinstance(self.fp, io.StringIO):  # type: ignore
            return self.fp.getvalue()

        raise TypeError(f'Expected str, io.StringIO, or io.BytesIO, got {type(self.fp)}')


class Gist(APIObject):
    """Representation of a gist on Github.

    Attributes
    ----------
    id: :class:`int`
        The ID of the gist in the API.
    html_url: :class:`str`
        The human-friendly url of the gist.
    files: List[:class:`File`]
        A list of the files in the gist, can be an empty list.
    public: :class:`bool`
        Whether the gist is public.
    owner: Union[:class:`PartialUser`, :class:`User`]
        The owner of the gist.
    created_at: :class:`datetime.datetime`
        The time the gist was created at.
    """

    __slots__ = (
        'id',
        'html_url',
        'node_id',
        'files',
        'public',
        'owner',
        'created_at',
        'truncated',
    )

    def __init__(self, response: Dict[str, Any], _http: http) -> None:
        super().__init__(response, _http)
        tmp = self.__slots__ + APIObject.__slots__
        keys = {key: value for key, value in self._response.items() if key in tmp}
        for key, value in keys.items():
            if key == 'owner':
                setattr(self, key, PartialUser(value, self._http))
                continue
            if key == 'created_at':
                setattr(self, key, dt_formatter(value))
                continue
            else:
                setattr(self, key, value)

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} id: {self.id}, owner: {self.owner}, created_at: {self.created_at}>'

    @property
    def updated_at(self) -> Optional[datetime]:
        """Optional[:class:`datetime.datetime`]: The time the gist was last updated, if applicable."""
        return dt_formatter(self._response.get('updated_at'))

    @property
    def comments(self) -> str:
        """TODO: document this."""
        return self._response.get('comments')

    @property
    def discussion(self) -> str:
        """TODO: document this."""
        return self._response.get('discussion')

    @property
    def raw(self) -> Dict[str, Any]:
        """TODO: document this."""
        return self._response

    @property
    def url(self) -> str:
        return self._response.get('html_url')

    async def delete(self):
        """Delete the gist."""
        await self._http.delete_gist(self.id)


# === Organization stuff ===#


class Organization(APIObject):
    """Representation of an organization in the API.

    Attributes
    ----------
    login: :class:`str`
        TODO: document this
    id: :class:`int`
        The ID of the organization in the API.
    is_verified: :class:`bool`
        Whether or not the organization is verified.
    created_at: :class:`datetime.datetime`
        The time the organization was created at.
    avatar_url: :class:`str`
        The url of the organization's avatar.
    """

    __slots__ = (
        'login',
        'id',
        'is_verified',
        'public_repos',
        'public_gists',
        'followers',
        'following',
        'created_at',
        'avatar_url',
    )

    def __init__(self, response: Dict[str, Any], _http: http) -> None:
        super().__init__(response, _http)
        tmp = self.__slots__ + APIObject.__slots__
        keys = {key: value for key, value in self._response.items() if key in tmp}
        for key, value in keys.items():
            if key == 'login':
                setattr(self, key, value)
                continue
            if '_at' in key and value is not None:
                setattr(self, key, dt_formatter(value))
                continue

            else:
                setattr(self, key, value)
                continue

    def __repr__(self):
        return (
            f'<{self.__class__.__name__} login: {self.login!r}, id: {self.id}, is_verified: {self.is_verified},'
            f' public_repos: {self.public_repos}, public_gists: {self.public_gists}, created_at: {self.created_at}>'
        )

    @property
    def description(self):
        """:class:`str`: The description of the organization."""
        return self._response.get('description')

    @property
    def html_url(self):
        """:class:`str`: The human-friendly url of the organization."""
        return self._response.get('html_url')
