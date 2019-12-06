
import abc
import logging

from qtoggleserver import utils
from qtoggleserver.core import ports as core_ports

from . import add_done_hook


logger = logging.getLogger(__name__)


class Peripheral(utils.ConfigurableMixin, utils.LoggableMixin, abc.ABC):
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

        add_done_hook(self.handle_done)

    def __str__(self):
        return self._name

    def get_address(self):
        return self._address

    def get_name(self):
        return self._name

    def add_port(self, port):
        self._ports.append(port)

    def is_enabled(self):
        return self._enabled

    async def enable(self):
        if self._enabled:
            return

        self._enabled = True
        await self.handle_enable()
        self.debug('peripheral is enabled')

    async def disable(self):
        if not self._enabled:
            return

        self._enabled = False
        await self.handle_disable()
        self.debug('peripheral is disabled')

    async def check_disabled(self):
        if not self._enabled:
            return

        for port in self._ports:
            if port.is_enabled():
                break

        else:
            self.debug('all ports are disabled, disabling peripheral')
            await self.disable()

    async def handle_enable(self):
        pass

    async def handle_disable(self):
        pass

    async def handle_done(self):
        pass


class PeripheralPort(core_ports.Port, abc.ABC):
    PERIPHERAL_CLASS = Peripheral
    ID = 'port'

    ADDITIONAL_ATTRDEFS = {
        'address': {
            'display_name': 'Address',
            'description': 'The peripheral address.',
            'type': 'string',
            'modifiable': False
        }
    }

    def __init__(self, address, name='', **kwargs):
        self._peripheral = self.PERIPHERAL_CLASS.get(address, name, **kwargs)
        self._peripheral.add_port(self)

        if name:
            _id = '{}.{}'.format(name, self.ID)

        else:
            _id = self.ID

        super().__init__(_id)

    def get_peripheral(self):
        return self._peripheral

    def attr_get_address(self):
        return self._peripheral.get_address()

    async def handle_enabled_change(self, enabled):
        if enabled and not self._peripheral.is_enabled():
            # enable the peripheral if disabled
            await self._peripheral.enable()

        elif not enabled and self._peripheral.is_enabled():
            # check if all peripheral ports are disabled
            await self._peripheral.check_disabled()
