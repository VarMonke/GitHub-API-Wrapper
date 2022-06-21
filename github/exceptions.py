# == exceptions.py ==#

import datetime
from typing import Optional, Tuple

from aiohttp import ClientResponse

__all__: Tuple[str, ...] = (
    'APIError',
    'AlreadyStarted',
    'ClientException',
    'ClientResponse',
    'GistNotFound',
    'HTTPException',
    'InvalidAuthCombination',
    'InvalidToken',
    'IssueNotFound',
    'LoginFailure',
    'MissingPermissions',
    'NoAuthProvided',
    'NotStarted',
    'OrganizationNotFound',
    'Ratelimited',
    'RepositoryAlreadyExists',
    'RepositoryNotFound',
    'ResourceAlreadyExists',
    'ResourceNotFound',
    'UserNotFound',
    'WillExceedRatelimit',
)


class APIError(Exception):
    """Base level exceptions raised by errors related to any API request or call."""

    pass


class HTTPException(Exception):
    """Base level exceptions raised by errors related to HTTP requests."""

    pass


class ClientException(Exception):
    """Base level exceptions raised by errors related to the client."""

    pass


class ResourceNotFound(Exception):
    """Base level exceptions raised when a resource is not found."""

    pass


class ResourceAlreadyExists(Exception):
    """Base level exceptions raised when a resource already exists."""

    pass


class Ratelimited(APIError):
    """Raised when the ratelimit from Github is reached or exceeded."""

    def __init__(self, reset_time: datetime.datetime):
        formatted = reset_time.strftime(r"%H:%M:%S %A, %d %b")
        msg = f"We're being ratelimited, wait until {formatted}.\nAuthentication raises the ratelimit."
        super().__init__(msg)


class WillExceedRatelimit(APIError):
    """Raised when the library predicts the call will exceed the ratelimit, will abort the call by default."""

    def __init__(self, response: ClientResponse, count: int):
        msg = 'Performing this action will exceed the ratelimit, aborting.\n{} remaining available calls, calls to make: {}.'
        msg = msg.format(response.headers['X-RateLimit-Remaining'], count)
        super().__init__(msg)


class NoAuthProvided(ClientException):
    """Raised when no authentication is provided."""

    def __init__(self):
        msg = 'This action required autentication. Pass username and token kwargs to your client instance.'
        super().__init__(msg)


class InvalidToken(ClientException):
    """Raised when the token provided is invalid."""

    def __init__(self):
        msg = 'The token provided is invalid.'
        super().__init__(msg)


class InvalidAuthCombination(ClientException):
    """Raised when the username and token are both provided."""

    def __init__(self, msg: str):
        # msg = 'The username and token cannot be used together.'
        super().__init__(msg)


class LoginFailure(ClientException):
    """Raised when the login attempt fails."""

    def __init__(self):
        msg = 'The login attempt failed. Provide valid credentials.'
        super().__init__(msg)


class NotStarted(ClientException):
    """Raised when the client is not started."""

    def __init__(self):
        msg = 'The client is not started. Run Github.GHClient() to start.'
        super().__init__(msg)


class AlreadyStarted(ClientException):
    """Raised when the client is already started."""

    def __init__(self):
        msg = 'The client is already started.'
        super().__init__(msg)


class MissingPermissions(APIError):
    def __init__(self):
        msg = 'You do not have permissions to perform this action.'
        super().__init__(msg)


class UserNotFound(ResourceNotFound):
    def __init__(self):
        msg = 'The requested user was not found.'
        super().__init__(msg)


class RepositoryNotFound(ResourceNotFound):
    def __init__(self):
        msg = 'The requested repository is either private or does not exist.'
        super().__init__(msg)


class IssueNotFound(ResourceNotFound):
    def __init__(self):
        msg = 'The requested issue was not found.'
        super().__init__(msg)


class OrganizationNotFound(ResourceNotFound):
    def __init__(self):
        msg = 'The requested organization was not found.'
        super().__init__(msg)


class GistNotFound(ResourceNotFound):
    def __init__(self):
        msg = 'The requested gist was not found.'
        super().__init__(msg)


class RepositoryAlreadyExists(ResourceAlreadyExists):
    def __init__(self):
        msg = 'The requested repository already exists.'
        super().__init__(msg)


class FileAlreadyExists(ResourceAlreadyExists):
    def __init__(self, msg: Optional[str] = None):
        if msg is None:
            msg = 'The requested file already exists.'
        super().__init__(msg)
