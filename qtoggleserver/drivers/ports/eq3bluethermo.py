
import datetime

from qtoggleserver.core import ports
from qtoggleserver.lib import ble


class EQ3BlueThermo(ble.BLEPeripheral):
    WRITE_HANDLE = 0x0411
    NOTIFY_HANDLE = 0x0421

    STATUS_SEND_HEADER = 0x03
    STATUS_RECV_HEADER = 0x02
    STATUS_BOOST_MASK = 0x04

    STATUS_BITS_INDEX = 2
    STATUS_TEMP_INDEX = 5

    WRITE_TEMP_HEADER = 0x41
    WRITE_BOOST_HEADER = 0x45

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._temp = None
        self._boost = False

    async def set_temp(self, temp):
        self.debug('setting temperature to %.1f degrees', temp)

        try:
            await self.write(self.WRITE_HANDLE, bytes([self.WRITE_TEMP_HEADER, int(temp * 2)]))

        except Exception as e:
            self.error('failed to set temperature: %s', e, exc_info=True)

        else:
            self.debug('successfully set temperature')
            self._temp = temp

    def get_temp(self):
        return self._temp

    async def set_boost(self, boost):
        self.debug('%s boost', ['disabling', 'enabling'][boost])

        try:
            await self.write(self.WRITE_HANDLE, bytes([self.WRITE_BOOST_HEADER, int(boost)]))

        except Exception as e:
            self.error('failed to set boost: %s', e, exc_info=True)

        else:
            self.debug('successfully set boost')
            self._boost = boost

    def get_boost(self):
        return self._boost

    async def poll(self):
        await self._read_config()

    async def _read_config(self):
        try:
            data = await self.write_notify(self.WRITE_HANDLE, self.NOTIFY_HANDLE,
                                           bytes([self.STATUS_SEND_HEADER] + self._make_status_value()))

        except Exception as e:
            self.error('failed to read current configuration: %s', e, exc_info=True)
            return

        if len(data) < 6:
            self.error('notification data too short: %s', self.pretty_data(data))
            return

        if data[0] != self.STATUS_RECV_HEADER:
            self.error('unexpected notification data header: %02X', data[0])
            return

        self._boost = bool(data[self.STATUS_BITS_INDEX] & self.STATUS_BOOST_MASK)
        self._temp = data[self.STATUS_TEMP_INDEX] / 2.0

        self.debug('temperature is %.1f degrees', self._temp)
        self.debug('boost mode is %s', ['disabled', 'enabled'][self._boost])

    @staticmethod
    def _make_status_value():
        now = datetime.datetime.now()

        return [
            now.year - 2000,
            now.month,
            now.day,
            now.hour,
            now.minute,
            now.second
        ]


class Temperature(ble.BLEPort):
    TYPE = 'number'
    WRITABLE = True
    MIN = 5
    MAX = 30
    STEP = 0.5
    DESCRIPTION = 'Thermostat Temperature'
    UNIT = u'\xb0C'  # degrees celsius

    PERIPHERAL_CLASS = EQ3BlueThermo
    ID = 'temperature'

    def read_value(self):
        return self.get_peripheral().get_temp()

    @ble.port_exceptions
    async def write_value(self, value):
        await self.get_peripheral().set_temp(value)


class Boost(ble.BLEPort):
    TYPE = ports.TYPE_BOOLEAN
    WRITABLE = True
    DESCRIPTION = 'Thermostat Boost Mode'

    PERIPHERAL_CLASS = EQ3BlueThermo
    ID = 'boost'

    def read_value(self):
        return self.get_peripheral().get_boost()

    @ble.port_exceptions
    async def write_value(self, value):
        await self.get_peripheral().set_boost(value)
