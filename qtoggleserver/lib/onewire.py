import abc
import asyncio
import logging
import os
import re

from qtoggleserver.lib import polled


W1_DEVICES_PATH = "/sys/bus/w1/devices"
SLAVE_FILE_NAME = "w1_slave"


class OneWireException(Exception):
    pass


class OneWirePeripheralNotFound(OneWireException):
    def __init__(self, address: str) -> None:
        super().__init__(f"Peripheral @{address} not found")


class OneWireTimeout(OneWireException):
    def __init__(self, message: str = "timeout") -> None:
        super().__init__(message)


class OneWirePeripheral(polled.PolledPeripheral, metaclass=abc.ABCMeta):
    TIMEOUT = 5  # seconds

    logger = logging.getLogger(__name__)

    def __init__(self, *, address: str, **kwargs) -> None:
        super().__init__(**kwargs)

        self._address: str = address
        self._filename: str | None = None
        self._data: str | None = None

    def get_filename(self) -> str:
        if self._filename is None:
            self._filename = self._find_filename()

        return self._filename

    def _find_filename(self) -> str:
        address_parts = re.split("[^a-zA-Z0-9]", self._address)
        pat = address_parts[0] + "-0*" + "".join(address_parts[1:])
        for name in os.listdir(W1_DEVICES_PATH):
            if re.match(pat, name, re.IGNORECASE):
                return os.path.join(W1_DEVICES_PATH, name, SLAVE_FILE_NAME)

        raise OneWirePeripheralNotFound(self._address)

    # def autodetect_addresses(self) -> list[str]:
    #     # TODO: make this method look only through specific device types (e.g. temperature sensors)
    #     # TODO: use this method in a more general peripheral autodetection routine
    #
    #     names = os.listdir(W1_DEVICES_PATH)
    #     names = [n for n in names if re.match('^[0-9]{2}-', n)]
    #     addresses = [re.sub('[^a-f0-9]', '', n, re.IGNORECASE) for n in names]
    #     addresses = [':'.join(a[2 * i: 2 * i + 2] for i in range(len(a) // 2)) for a in addresses]
    #
    #     return addresses

    def read(self) -> str | None:
        data = self._data
        self._data = None

        return data

    def read_sync(self) -> str | None:
        filename = self.get_filename()
        self.debug("opening file %s", filename)
        with open(filename) as f:
            data = f.read()
            self.debug("read data: %s", data.replace("\n", "\\n"))

        return data

    async def poll(self) -> None:
        try:
            future = self.run_threaded(self.read_sync)
            self._data = await asyncio.wait_for(future, timeout=self.TIMEOUT)
        except TimeoutError as e:
            raise OneWireTimeout("Timeout waiting for one-wire data from peripheral") from e

    async def handle_disable(self) -> None:
        await super().handle_disable()

        self._filename = None
        self._data = None


class OneWirePort(polled.PolledPort, metaclass=abc.ABCMeta):
    pass
