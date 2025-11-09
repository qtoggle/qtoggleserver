import asyncio
import inspect
import logging

from collections.abc import Callable
from functools import reduce


__all__ = ["Debouncer"]

logger = logging.getLogger(__name__)


class Debouncer:
    """
    Utility to debounce calls to a function.

    Debounced calls are queued and after a specified delay, the queued arguments are reduced using a reducer function
    and the target function is called with the reduced arguments.

    Given `args` and `kwargs` will be used as the initial arguments for the function call.
    """

    def __init__(
        self,
        func: Callable,
        args: tuple | None = None,
        kwargs: dict | None = None,
        args_reducer: Callable | None = None,
        kwargs_reducer: Callable | None = None,
        delay: float = 0,
    ) -> None:
        self._func: Callable = func
        self._args_reducer: Callable | None = args_reducer
        self._kwargs_reducer: Callable | None = kwargs_reducer
        self._args: tuple = args or ()
        self._kwargs: dict = kwargs or {}
        self._queue: list[tuple] = []
        self._delay: float = delay
        self._task: asyncio.Task | None = None

    def call(self, *args, **kwargs) -> None:
        # Push call details to queue
        self._queue.append((args, kwargs))
        if self._task is None:
            self._task = asyncio.create_task(self._run())

    async def _run(self) -> None:
        await asyncio.sleep(self._delay)

        args = self._args
        if self._args_reducer:
            args += reduce(self._args_reducer, (q[0] for q in self._queue))

        kwargs = self._kwargs
        if self._kwargs_reducer:
            kwargs |= reduce(self._kwargs_reducer, (q[1] for q in self._queue))

        try:
            if inspect.iscoroutinefunction(self._func):
                await self._func(*args, **kwargs)
            else:
                self._func(*args, **kwargs)
        except Exception:
            logger.error("error while executing debounced function: %s", self._func, exc_info=True)

        self._queue.clear()
        self._task = None

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        self._queue.clear()
        self._task = None
