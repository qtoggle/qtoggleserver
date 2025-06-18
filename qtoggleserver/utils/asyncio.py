import abc
import asyncio
import inspect
import queue
import sys
import threading
import weakref

from collections.abc import Awaitable, Callable, Coroutine
from typing import Any


class ParallelCaller:
    def __init__(self, parallel: int = 1, max_queued: int = 0) -> None:
        self._queue: asyncio.Queue = asyncio.Queue(max_queued)
        self._loop_tasks: list[asyncio.Task] = []

        # Start loop tasks
        for i in range(parallel):
            self._loop_tasks.append(asyncio.create_task(self._loop(i)))

    async def call(self, func: Callable, *args, is_async: bool | None = None, **kwargs) -> Any:
        # Push call details to queue
        when_ready = asyncio.Condition()
        result = {"ret": None, "exc_info": (None, None, None)}

        # Allow QueueFull exceptions to be propagated to caller
        self._queue.put_nowait((func, is_async, args, kwargs, when_ready, result))

        # Wait for call to be ready
        async with when_ready:
            await when_ready.wait()

        # If an exception was raised, re-raise it
        assert result["exc_info"]
        typ, val, tb = result["exc_info"]
        if typ:
            raise val

        return result["ret"]

    async def _loop(self, index: int) -> None:
        try:
            while True:
                func, is_async, args, kwargs, when_ready, result = await self._queue.get()

                if is_async is None:
                    is_async = inspect.iscoroutinefunction(func)

                try:
                    if is_async:
                        result["ret"] = await func(*args, **kwargs)
                    else:
                        result["ret"] = func(*args, **kwargs)
                except Exception:
                    result["exc_info"] = sys.exc_info()

                async with when_ready:
                    when_ready.notify_all()
        except asyncio.CancelledError:
            pass

    async def stop(self) -> None:
        current_task = asyncio.current_task()

        for task in self._loop_tasks:
            if task is not current_task:
                task.cancel()

        await asyncio.gather(*[t for t in self._loop_tasks if t is not current_task])


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


class RunnerBusy(Exception):
    pass


class ThreadedRunner(threading.Thread, metaclass=abc.ABCMeta):
    QUEUE_TIMEOUT = 1

    def __init__(self, queue_size: int | None = None) -> None:
        self._running: bool = False
        self._loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
        self._queue: queue.Queue = queue.Queue(queue_size or 0)
        self._stopped_future: asyncio.Future = self._loop.create_future()

        super().__init__()

    def run(self) -> None:
        while self._running:
            try:
                func, callback = self._queue.get(timeout=self.QUEUE_TIMEOUT)
            except queue.Empty:
                continue

            try:
                result = func()
            except Exception as e:
                self._loop.call_soon_threadsafe(callback, None, e)
            else:
                self._loop.call_soon_threadsafe(callback, result, None)

        self._loop.call_soon_threadsafe(self._stopped_future.set_result, None)

    def schedule_func(self, func: Callable, callback: Callable) -> None:
        try:
            self._queue.put_nowait((func, callback))
        except queue.Full:
            raise RunnerBusy() from None

    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        self._running = True
        super().start()

    async def stop(self) -> None:
        self._running = False

        await self._stopped_future


async def await_later(delay: float, aw: Awaitable) -> None:
    await asyncio.sleep(delay)
    await aw


def fire_and_forget(coro: Coroutine[Any, Any, Any]) -> None:
    task = asyncio.create_task(coro)
    weakref.finalize(task, task.get_coro().close)
