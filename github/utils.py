from __future__ import annotations

from base64 import b64encode
from typing import TYPE_CHECKING, Optional

from .errors import HTTPError

if TYPE_CHECKING:
    from datetime import datetime, timedelta

    from aiohttp import ClientResponse

    from .errors import BaseHTTPError

__all__ = ("human_readable_time_until", "str_to_datetime", "repr_dt", "bytes_to_b64", "error_from_request")


def human_readable_time_until(td: timedelta, /) -> str:
    seconds = int(td.total_seconds())
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    return f"{hours} hours, {minutes} minues, {seconds} seconds"


def str_to_datetime(time: Optional[str], /) -> Optional[datetime]:
    return None if time is None else datetime.strptime(time, r"%Y-%m-%dT%H:%M:%SZ")


def repr_dt(time: datetime, /) -> str:
    return time.strftime(r"%d-%m-%Y, %H:%M:%S")


def bytes_to_b64(content: str, /) -> str:
    return b64encode(content.encode("utf-8")).decode("ascii")


def error_from_request(request: ClientResponse, /) -> BaseHTTPError:
    # TODO: make errors specific
    return HTTPError(request)
