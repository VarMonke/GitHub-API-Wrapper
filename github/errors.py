from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aiohttp import ClientResponse


class GitHubError(Exception):
    """The base class for all errors raised in this library."""


class HTTPError(GitHubError):
    def __new__(self, response: ClientResponse) -> HTTPError:

        # TODO: make custom error classes
        return self.__class__(response)

    def __init__(self, response: ClientResponse, /):
        self.method = response.method
        self.code = response.status
        self.url = response.url
        self._response = response

    def __str__(self):
        return (
            f"An HTTP error with the code {self.code} has occured while trying to do a {self.method} request to the URL"
            f" {self.url}"
        )
