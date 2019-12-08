
import asyncio
import logging


logger = logging.getLogger(__name__)


class Sequence:
    def __init__(self, values, delays, repeat, callback, finish_callback):
        self._values = values
        self._delays = delays
        self._repeat = repeat

        self._callback = callback
        self._finish_callback = finish_callback
        self._cancelled = False
        self._counter = 0

    def start(self):
        asyncio.create_task(self._loop())

    def cancel(self):
        self._cancelled = True

    async def _loop(self):
        for i, value in enumerate(self._values):
            if self._cancelled:
                break

            try:
                self._callback(value)

            except Exception as e:
                logger.error('sequence callback failed: %s', e, exc_info=True)

            if i < len(self._values) - 1:
                await asyncio.sleep(self._delays[i] / 1000.0)

            else:
                if self._repeat > 0 and self._counter >= self._repeat - 1:
                    await self._finish_callback()

                    return

                self._counter += 1
                await asyncio.sleep(self._delays[i] / 1000.0)

                asyncio.create_task(self._loop())
