
import functools
import inspect
import logging

from typing import Callable, List


logger = logging.getLogger(__name__)

_init_hooks: List[Callable] = []
_cleanup_hooks: List[Callable] = []


def add_init_hook(hook: Callable, *args, **kwargs) -> None:
    _init_hooks.append(functools.partial(hook, *args, **kwargs))


def add_cleanup_hook(hook: Callable, *args, **kwargs) -> None:
    _cleanup_hooks.append(functools.partial(hook, *args, **kwargs))


async def init() -> None:
    for hook in _init_hooks:
        try:
            result = hook()
            if inspect.isawaitable(result):
                await result

        except Exception as e:
            logger.error('init hook failed: %s', e, exc_info=True)


async def cleanup() -> None:
    for hook in _cleanup_hooks:
        try:
            result = hook()
            if inspect.isawaitable(result):
                await result

        except Exception as e:
            logger.error('cleanup hook failed: %s', e, exc_info=True)
