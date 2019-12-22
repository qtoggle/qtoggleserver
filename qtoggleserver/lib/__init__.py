
import functools
import inspect
import logging


logger = logging.getLogger(__name__)

_init_hooks = []
_cleanup_hooks = []


def add_init_hook(hook, *args, **kwargs):
    _init_hooks.append(functools.partial(hook, *args, **kwargs))


def add_cleanup_hook(hook, *args, **kwargs):
    _cleanup_hooks.append(functools.partial(hook, *args, **kwargs))


async def init():
    for hook in _init_hooks:
        try:
            result = hook()
            if inspect.isawaitable(result):
                await result

        except Exception as e:
            logger.error('init hook failed: %s', e, exc_info=True)


async def cleanup():
    for hook in _cleanup_hooks:
        try:
            result = hook()
            if inspect.isawaitable(result):
                await result

        except Exception as e:
            logger.error('cleanup hook failed: %s', e, exc_info=True)
