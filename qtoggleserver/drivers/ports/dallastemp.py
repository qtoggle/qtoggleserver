
import logging
import re

from qtoggleserver.lib import onewire


logger = logging.getLogger(__name__)


class DallasTemperatureSensor(onewire.OneWirePeripheral):
    TEMP_PATTERN = r't=(\d+)'

    logger = logger

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._temp = None

    def get_temp(self):
        data = self.read()
        if data:
            m = re.search(self.TEMP_PATTERN, data, re.MULTILINE | re.DOTALL)
            if m:
                self._temp = round(int(m.group(1)) / 100.0) / 10.0
                self.debug('temperature is %.1f degrees', self._temp)

        return self._temp


class Temperature(onewire.OneWirePort):
    TYPE = 'number'
    WRITABLE = False
    MIN = -55
    MAX = 125
    DISPLAY_NAME = 'Temperature'
    UNIT = u'\xb0C'  # degrees celsius

    PERIPHERAL_CLASS = DallasTemperatureSensor
    ID = 'temperature'

    async def read_value(self):
        return self.get_peripheral().get_temp()
