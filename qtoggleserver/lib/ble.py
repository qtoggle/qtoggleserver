
import abc
import asyncio
import functools
import logging
import re
import subprocess
import time

from bluepy import btle

from qtoggleserver import utils
from qtoggleserver.core import ports as core_ports

from . import polled
from .peripheral import Peripheral, RunnerBusy


logger = logging.getLogger(__name__)


class BLEException(Exception):
    pass


class BLEBusy(BLEException):
    def __init__(self, message='busy'):
        super().__init__(message)


class BLETimeout(BLEException):
    def __init__(self, message='timeout'):
        super().__init__(message)


class _BluepyTimeoutError(btle.BTLEException):
    def __init__(self, message, rsp=None):
        super().__init__(message, rsp)


class _BluepyPeripheral(btle.Peripheral):
    def __init__(self, timeout=None, *args, **kwargs):
        self._timeout = timeout
        super().__init__(*args, **kwargs)

    def _getResp(self, wantType, timeout=None):
        # Override this method to be able to inject a default timeout
        # We also need to raise a timeout exception in case the response is None

        timeout = timeout or self._timeout
        response = super()._getResp(wantType, timeout)
        if response is None:
            raise _BluepyTimeoutError('timeout waiting for a response from peripheral')

        return response

    def _stopHelper(self):
        # Override this method to close the helper's stdout and stdin streams.
        helper = self._helper
        super()._stopHelper()
        self._helper = helper
        if helper:
            helper.stdin.close()
            helper.stdout.close()


class BLEAdapter(utils.ConfigurableMixin, utils.LoggableMixin):
    DEFAULT_NAME = 'hci0'
    RUNNER_CLASS = Peripheral.RUNNER_CLASS

    _adapters_by_name = {}

    @classmethod
    def get(cls, name):
        if name not in cls._adapters_by_name:
            logger.debug('initializing adapter %s', name)
            adapter = cls(name)
            cls._adapters_by_name[name] = adapter

        return cls._adapters_by_name[name]

    def __init__(self, name):
        utils.LoggableMixin.__init__(self, name, logger)

        self._name = name
        try:
            self._address = self._find_address(name)

        except Exception as e:
            self.error('could not initialize adapter: %s', e)
            raise

        self.debug('found adapter address %s', self._address)

        self._runner = None
        self._peripherals = []

    def __str__(self):
        return self._name

    def add_peripheral(self, peripheral):
        self._peripherals.append(peripheral)

    def get_runner(self):
        if self._runner is None:
            self._runner = self.make_runner()

        return self._runner

    def make_runner(self):
        self.debug('starting threaded runner')
        runner = self.RUNNER_CLASS(queue_size=Peripheral.RUNNER_QUEUE_SIZE)
        runner.start()

        return runner

    @staticmethod
    def pretty_data(data):
        return ' '.join(map(lambda c: '{:02X}'.format(c), data))

    @staticmethod
    def _find_address(name):
        try:
            output = subprocess.check_output(['hcitool', '-i', name, 'dev'], stderr=subprocess.STDOUT).decode()

        except subprocess.CalledProcessError as e:
            output = e.output.decode()
            if output.count('No such device'):
                raise Exception('adapter not found: {}'.format(name)) from e

            else:
                raise Exception(output.strip()) from e

        found = re.findall(name + r'\s([0-9a-f:]{17})', output, re.IGNORECASE)
        if not found:
            raise Exception('adapter not found: {}'.format(name))

        return found[0]


class BLEPeripheral(polled.PolledPeripheral, metaclass=abc.ABCMeta):
    CMD_TIMEOUT = 10
    RETRY_COUNT = 2
    RETRY_DELAY = 2
    WRITE_VALUE_PAUSE = 5

    logger = logger

    @classmethod
    def make_peripheral(cls, address, name, adapter_name=None, **kwargs):
        return cls(address, name, BLEAdapter.get(adapter_name))

    def __init__(self, address, name, adapter):
        super().__init__(address, name)

        self._adapter = adapter
        self._adapter.add_peripheral(self)
        self._online = False

    def __str__(self):
        return '{}/{}'.format(self._adapter, self._name)

    def make_runner(self):
        # Instead of creating a runner for each peripheral instance, we use adapter's runner, thus having one runner per
        # adapter instance.

        return self._adapter.get_runner()

    async def read(self, handle, retry_count=None):
        if retry_count is None:
            retry_count = self.RETRY_COUNT

        return await self._run_cmd_async('read', self.get_address(), handle, notify_handle=None,
                                         data=None, timeout=self.CMD_TIMEOUT, retry_count=retry_count)

    async def write(self, handle, data, retry_count=None):
        if retry_count is None:
            retry_count = self.RETRY_COUNT

        return await self._run_cmd_async('write', self.get_address(), handle, notify_handle=None,
                                         data=data, timeout=self.CMD_TIMEOUT, retry_count=retry_count)

    async def write_notify(self, handle, notify_handle, data, timeout=None, retry_count=None):
        if retry_count is None:
            retry_count = self.RETRY_COUNT

        if timeout is None:
            timeout = self.CMD_TIMEOUT

        return await self._run_cmd_async('write', self.get_address(), handle, notify_handle=notify_handle,
                                        data=data, timeout=timeout, retry_count=retry_count)

    def _run_cmd(self, cmd, address, handle, notify_handle, data, timeout):
        start_time = time.time()
        response = None
        notification_data = None

        self.debug('connecting to %s', address)

        bluepy_peripheral = _BluepyPeripheral(timeout=timeout)
        bluepy_peripheral.connect(address)

        if notify_handle:
            # Create a temporary class to deal with BTLE delegation

            peripheral = self
            class Delegate(btle.DefaultDelegate):

                def handleNotification(self, h, d):
                    nonlocal notification_data

                    if not notify_handle or h != notify_handle:
                        peripheral.warning('got unexpected notification on %04X', h)
                        return

                    peripheral.debug('got notification on %04X: %s', h, BLEPeripheral.pretty_data(d))
                    notification_data = d

            bluepy_peripheral.withDelegate(Delegate())

        if cmd == 'write':
            self.debug('writing at %04X: %s', handle, self.pretty_data(data))
            bluepy_peripheral.writeCharacteristic(handle, data, withResponse=True)

        else:  # assuming read
            self.debug('reading from %04X', handle)
            response = bluepy_peripheral.readCharacteristic(handle)
            self.debug('got response %s', self.pretty_data(response))

        if notify_handle and notification_data is None:
            self.debug('waiting for notification on %04X', notify_handle)

            while not notification_data and self.get_runner().is_running():
                if time.time() - start_time > timeout:
                    bluepy_peripheral._stopHelper()
                    raise BLETimeout('timeout waiting for notification on {:04X}'.format(notify_handle))

                try:
                    bluepy_peripheral.waitForNotifications(0.1)

                except _BluepyTimeoutError:
                    continue

        return response, notification_data

    async def _run_cmd_async(self, cmd, address, handle, notify_handle, data, timeout, retry_count):
        retry = 1
        while True:
            try:
                response, notification_data = await self.run_threaded(self._run_cmd, cmd, address, handle,
                                                                      notify_handle, data, timeout)

            except Exception as e:
                self.error('command execution failed: %s', e, exc_info=True)

                if retry <= retry_count:
                    self.warning('retry %s/%s', retry, retry_count)
                    await asyncio.sleep(self.RETRY_DELAY)
                    retry += 1
                    continue

                if self._online:
                    self._online = False
                    self._handle_offline()

                if isinstance(e, RunnerBusy):
                    raise BLEBusy('too many pending commands') from e

                raise

            else:
                if not self._online:
                    self._online = True
                    self._handle_online()

                return response, notification_data

    def is_online(self):
        return self._enabled and self._online

    def _handle_offline(self):
        self.debug('%s is offline', self)
        self.trigger_port_update()

    def _handle_online(self):
        self.debug('%s is online', self)
        self.trigger_port_update()

    @staticmethod
    def pretty_data(data):
        return BLEAdapter.pretty_data(data)


class BLEPort(polled.PolledPort, metaclass=abc.ABCMeta):
    PERIPHERAL_CLASS = BLEPeripheral

    READ_INTERVAL_MAX = 1440
    READ_INTERVAL_STEP = 1
    READ_INTERVAL_MULTIPLIER = 60

    def __init__(self, address, peripheral_name=None, adapter_name=None):
        if adapter_name is None:
            adapter_name = BLEAdapter.DEFAULT_NAME

        super().__init__(address, peripheral_name, adapter_name=adapter_name)

    async def attr_get_write_value_pause(self):
        # Inherit from peripheral
        return self.get_peripheral().WRITE_VALUE_PAUSE

    async def attr_is_online(self):
        if not self.is_enabled():
            return False

        return self.get_peripheral().is_online()


def port_exceptions(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # transform BLE exceptions into port exceptions, where applicable
        try:
            return func(*args, **kwargs)

        except BLETimeout as e:
            raise core_ports.PortTimeout() from e

        except BLEException as e:
            raise core_ports.PortError(str(e)) from e

    return wrapper
