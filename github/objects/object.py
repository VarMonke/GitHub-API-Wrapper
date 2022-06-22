from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from ..internals import HTTPClient


class Object:
    __slots__ = ("_response", "_http")

    def __init__(self, response: Dict[str, Any], http: HTTPClient) -> None:
        self._http = http
        self._response = response

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"
