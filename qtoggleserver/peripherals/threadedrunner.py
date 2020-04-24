
from __future__ import annotations

import abc
import asyncio
import queue
import threading

from typing import Callable, Optional


class RunnerBusy(Exception):
    pass


class ThreadedRunner(threading.Thread, metaclass=abc.ABCMeta):
    QUEUE_TIMEOUT = 1

    def __init__(self, queue_size: Optional[int] = None) -> None:
        self._running: bool = False
        self._loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
        self._queue: queue.Queue = queue.Queue(queue_size or 0)
        self._queue_size: int = queue_size
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
