
import collections.abc
import time

from typing import Any, Dict, Iterable, Set


class TimedSet(collections.abc.MutableSet):
    def __init__(self, timeout: float) -> None:
        self._timeout: float = timeout
        self._times: Dict[Any, float] = {}
        self._set: Set[Any] = set()

    def add(self, x: Any) -> None:
        self._set.add(x)
        self._times[x] = time.time()

    def discard(self, x: Any) -> None:
        self._set.discard(x)

    def __contains__(self, x: Any) -> bool:
        if not self._set.__contains__(x):
            return False

        if time.time() - self._times[x] > self._timeout:
            del self._times[x]
            self._set.discard(x)
            return False

        return True

    def __len__(self) -> int:
        return self._set.__len__()

    def __iter__(self) -> Iterable[Any]:
        return self._set.__iter__()
