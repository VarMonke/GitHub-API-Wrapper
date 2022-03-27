#== objects.py ==#

from datetime import datetime
import aiohttp

__all__ = (
    'APIOBJECT',
)

def dt_formatter(time_str):
    if time_str is not None:
        return datetime.strptime(time_str, r"%Y-%m-%dT%H:%M:%SZ")
    return None

def repr_dt(time_str):
    return time_str.strftime(r'%d-%m-%Y, %H:%M:%S')

class APIOBJECT:
    __slots__ = (
        '_response',
        'session'
    )

    def __init__(self, response: dict[str, str | int], session: aiohttp.ClientSession) -> None:
        self._response = response
        self.session = session

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}>'