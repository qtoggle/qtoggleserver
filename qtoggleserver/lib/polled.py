
import abc
import asyncio
import copy
import logging

from .peripheral import Peripheral, PeripheralPort


READ_INTERVAL_ATTRDEF = {
    'display_name': 'Read Interval',
    'description': 'How often to read peripheral data (set to 0 to disable reading).',
    'type': 'number',
    'modifiable': True,
    'integer': True
}


logger = logging.getLogger(__name__)


class PolledPeripheral(Peripheral):
    DEFAULT_POLL_INTERVAL = 1800
    RETRY_POLL_INTERVAL = 60

    def __init__(self, address, name, **kwargs):
        self._polling = False
        self._poll_stopped = False
        self._poll_task = None
        self._poll_interval = self.DEFAULT_POLL_INTERVAL
        self._poll_error = None

        super().__init__(address, name, **kwargs)

    async def _poll_loop(self):
        self.debug('polling started')
        self._polling = True

        while self._polling:
            if self._poll_interval == 0:
                await asyncio.sleep(1)
                continue

            try:
                await self.poll()

            except Exception as e:
                retry_poll_interval = min(self.RETRY_POLL_INTERVAL, self._poll_interval)
                self.error('polling failed (retrying in %s seconds): %s', retry_poll_interval, e, exc_info=True)
                self._poll_error = e
                await asyncio.sleep(retry_poll_interval)
                continue

            # Clear poll error, as the poll call has been successful
            self._poll_error = None

            # Granular sleep so it can be interrupted
            orig_poll_interval = self._poll_interval
            for i in range(self._poll_interval):
                if not self._polling:
                    break

                if orig_poll_interval != self._poll_interval:  # Poll interval changed
                    break

                await asyncio.sleep(1)

        self._poll_task = None
        self.debug('polling stopped')

    def set_poll_interval(self, interval):
        self._poll_interval = interval

    def get_poll_interval(self):
        return self._poll_interval

    def get_poll_error(self):
        return self._poll_error

    def check_poll_error(self):
        if self._poll_error:
            # Raise a copy of the error, to prevent traceback piling up
            raise copy.copy(self._poll_error)

    async def poll(self):
        raise NotImplementedError

    async def handle_enable(self):
        self._poll_task = asyncio.create_task(self._poll_loop())

    async def handle_disable(self):
        self._polling = False  # Will stop poll loop
        self._poll_error = None

    async def handle_cleanup(self):
        self._polling = False
        return self._poll_task


class PolledPort(PeripheralPort, metaclass=abc.ABCMeta):
    PERIPHERAL_CLASS = PolledPeripheral

    # Set these to None to disable read interval attribute
    READ_INTERVAL_MIN = 0
    READ_INTERVAL_MAX = 86400
    READ_INTERVAL_STEP = 1
    READ_INTERVAL_MULTIPLIER = 1
    READ_INTERVAL_UNIT = None

    def __init__(self, address, peripheral_name=None, **kwargs):
        super().__init__(address, peripheral_name, **kwargs)

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

            attrdef.update(unit=unit, step=self.READ_INTERVAL_STEP,
                           min=self.READ_INTERVAL_MIN, max=self.READ_INTERVAL_MAX)

            self.ADDITIONAL_ATTRDEFS = dict(self.ADDITIONAL_ATTRDEFS, read_interval=attrdef)

    async def attr_set_read_interval(self, interval):
        self.get_peripheral().set_poll_interval(int(interval) * self.READ_INTERVAL_MULTIPLIER)

    async def attr_get_read_interval(self):
        return self.get_peripheral().get_poll_interval() / self.READ_INTERVAL_MULTIPLIER
