
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
        self._counter = 0
        self._loop_task = None

    def start(self):
        if self._loop_task:
            raise Exception('loop task already started')

        self._loop_task = asyncio.create_task(self._loop())

    async def cancel(self):
        if self._loop_task:
            self._loop_task.cancel()
            await self._loop_task

    async def _loop(self):
        for i, value in enumerate(self._values):
            try:
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

                    self._loop_task = asyncio.create_task(self._loop())
                    return

            except asyncio.CancelledError:
                logger.debug('sequence loop cancelled')
                break

        self._loop_task = None
