#== exceptions.py ==#

import datetime

__all__ = (
    'APIError',
    'Ratelimited',
    'WillExceedRatelimit',
    'UserNotFound',
    'OrganizationNotFound',
    'RepositoryNotFound',
    'ObjectNotFound',
    'IssueNotFound',
    'NoAuthProvided',
    'InvalidAuthCombination',
    'InvalidToken',
    'AlreadyStarted',
    'NotStarted'
)

class APIError(Exception):
    """Base level exceptions raised by errors related to any API request or call."""
    pass

class Ratelimited(APIError):
    """Raised when the ratelimit from Github is reached or exceeded."""
    def __init__(self, reset_time: datetime.datetime):
        formatted = reset_time.strftime(r"%H:%M:%S %A, %d %b")
        msg = "We're being ratelimited, wait until {}.\nAuthentication raises the ratelimit.".format(formatted)
        super().__init__(msg)

class WillExceedRatelimit(APIError):
    """Raised when the library predicts the call will exceed the ratelimit, will abort the call by default."""
    def __init__(self, response, count):
        msg = 'Performing this action will exceed the ratelimit, aborting.\n{} remaining available calls, calls to make: {}.'
        msg = msg.format(response.header['X-RateLimit-Remaining'], count)
        super().__init__(msg)

class UserNotFound(APIError):
    def __init__(self):
        msg = 'User not found.'
        super().__init__(msg)

class OrganizationNotFound(APIError):
    def __init__(self):
        msg = 'Organization not found.'
        super().__init__(msg)

class RepositoryNotFound(APIError):
    def __init__(self):
        msg = 'Repository not found.'
        super().__init__(msg)

class ObjectNotFound(APIError):
    def __init__(self):
        msg = 'The requested object was not found, ensure spelling is correct before proceeding.'
        super().__init__(msg)

class IssueNotFound(APIError):
    def __init__(self):
        msg = 'The requested issue was not found, ensure spelling is correct before proceeding.'
        super().__init__(msg)

class NoAuthProvided(APIError):
    """Raised when no proper authorization or invalid authorization is given to the client"""
    def __init__(self):
        msg = 'Without authorization, this client doesn\'t have it\'s own repository.'
        super().__init__(msg)

class InvalidAuthCombination(APIError):
    def __init__(self):
        msg = 'You must provide both a username and a user token or neither.'
        super().__init__(msg)

class InvalidToken(APIError):
    def __init__(self) -> None:
        msg = "The token you provided was invalid, please check again."
        super().__init__(msg)

class AlreadyStarted(APIError):
    """Raised when start is called multiple times."""
    def __init__(self):
        msg = 'This client has already been started and cannot be started again.'
        super().__init__(msg)

class NotStarted(APIError):
    """Raised when a call is made before start is called."""
    def __init__(self):
        msg = 'You must call `await <Github_instance>.start()` before making this call.'
        super().__init__(msg)

class RepositoryAlreadyExists(APIError):
    """Raised when a repository already exists."""
    def __init__(self):
        msg = 'The repository you are trying to create already exists.'
        super().__init__(msg)