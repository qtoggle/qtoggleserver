
import abc
import asyncio
import functools
import logging
import re
import subprocess
import threading
import time

from bluepy import btle

from qtoggleserver import utils
from qtoggleserver.core import ports as core_ports

from . import polled
from . import add_done_hook


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
        if helper:
            helper.stdin.close()
            helper.stdout.close()


class _BluepyThread(threading.Thread, btle.DefaultDelegate):
    def __init__(self, adapter):
        super().__init__()

        self._adapter = adapter
        self._running = True
        self._loop = asyncio.get_event_loop()
        self._stopped_future = self._loop.create_future()

        self._cmd = None
        self._address = None
        self._handle = None
        self._notify_handle = None
        self._data = None
        self._callback = None
        self._timeout = None

        self._start_time = None
        self._response = None
        self._notification_data = None
        self._error = None
        self._bluepy_peripheral = None

    def run(self):
        while self._running:
            time.sleep(0.5)
            if not self._cmd:
                continue

            try:
                self._execute()

            except Exception as e:
                self._adapter.error('command execution failed: %s', e, exc_info=True)
                self._error = e

            finally:
                self._cmd = None
                self._cleanup()
                self._loop.call_soon_threadsafe(self._callback, self._response,
                                                self._notification_data, self._error)

        self._adapter.debug('command thread stopped')
        self._stopped_future.set_result(None)

    def schedule_cmd(self, cmd, address, handle, notify_handle, data, callback, timeout):
        if self._cmd:
            raise BLEBusy('a command is already scheduled')

        if not self._running:
            raise BLEException('refusing to schedule command on stopped thread')

        self._cmd = cmd
        self._address = address
        self._handle = handle
        self._notify_handle = notify_handle
        self._data = data
        self._callback = callback
        self._timeout = timeout

    def is_busy(self):
        return self._cmd is not None

    def cancel(self):
        if self._cmd:
            self._cmd = None

    def stop(self):
        self._adapter.debug('stopping command thread')
        self._running = False

        return self._stopped_future

    def _execute(self):
        self._start_time = time.time()
        self._response = None
        self._notification_data = None
        self._error = None

        self._adapter.debug('connecting to %s', self._address)
        self._bluepy_peripheral = _BluepyPeripheral(timeout=self._timeout)
        self._bluepy_peripheral.connect(self._address)

        if self._notify_handle:
            self._bluepy_peripheral.withDelegate(self)

        if self._cmd == 'write':
            self._adapter.debug('writing at %04X: %s', self._handle, BLEAdapter.pretty_data(self._data))
            self._bluepy_peripheral.writeCharacteristic(self._handle, self._data, withResponse=True)

        else:  # assuming read
            self._adapter.debug('reading from %04X', self._handle)
            self._response = self._bluepy_peripheral.readCharacteristic(self._handle)

        if not self._cmd:
            return  # Cancelled in the meantime

        if self._response:
            self._adapter.debug('got response %s', BLEAdapter.pretty_data(self._response))

        if not self._cmd:
            return  # Cancelled in the meantime

        if self._notify_handle and self._notification_data is None:
            self._adapter.debug('waiting for notification on %04X', self._notify_handle)

            while not self._notification_data and self._cmd:
                if time.time() - self._start_time > self._timeout:
                    raise BLETimeout('timeout waiting for notification on {:04X}'.format(self._notify_handle))

                try:
                    self._bluepy_peripheral.waitForNotifications(0.1)

                except _BluepyTimeoutError:
                    continue

    def _cleanup(self):
        if self._bluepy_peripheral:
            self._adapter.debug('disconnecting from %s', self._bluepy_peripheral.addr)
            self._bluepy_peripheral.disconnect()
            self._bluepy_peripheral = None

    def handleNotification(self, handle, data):
        if not self._notify_handle or handle != self._notify_handle:
            self._adapter.warning('got unexpected notification on %04X', handle)
            return

        self._adapter.debug('got notification on %04X: %s', handle, BLEAdapter.pretty_data(data))
        self._notification_data = data


class BLEAdapter(utils.ConfigurableMixin, utils.LoggableMixin):
    DEFAULT_NAME = 'hci0'
    CMD_TIMEOUT = 20
    MAX_PENDING_CMDS = 64

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

        self._current = None

        self._cmd_queue = []
        self._peripherals = []

        self._thread = _BluepyThread(self)
        self._thread.start()
        self.debug('command thread started')
        add_done_hook(self._thread.stop)

    def __str__(self):
        return self._name

    def add_peripheral(self, peripheral):
        self._peripherals.append(peripheral)

    def push_cmd(self, cmd, peripheral, handle, notify_handle, data, callback, timeout=None, retry_count=0):
        if len(self._cmd_queue) >= self.MAX_PENDING_CMDS:
            if callback:
                callback(error=BLEBusy('too many pending commands'))

            self.error('too many pending commands')

        self._cmd_queue.append({
            'cmd': cmd,
            'peripheral': peripheral,
            'handle': handle,
            'notify_handle': notify_handle,
            'data': data,
            'callback': callback,
            'timeout': timeout,
            'retry_count': retry_count,
            'retry_no': 0
        })

        self._run_next_cmd()

    def purge(self, peripheral):
        self._cmd_queue = [i for i in self._cmd_queue if i['peripheral'] != peripheral]
        if self._thread.is_busy() and self._current['peripheral'] == peripheral:
            self.debug('canceling current command for peripheral %s', peripheral.get_name())
            self._thread.cancel()
            self._current = None

    def _run_next_cmd(self):
        if self._current:
            return  # busy

        if not self._cmd_queue:
            return  # idle

        self._current = self._cmd_queue.pop(0)
        if not self._current['timeout']:
            self._current['timeout'] = self.CMD_TIMEOUT

        cmd = self._current['cmd']
        peripheral = self._current['peripheral']
        handle = self._current['handle']
        notify_handle = self._current['notify_handle']
        data = self._current['data']
        timeout = self._current['timeout']
        address = peripheral.get_address()

        self._thread.schedule_cmd(cmd, address, handle, notify_handle, data, self._on_cmd_done, timeout)

    def _on_cmd_done(self, response, notification_data, error):
        # Ignore callbacks from cancelled/purged commands
        if not self._current:
            return

        if error:
            if self._retry():
                self._current = None
                self._run_next_cmd()
                return

        self._run_callback(response=response, notification_data=notification_data, error=error)
        self._current = None

        self._run_next_cmd()

    def _run_callback(self, **kwargs):
        if not self._current['callback']:
            return

        try:
            self._current['callback'](**kwargs)

        except Exception as e:
            self.error('command callback failed: %s', e, exc_info=True)

    def _retry(self):
        if self._current['retry_no'] < self._current['retry_count']:
            self._current['retry_no'] += 1
            self._cmd_queue.insert(0, self._current)
            self.warning('retry %s/%s', self._current['retry_no'], self._current['retry_count'])

            return True

        return False

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
                raise Exception('adapter not found: {}'.format(name))

            else:
                raise Exception(output.strip())

        found = re.findall(name + r'\s([0-9a-f:]{17})', output, re.IGNORECASE)
        if not found:
            raise Exception('adapter not found: {}'.format(name))

        return found[0]


class BLEPeripheral(polled.PolledPeripheral, abc.ABC):
    RETRY_COUNT = 3
    WRITE_VALUE_PAUSE = 5

    logger = logger

    @classmethod
    def make_peripheral(cls, address, name='', adapter_name=None, **kwargs):
        if adapter_name is None:
            adapter_name = BLEAdapter.DEFAULT_NAME

        return cls(address, name, BLEAdapter.get(adapter_name))

    def __init__(self, address, name, adapter):
        super().__init__(address, name)

        self._adapter = adapter
        self._adapter.add_peripheral(self)
        self._online = False

    def __str__(self):
        return '{}/{}'.format(self._adapter, self._name)

    def get_adapter(self):
        return self._adapter

    def read(self, handle, retry_count=None):
        if retry_count is None:
            retry_count = self.RETRY_COUNT

        future = asyncio.get_event_loop().create_future()

        self._adapter.push_cmd('read', self, handle, notify_handle=None, data=None,
                               callback=functools.partial(self._response_wrapper, future),
                               retry_count=retry_count)

        return future

    def write(self, handle, data, retry_count=None):
        if retry_count is None:
            retry_count = self.RETRY_COUNT

        future = asyncio.get_event_loop().create_future()

        self._adapter.push_cmd('write', self, handle, notify_handle=None, data=data,
                               callback=functools.partial(self._response_wrapper, future),
                               retry_count=retry_count)

        return future

    def write_notify(self, handle, notify_handle, data, timeout=None, retry_count=None):
        if retry_count is None:
            retry_count = self.RETRY_COUNT

        future = asyncio.get_event_loop().create_future()

        self._adapter.push_cmd('write', self, handle, notify_handle, data,
                               callback=functools.partial(self._response_wrapper, future),
                               timeout=timeout, retry_count=retry_count)

        return future

    def _response_wrapper(self, future, error=None, response=None, notification_data=None):
        if error and self._online:
            self._online = False
            self._handle_offline()

        elif not error and not self._online:
            self._online = True
            self._handle_online()

        if error:
            future.set_exception(error)

        elif notification_data is not None:
            future.set_result(notification_data)

        else:
            future.set_result(response)

    def is_online(self):
        return self._enabled and self._online

    def _handle_offline(self):
        self.debug('%s is offline', self)

        # trigger an update for all ports
        for port in self._ports:
            port.trigger_update()

    def _handle_online(self):
        self.debug('%s is online', self)

        # trigger an update for all ports
        for port in self._ports:
            port.trigger_update()

    @staticmethod
    def pretty_data(data):
        return BLEAdapter.pretty_data(data)


class BLEPort(polled.PolledPort, abc.ABC):
    PERIPHERAL_CLASS = BLEPeripheral

    READ_INTERVAL_MAX = 1440
    READ_INTERVAL_STEP = 5
    READ_INTERVAL_MULTIPLIER = 60

    def __init__(self, address, name, adapter_name=None):
        super().__init__(address, name, adapter_name=adapter_name)

        # Inherit from peripheral
        self._write_value_pause = self.get_peripheral().WRITE_VALUE_PAUSE

    def attr_is_online(self):
        if not self.is_enabled():
            return False

        return self.get_peripheral().is_online()


def port_exceptions(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # transform BLE exceptions into port exceptions, where applicable
        try:
            return func(*args, **kwargs)

        except BLETimeout:
            raise core_ports.PortTimeout()

        except BLEException as e:
            raise core_ports.PortError(str(e))

    return wrapper
