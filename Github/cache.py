#== cache.py ==#

from __future__ import annotations

__all__ = (
    'UserCache',
    'RepoCache',
    'OrgCache',
)

from collections import deque

from .objects import APIObject, User, Repository, Organization


class _BaseCache(dict):
    """This is a rough implementation of an LRU Cache using a deque and a dict."""
    _max_size: int
    _lru_keys: deque
    def __init__(self, max_size: int, *args):
        self._max_size = max(min(max_size, 15), 0) # bounding max_size to 15 for now
        self._lru_keys = deque(maxlen=self._max_size)
        super().__init__(args)
    
    def __getitem__(self, __k: str) -> APIObject:
        target = self._lru_keys.pop(self._lru_keys.index(__k))
        self._lru_keys.appendleft(target)
        return super().__getitem__(__k)

    def __setitem__(self, __k: str, __v: APIObject) -> None:
        if len(self) == self._max_size:
            to_pop = self._lru_keys.pop(-1)
            del self[to_pop]
        self._lru_keys.appendleft(__k)
        return super().__setitem__(__k, __v)

    def update(self, *args, **kwargs) -> None:
        for key, value in dict(*args, **kwargs).iteritems():
            self[key] = value

class UserCache(_BaseCache):
    """This adjusts the typehints to reflect User objects"""
    def __getitem__(self, __k: str) -> 'User':
        target = self._lru_keys.pop(self._lru_keys.index(__k))
        self._lru_keys.appendleft(target)
        return super().__getitem__(__k)

    def __setitem__(self, __k: str, __v: 'User') -> None:
        if len(self) == self._max_size:
            to_pop = self._lru_keys.pop(-1)
            del self[to_pop]
        self._lru_keys.appendleft(__k)
        return super().__setitem__(__k, __v)

    def update(self, *args, **kwargs) -> None:
        for key, value in dict(*args, **kwargs).iteritems():
            self[key] = value

class RepoCache(_BaseCache):
    """This adjusts the typehints to reflect Repo objects"""
    def __getitem__(self, __k: str) -> 'Repository':
        target = self._lru_keys.pop(self._lru_keys.index(__k))
        self._lru_keys.appendleft(target)
        return super().__getitem__(__k)

    def __setitem__(self, __k: str, __v: 'Repository') -> None:
        if len(self) == self._max_size:
            to_pop = self._lru_keys.pop(-1)
            del self[to_pop]
        self._lru_keys.appendleft(__k)
        return super().__setitem__(__k, __v)

    def update(self, *args, **kwargs) -> None:
        for key, value in dict(*args, **kwargs).iteritems():
            self[key] = value

class OrgCache(_BaseCache):
    def __getitem__(self, __k: str) -> 'Organization':
        target = self._lru_keys.pop(self._lru_keys.index(__k))
        self._lru_keys.appendleft(target)
        return super().__getitem__(__k)

    def __setitem__(self, __k: str, __v: 'Organization') -> None:
        if len(self) == self._max_size:
            to_pop = self._lru_keys.pop(-1)
            del self[to_pop]
        self._lru_keys.appendleft(__k)
        return super().__setitem__(__k, __v)

    def update(self, *args, **kwargs) -> None:
        for key, value in dict(*args, **kwargs).iteritems():
            self[key] = value
