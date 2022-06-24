from __future__ import annotations

__all__ = ("Object",)

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..internals import HTTPClient


class Object:
    __slots__ = ("__http",)

    def __init__(self, *, http: HTTPClient) -> None:
        self.__http = http

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"
