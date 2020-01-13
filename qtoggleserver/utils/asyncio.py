
import asyncio

from typing import Callable


async def await_later(delay: float, coroutine: Callable, *args, loop: asyncio.AbstractEventLoop = None) -> None:
    await asyncio.sleep(delay, loop=loop)
    await coroutine(*args)
