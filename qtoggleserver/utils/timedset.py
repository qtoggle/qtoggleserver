
import collections.abc
import time


class TimedSet(collections.abc.MutableSet):
    def __init__(self, timeout):
        self._timeout = timeout
        self._times = {}
        self._set = set()

    def add(self, x):
        self._set.add(x)
        self._times[x] = time.time()

    def discard(self, x):
        self._set.discard(x)

    def __contains__(self, x):
        if not self._set.__contains__(x):
            return False

        if time.time() - self._times[x] > self._timeout:
            del self._times[x]
            self._set.discard(x)
            return False

        return True

    def __len__(self):
        return self._set.__len__()

    def __iter__(self):
        return self._set.__iter__()
