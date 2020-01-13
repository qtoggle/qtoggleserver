
import asyncio
import sys

from typing import Any, Callable


def load_attr(attr_path: str) -> Any:
    m, attr = attr_path.rsplit('.', 1)

    try:
        __import__(m)
        mod = sys.modules[m]

    except ImportError as e:
        raise Exception(f'Error importing {attr_path}: {e}') from e

    try:
        attr = getattr(mod, attr)

    except AttributeError as e:
        raise Exception(f'Error importing {attr_path}: {e}') from e

    return attr


async def await_later(delay: float, coroutine: Callable, *args, loop: asyncio.AbstractEventLoop = None) -> None:
    await asyncio.sleep(delay, loop=loop)
    await coroutine(*args)
