from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from .utils import human_readable_time_until

if TYPE_CHECKING:
    from aiohttp import ClientResponse


class GitHubError(Exception):
    """The base class for all errors raised in this library."""


class BaseHTTPError(GitHubError):
    """The base class for all HTTP related errors in this library."""


class HTTPError(BaseHTTPError):
    """Raised when an HTTP request doesn't respond with a successfull code."""

    def __init__(self, response: ClientResponse, /) -> None:
        self.method = response.method
        self.code = response.status
        self.url = response.url
        self._response = response

    def __str__(self) -> str:
        return (
            f"An HTTP error with the code {self.code} has occured while trying to do a {self.method} request to the URL"
            f" {self.url}"
        )


class RatelimitReached(GitHubError):
    """Raised when a ratelimit is reached."""

    def __init__(self, reset_time: datetime, /) -> None:
        self.reset_time = reset_time

    def __str__(self) -> str:
        return (
            "The ratelimit has been reached. You can try again in"
            f" {human_readable_time_until(datetime.now(timezone.utc) - self.reset_time)}"
        )
