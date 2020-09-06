
from __future__ import annotations

import abc
import asyncio
import functools
import logging
import re
import subprocess
import time

from typing import Any, Callable, Dict, List, Optional, Tuple

from bluepy import btle

from qtoggleserver.core import ports as core_ports
from qtoggleserver.peripherals import Peripheral, RunnerBusy
from qtoggleserver.utils import logging as logging_utils

from . import polled


logger = logging.getLogger(__name__)

DEFAULT_ADAPTER_NAME = 'hci0'


class BLEException(Exception):
    pass


class BLEBusy(BLEException):
    def __init__(self, message: str = 'busy') -> None:
        super().__init__(message)


class BLETimeout(BLEException):
    def __init__(self, message: str = 'timeout') -> None:
        super().__init__(message)


class _BluepyTimeoutError(btle.BTLEException):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class _BluepyPeripheral(btle.Peripheral):
    def __init__(self, timeout: Optional[int] = None, *args, **kwargs) -> None:
        self._timeout: Optional[int] = timeout
        super().__init__(*args, **kwargs)

    def _getResp(self, wantType: Any, timeout: int = None) -> Any:
        # Override this method to be able to inject a default timeout
        # We also need to raise a timeout exception in case the response is None

        timeout = timeout or self._timeout
        response = super()._getResp(wantType, timeout)
        if response is None:
            raise _BluepyTimeoutError('Timeout waiting for a response from peripheral')

        return response

    def _stopHelper(self) -> None:
        # Override this method to close the helper's stdout and stdin streams

        helper = self._helper
        super()._stopHelper()
        self._helper = helper
        if helper:
            helper.stdin.close()
            helper.stdout.close()


class BLEAdapter(logging_utils.LoggableMixin):
    RUNNER_CLASS = Peripheral.RUNNER_CLASS

    _adapters_by_name: Dict[str, BLEAdapter] = {}

    @classmethod
    def get(cls, name: str) -> BLEAdapter:
        if name not in cls._adapters_by_name:
            logger.debug('initializing adapter %s', name)
            adapter = cls(name)
            cls._adapters_by_name[name] = adapter

        return cls._adapters_by_name[name]

    def __init__(self, name: str) -> None:
        logging_utils.LoggableMixin.__init__(self, name, logger)

        self._name: str = name
        try:
            self._address: str = self._find_address(name)

        except Exception as e:
            self.error('could not initialize adapter: %s', e)
            raise

        self.debug('found adapter address %s', self._address)

        self._runner: Optional[BLEPeripheral.RUNNER_CLASS] = None
        self._peripherals: List[BLEPeripheral] = []

    def __str__(self) -> str:
        return self._name

    def add_peripheral(self, peripheral: BLEPeripheral) -> None:
        self._peripherals.append(peripheral)

    def get_runner(self) -> BLEPeripheral.RUNNER_CLASS:
        if self._runner is None:
            self._runner = self.make_runner()

        return self._runner

    def make_runner(self) -> BLEPeripheral.RUNNER_CLASS:
        self.debug('starting threaded runner')
        runner = self.RUNNER_CLASS(queue_size=Peripheral.RUNNER_QUEUE_SIZE)
        runner.start()

        return runner

    @staticmethod
    def pretty_data(data: bytes) -> str:
        return ' '.join(map(lambda c: f'{c:02X}', data))

    @staticmethod
    def _find_address(name: str) -> str:
        try:
            output = subprocess.check_output(['hcitool', '-i', name, 'dev'], stderr=subprocess.STDOUT).decode()

        except subprocess.CalledProcessError as e:
            output = e.output.decode()
            if output.count('No such device'):
                raise Exception(f'Adapter not found: {name}') from e

            else:
                raise Exception(output.strip()) from e

        found = re.findall(name + r'\s([0-9a-f:]{17})', output, re.IGNORECASE)
        if not found:
            raise Exception(f'Adapter not found: {name}')

        return found[0]


class BLEPeripheral(polled.PolledPeripheral, metaclass=abc.ABCMeta):
    CMD_TIMEOUT = 10
    RETRY_COUNT = 2
    RETRY_DELAY = 2

    logger = logger

    def __init__(self, *, address: str, adapter_name: str = DEFAULT_ADAPTER_NAME, **kwargs) -> None:
        self._address = address
        self._adapter: BLEAdapter = BLEAdapter.get(adapter_name)
        self._adapter.add_peripheral(self)

        super().__init__(**kwargs)

    def __str__(self) -> str:
        return f'{self._adapter}/{self._name}'

    def make_runner(self) -> BLEPeripheral.RUNNER_CLASS:
        # Instead of creating a runner for each peripheral instance, we use adapter's runner, thus having one runner per
        # adapter instance.

        return self._adapter.get_runner()

    async def read(self, handle: int, retry_count: Optional[int] = None) -> Optional[bytes]:
        if retry_count is None:
            retry_count = self.RETRY_COUNT

        return (await self._run_cmd_async(
            'read',
            self._address,
            handle,
            notify_handle=None,
            data=None,
            timeout=self.CMD_TIMEOUT,
            retry_count=retry_count
        ))[0]

    async def write(
        self,
        handle: int,
        data: bytes,
        retry_count: Optional[int] = None
    ) -> Optional[bytes]:

        if retry_count is None:
            retry_count = self.RETRY_COUNT

        return (await self._run_cmd_async(
            'write',
            self._address,
            handle,
            notify_handle=None,
            data=data,
            timeout=self.CMD_TIMEOUT,
            retry_count=retry_count
        ))[0]

    async def write_notify(
        self,
        handle: int,
        notify_handle: int,
        data: bytes,
        timeout: Optional[int] = None,
        retry_count: int = None
    ) -> Tuple[Optional[bytes], Optional[bytes]]:

        if retry_count is None:
            retry_count = self.RETRY_COUNT

        if timeout is None:
            timeout = self.CMD_TIMEOUT

        return await self._run_cmd_async(
            'write',
            self._address,
            handle,
            notify_handle=notify_handle,
            data=data,
            timeout=timeout,
            retry_count=retry_count
        )

    def _run_cmd(
        self,
        cmd: str,
        address: str,
        handle: int,
        notify_handle: Optional[int],
        data: Optional[bytes],
        timeout: Optional[int]
    ) -> Tuple[Optional[bytes], Optional[bytes]]:

        start_time = time.time()
        response = None
        notification_data = None

        self.debug('connecting to %s', address)

        bluepy_peripheral = _BluepyPeripheral(timeout=timeout)
        try:
            bluepy_peripheral.connect(address)

        except _BluepyTimeoutError:
            bluepy_peripheral._stopHelper()
            raise BLETimeout(f'Timeout connecting to {address}') from None

        if notify_handle:
            # Create a temporary class to deal with BTLE delegation

            peripheral = self

            class Delegate(btle.DefaultDelegate):

                def handleNotification(self, h: int, d: bytes) -> None:
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

        else:  # Assuming read
            self.debug('reading from %04X', handle)
            response = bluepy_peripheral.readCharacteristic(handle)
            self.debug('got response: %s', self.pretty_data(response))

        if notify_handle and notification_data is None:
            self.debug('waiting for notification on %04X', notify_handle)

            while not notification_data and self.get_runner().is_running():
                if time.time() - start_time > timeout:
                    bluepy_peripheral._stopHelper()
                    raise BLETimeout(f'Timeout waiting for notification on {notify_handle:04X} from {address}')

                try:
                    bluepy_peripheral.waitForNotifications(0.1)

                except _BluepyTimeoutError:
                    continue

        self.debug('%s command done', cmd)

        return response, notification_data

    async def _run_cmd_async(
        self,
        cmd: str,
        address: str,
        handle: int,
        notify_handle: Optional[int],
        data: Optional[bytes],
        timeout: Optional[int],
        retry_count: int
    ) -> Tuple[Optional[bytes], Optional[bytes]]:

        retry = 1
        while True:
            try:
                response, notification_data = await self.run_threaded(
                    self._run_cmd,
                    cmd,
                    address,
                    handle,
                    notify_handle,
                    data,
                    timeout
                )

            except Exception as e:
                self.error('command execution failed: %s', e)

                if retry <= retry_count:
                    await asyncio.sleep(self.RETRY_DELAY)
                    self.warning('retry %s/%s', retry, retry_count)
                    retry += 1
                    continue

                self.set_online(False)

                if isinstance(e, RunnerBusy):
                    raise BLEBusy('Too many pending commands') from e

                raise

            else:
                self.set_online(True)

                return response, notification_data

    @staticmethod
    def pretty_data(data: bytes) -> str:
        return BLEAdapter.pretty_data(data)


class BLEPort(polled.PolledPort, metaclass=abc.ABCMeta):
    READ_INTERVAL_MAX = 1440
    READ_INTERVAL_STEP = 1
    READ_INTERVAL_MULTIPLIER = 60


def port_exceptions(func: Callable) -> Callable:
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        # Transform BLE exceptions into port exceptions, where applicable
        try:
            return func(*args, **kwargs)

        except BLETimeout as e:
            raise core_ports.PortTimeout() from e

        except BLEException as e:
            raise core_ports.PortError(str(e)) from e

    return wrapper
