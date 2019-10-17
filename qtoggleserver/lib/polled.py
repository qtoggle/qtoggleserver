
import abc
import asyncio
import copy
import inspect
import logging

from qtoggleserver import utils
from qtoggleserver.core import ports as core_ports

from . import add_done_hook


READ_INTERVAL_ATTRDEF = {
    'display_name': 'Read Interval',
    'description': 'How often to read peripheral data (set to 0 to disable reading).',
    'type': 'number',
    'modifiable': True,
    'integer': True
}


logger = logging.getLogger(__name__)


class PolledPeripheral(utils.ConfigurableMixin, utils.LoggableMixin):
    DEFAULT_POLL_INTERVAL = 1800

    logger = logger
    _peripherals_by_address = {}

    @classmethod
    def get(cls, address, name='', **kwargs):
        if address not in cls._peripherals_by_address:
            logger.debug('initializing peripheral %s@%s', name, address)
            peripheral = cls.make_peripheral(address, name, **kwargs)
            cls._peripherals_by_address[address] = peripheral

        return cls._peripherals_by_address[address]

    @classmethod
    def make_peripheral(cls, address, name='', **kwargs):
        return cls(address, name, **kwargs)

    def __init__(self, address, name, **kwargs):
        utils.LoggableMixin.__init__(self, name, self.logger)

        self._address = address
        self._name = name
        self._ports = []
        self._enabled = False
        self._polling = False
        self._poll_stopped = False
        self._poll_task = None

        self._poll_interval = self.DEFAULT_POLL_INTERVAL

        add_done_hook(self.handle_done)

    def __str__(self):
        return self._name

    def get_address(self):
        return self._address

    def get_name(self):
        return self._name

    def add_port(self, port):
        self._ports.append(port)

    async def _poll_loop(self):
        self.debug('polling started')
        self._polling = True

        while self._polling:
            if self._poll_interval == 0:
                await asyncio.sleep(1)
                continue

            result = self.poll()
            if inspect.isawaitable(result):
                await result

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

    async def poll(self):
        raise NotImplementedError

    def enable(self):
        if self._enabled:
            return

        self._poll_task = asyncio.create_task(self._poll_loop())

        self._enabled = True
        self.handle_enable()
        self.debug('peripheral is enabled')

    def disable(self):
        if not self._enabled:
            return

        self._enabled = False
        self._polling = False  # Will stop poll loop
        self.handle_disable()
        self.debug('peripheral is disabled')

    def check_disabled(self):
        if not self._enabled:
            return

        for port in self._ports:
            if port.is_enabled():
                break

        else:
            self.debug('all ports are disabled, disabling peripheral')
            self.disable()

    def handle_enable(self):
        pass

    def handle_disable(self):
        pass

    async def handle_done(self):
        self._polling = False
        return self._poll_task


class PolledPort(core_ports.Port, abc.ABC):
    PERIPHERAL_CLASS = PolledPeripheral
    ID = 'port'

    ADDITIONAL_ATTRDEFS = {
        'address': {
            'display_name': 'Address',
            'description': 'The peripheral address.',
            'type': 'string',
            'modifiable': False
        }
    }

    # Set these to None to disable read interval attribute
    READ_INTERVAL_MIN = 0
    READ_INTERVAL_MAX = 86400
    READ_INTERVAL_STEP = 1
    READ_INTERVAL_MULTIPLIER = 1
    READ_INTERVAL_UNIT = None

    def __init__(self, address, name='', **kwargs):
        self._peripheral = self.PERIPHERAL_CLASS.get(address, name, **kwargs)
        self._peripheral.add_port(self)

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

        if name:
            _id = '{}.{}'.format(name, self.ID)

        else:
            _id = self.ID

        super().__init__(_id)

    def get_peripheral(self):
        return self._peripheral

    def handle_enabled_change(self, enabled):
        if enabled:
            # enable the peripheral if disabled
            self._peripheral.enable()

        else:
            # check if all peripheral ports are disabled
            self._peripheral.check_disabled()

    def attr_get_address(self):
        return self._peripheral.get_address()

    def attr_set_read_interval(self, interval):
        self.get_peripheral().set_poll_interval(int(interval) * self.READ_INTERVAL_MULTIPLIER)

    def attr_get_read_interval(self):
        return self.get_peripheral().get_poll_interval() / self.READ_INTERVAL_MULTIPLIER
