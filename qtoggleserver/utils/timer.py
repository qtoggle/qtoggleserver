import asyncio
import inspect
import logging

from collections.abc import Callable


__all__ = ["Timer"]

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
