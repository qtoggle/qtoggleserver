import inspect

from collections.abc import Callable

from cachetools import TTLCache, cached
from cachetools_async import cached as async_cached


DEFAULT_MAXSIZE = 1024
DEFAULT_TTL = 600


def ttl_cached(*, maxsize: int = DEFAULT_MAXSIZE, ttl: int = DEFAULT_TTL) -> Callable:
    """
    Decorator factory that caches function results using cachetools.TTLCache.

    Usage:
        @ttl_cached()  # uses defaults
        def f(...):
            ...

        @ttl_cached(maxsize=2048, ttl=300)
        def g(...):
            ...

        @ttl_cached(cache=my_cache)
        def h(...):
            ...

    Works with both sync and async functions. For sync functions it delegates to
    `cachetools.cached`. For async functions it provides an async wrapper that
    stores the awaited result in the TTLCache.
    """
    cache = TTLCache(maxsize=maxsize, ttl=ttl)

    def decorator(func: Callable) -> Callable:
        # Async coroutine function: provide an async wrapper that awaits the
        # underlying function and caches the result in the TTLCache.
        if inspect.iscoroutinefunction(func):
            return async_cached(cache)(func)
        else:
            return cached(cache)(func)

    return decorator
