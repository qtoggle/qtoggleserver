import asyncio
import logging

from collections.abc import Callable

from qtoggleserver.core.typing import PortValue


logger = logging.getLogger(__name__)


class SequenceError(Exception):
    pass


class Sequence:
    def __init__(
        self, values: list[PortValue], delays: list[int], repeat: int, callback: Callable, finish_callback: Callable
    ) -> None:
        self._values: list[PortValue] = values
        self._delays: list[int] = delays
        self._repeat: int = repeat

        self._callback: Callable = callback
        self._finish_callback: Callable = finish_callback
        self._counter: int = 0
        self._loop_task: asyncio.Task | None = None

    def start(self) -> None:
        if self._loop_task:
            raise SequenceError("Loop task already started")

        self._loop_task = asyncio.create_task(self._loop())

    async def cancel(self) -> None:
        if self._loop_task:
            self._loop_task.cancel()
            await self._loop_task

    async def _loop(self) -> None:
        for i, value in enumerate(self._values):
            try:
                try:
                    self._callback(value)
                except Exception as e:
                    logger.error("sequence callback failed: %s", e, exc_info=True)

                if i < len(self._values) - 1:
                    await asyncio.sleep(self._delays[i] / 1000.0)
                else:
                    if self._repeat > 0 and self._counter >= self._repeat - 1:
                        await self._finish_callback()

                        return

                    self._counter += 1
                    await asyncio.sleep(self._delays[i] / 1000.0)

                    self._loop_task = asyncio.create_task(self._loop())
                    return
            except asyncio.CancelledError:
                logger.debug("sequence task cancelled")
                break

        self._loop_task = None
