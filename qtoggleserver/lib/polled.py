
import abc
import asyncio
import copy
import logging

from typing import cast, Optional

from qtoggleserver.peripherals import Peripheral, PeripheralPort


READ_INTERVAL_ATTRDEF = {
    'display_name': 'Read Interval',
    'description': 'How often to read peripheral data (set to 0 to disable reading).',
    'type': 'number',
    'modifiable': True,
    'integer': True
}


logger = logging.getLogger(__name__)


class PolledPeripheral(Peripheral, metaclass=abc.ABCMeta):
    DEFAULT_POLL_INTERVAL = 1800
    RETRY_POLL_INTERVAL = 60

    def __init__(self, **kwargs) -> None:
        self._polling: bool = False
        self._poll_stopped: bool = False
        self._poll_task: Optional[asyncio.Task] = None
        self._poll_interval: int = self.DEFAULT_POLL_INTERVAL
        self._poll_error: Optional[Exception] = None

        super().__init__(**kwargs)

    async def _poll_loop(self) -> None:
        self.debug('polling started')
        self._polling = True

        while self._polling:
            try:
                if self._poll_interval == 0:
                    await asyncio.sleep(1)
                    continue

                try:
                    await self.poll()

                except Exception as e:
                    retry_poll_interval = min(self.RETRY_POLL_INTERVAL, self._poll_interval)
                    self.error('polling failed (retrying in %s seconds): %s', retry_poll_interval, e, exc_info=True)
                    self._poll_error = e
                    self.set_online(False)
                    await asyncio.sleep(retry_poll_interval)
                    continue

                # Clear poll error, as the poll call has been successful
                self._poll_error = None
                self.set_online(True)

                # Granular sleep so it can be interrupted
                orig_poll_interval = self._poll_interval
                for i in range(self._poll_interval):
                    if not self._polling:
                        break

                    if orig_poll_interval != self._poll_interval:  # Poll interval changed
                        break

                    await asyncio.sleep(1)

            except asyncio.CancelledError:
                self.debug('polling task cancelled')
                break

        self._poll_task = None
        self.debug('polling stopped')

    def set_poll_interval(self, interval: int) -> None:
        self._poll_interval = interval
        self.trigger_port_update_fire_and_forget()

    def get_poll_interval(self) -> int:
        return self._poll_interval

    def get_poll_error(self) -> Exception:
        return self._poll_error

    def has_poll_error(self) -> bool:
        return bool(self._poll_error)

    @abc.abstractmethod
    async def poll(self) -> None:
        raise NotImplementedError()

    async def handle_enable(self) -> None:
        self._poll_task = asyncio.create_task(self._poll_loop())

    async def handle_disable(self) -> None:
        self._polling = False  # Will stop poll loop
        self._poll_error = None

    async def handle_cleanup(self) -> None:
        await super().handle_cleanup()

        if self._poll_task and not self._poll_task.done():
            self._polling = False
            self._poll_task.cancel()
            await self._poll_task


class PolledPort(PeripheralPort, metaclass=abc.ABCMeta):
    # Set these to None to disable read interval attribute
    READ_INTERVAL_MIN = 0
    READ_INTERVAL_MAX = 86400
    READ_INTERVAL_STEP = 1
    READ_INTERVAL_MULTIPLIER = 1
    READ_INTERVAL_UNIT = None

    def __init__(self, peripheral: Peripheral) -> None:
        super().__init__(peripheral)

        # Add read interval attrdef
        if self.READ_INTERVAL_MIN is not None:
            attrdef = copy.deepcopy(READ_INTERVAL_ATTRDEF)

            unit = self.READ_INTERVAL_UNIT
            if unit is None:
                if self.READ_INTERVAL_MULTIPLIER == 3600:
                    unit = 'hours'

                elif self.READ_INTERVAL_MULTIPLIER == 60:
                    unit = 'minutes'

                else:
                    unit = 'seconds'

            attrdef.update(
                unit=unit,
                step=self.READ_INTERVAL_STEP,
                min=self.READ_INTERVAL_MIN,
                max=self.READ_INTERVAL_MAX
            )

            self.ADDITIONAL_ATTRDEFS = dict(self.ADDITIONAL_ATTRDEFS, read_interval=attrdef)

    async def attr_set_read_interval(self, interval: int) -> None:
        peripheral = cast(PolledPeripheral, self.get_peripheral())
        peripheral.set_poll_interval(int(interval) * self.READ_INTERVAL_MULTIPLIER)

    async def attr_get_read_interval(self) -> int:
        peripheral = cast(PolledPeripheral, self.get_peripheral())
        return peripheral.get_poll_interval() // self.READ_INTERVAL_MULTIPLIER
