import asyncio
import inspect
import logging

from collections.abc import Callable
from typing import Any, Awaitable, Coroutine


logger = logging.getLogger(__name__)


class Timer:
    def __init__(self, timeout: int, callback: Callable, *args, **kwargs) -> None:
        self._timeout: int = timeout
        self._callback: Callable = callback
        self._args: tuple = args
        self._kwargs: dict = kwargs
        self._task: asyncio.Task | None = None
        self._task = asyncio.ensure_future(self.run())

    def cancel(self) -> None:
        if self._task is None:
            raise Exception("Task is not running")

        self._task.cancel()

    async def wait(self) -> None:
        if self._task is None:
            raise Exception("Task is not running")

        await self._task

    async def run(self) -> None:
        try:
            await asyncio.sleep(self._timeout)
        except asyncio.CancelledError:
            pass
        else:
            result = self._callback(*self._args, **self._kwargs)
            if inspect.isawaitable(result):
                await result
        finally:
            self._task = None


async def await_later(delay: float, aw: Awaitable) -> None:
    await asyncio.sleep(delay)
    await aw


def fire_and_forget(coro: Coroutine[Any, Any, Any]) -> None:
    """Schedule coro as a background task, log any exception and consume it."""
    task = asyncio.create_task(coro)

    def _on_done(t: asyncio.Task) -> None:
        try:
            t.result()
        except Exception as e:
            logger.error("Error while handling task: %s", e, exc_info=True)
        except asyncio.CancelledError:
            # Task was cancelled while we were handling it - nothing to do.
            pass

    task.add_done_callback(_on_done)
