# == cache.py ==#

from __future__ import annotations

from collections import deque
from typing import Any, Deque, Dict, Tuple, TypeVar

__all__: Tuple[str, ...] = ('ObjectCache',)


K = TypeVar('K')
V = TypeVar('V')


class _BaseCache(Dict[K, V]):
    """This is a rough implementation of an LRU Cache using a deque and a dict."""

    __slots__: Tuple[str, ...] = ('_max_size', '_lru_keys')

    def __init__(self, max_size: int, *args: Any) -> None:
        self._max_size: int = max(min(max_size, 30), 0)  # bounding max_size to 15 for now
        self._lru_keys: Deque[K] = deque(maxlen=self._max_size)
        super().__init__(*args)

    def __getitem__(self, __k: K) -> V:
        index = self._lru_keys.index(__k)
        target = self._lru_keys[index]
        del self._lru_keys[index]

        self._lru_keys.appendleft(target)
        return super().__getitem__(__k)

    def __setitem__(self, __k: K, __v: V) -> None:
        if len(self) == self._max_size:
            self.__delitem__(self._lru_keys.pop())

        self._lru_keys.appendleft(__k)
        return super().__setitem__(__k, __v)

    def update(self, **kwargs: Any) -> None:
        for key, value in dict(**kwargs).items():
            key: K
            value: V

            self.__setitem__(key, value)


class ObjectCache(_BaseCache[K, V]):
    """This adjusts the typehints to reflect Github objects."""

    def __getitem__(self, __k: K) -> V:
        index = self._lru_keys.index(__k)
        target = self._lru_keys[index]
        self._lru_keys.appendleft(target)
        return super().__getitem__(__k)

    def __setitem__(self, __k: K, __v: V) -> None:
        if self.__len__() == self._max_size:
            self.__delitem__(self._lru_keys.pop())

        self._lru_keys.appendleft(__k)
        return super().__setitem__(__k, __v)

    def update(self, **kwargs: Any) -> None:
        for key, value in dict(**kwargs).items():
            key: K
            value: V

            self.__setitem__(key, value)
