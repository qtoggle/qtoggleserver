
import abc
import asyncio
import logging
import os
import re

from qtoggleserver.lib import polled


W1_DEVICES_PATH = '/sys/bus/w1/devices'
SLAVE_FILE_NAME = 'w1_slave'


logger = logging.getLogger(__name__)


class OneWireException(Exception):
    pass


class OneWirePeripheralNotFound(OneWireException):
    def __init__(self, address):
        super().__init__('peripheral @{} not found'.format(address))


class OneWirePeripheralAddressRequired(OneWireException):
    def __init__(self):
        super().__init__('peripheral address required')


class OneWireTimeout(OneWireException):
    def __init__(self, message='timeout'):
        super().__init__(message)


class OneWirePeripheral(polled.PolledPeripheral):
    logger = logger

    TIMEOUT = 5  # Seconds

    def __init__(self, address, name):
        super().__init__(address, name)

        self._filename = None
        self._data = None
        self._error = None

    def get_filename(self):
        if self._filename is None:
            self._filename = self._find_filename()

        return self._filename

    def _find_filename(self):
        address_parts = re.split('[^a-zA-Z0-9]', self.get_address())
        pat = address_parts[0] + '-0*' + ''.join(address_parts[1:])
        for name in os.listdir(W1_DEVICES_PATH):
            if re.match(pat, name, re.IGNORECASE):
                return os.path.join(W1_DEVICES_PATH, name, SLAVE_FILE_NAME)

        raise OneWirePeripheralNotFound(self.get_address())

    def read(self):
        if self._error:
            error = self._error
            self._error = None

            raise error

        data = self._data
        self._data = None

        return data

    def read_sync(self):
        filename = self.get_filename()
        self.debug('opening file %s', filename)
        with open(filename, 'r') as f:
            data = f.read()
            self.debug('read data: %s', data.replace('\n', '\\n'))

        return data

    async def poll(self):
        try:
            future = self.run_threaded(self.read_sync)
            self._data = await asyncio.wait_for(future, timeout=self.TIMEOUT)

        except asyncio.TimeoutError:
            self._error = OneWireTimeout('timeout waiting for one-wire data from peripheral')

        except Exception as e:
            self._error = e

        else:
            self._error = None

    async def handle_disable(self):
        self._filename = None
        self._data = None
        self._error = None


class OneWirePort(polled.PolledPort, metaclass=abc.ABCMeta):
    PERIPHERAL_CLASS = OneWirePeripheral

    def __init__(self, address=None, peripheral_name=None):
        autodetected = False
        if address is None:
            address = self.autodetect_address()
            autodetected = True

        super().__init__(address, peripheral_name)

        if autodetected:
            self.debug('autodetected device address %s', address)

    @staticmethod
    def autodetect_address():
        # TODO make this method look only through specific device types (e.g. temperature sensors)

        names = os.listdir(W1_DEVICES_PATH)
        names = [n for n in names if re.match('^[0-9]{2}-', n)]
        if len(names) == 0:
            raise OneWirePeripheralNotFound('auto')

        if len(names) > 1:
            raise OneWirePeripheralAddressRequired()

        address = re.sub('[^a-f0-9]', '', names[0], re.IGNORECASE)
        address = ':'.join([address[2 * i: 2 * i + 2] for i in range(len(address) // 2)])

        return address
