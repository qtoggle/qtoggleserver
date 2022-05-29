
from __future__ import annotations

import abc
import asyncio
import functools
import logging

from typing import Any, Callable, Optional

import bleak

from qtoggleserver.core import ports as core_ports

from . import polled


logger = logging.getLogger(__name__)


class BLEException(Exception):
    pass


class CommandTimeout(BLEException):
    pass


class NotificationTimeout(BLEException):
    pass


class BLEPeripheral(polled.PolledPeripheral, metaclass=abc.ABCMeta):
    DEFAULT_CMD_TIMEOUT = 30
    DEFAULT_RETRY_COUNT = 3
    DEFAULT_RETRY_DELAY = 5
    TIMEOUT_ATOM = 0.1

    logger = logger

    def __init__(
        self,
        *,
        address: str,
        cmd_timeout: int = DEFAULT_CMD_TIMEOUT,
        retry_count: int = DEFAULT_RETRY_COUNT,
        retry_delay: int = DEFAULT_RETRY_DELAY,
        **kwargs
    ) -> None:
        self._address: str = address
        self._cmd_timeout: int = cmd_timeout
        self._retry_count: int = retry_count
        self._retry_delay: int = retry_delay
        self._busy: bool = False
        self._notification_data: Optional[bytes] = None

        super().__init__(**kwargs)

    def __str__(self) -> str:
        return self.get_name()

    async def read(self, handle: int) -> bytes:
        return await self._run_cmd(self._read, handle=handle)

    async def write(self, handle: int, data: bytes) -> None:
        return await self._run_cmd(self._write, handle=handle, data=data)

    async def wait_notify(self, handle: int) -> bytes:
        return await self._run_cmd(self._wait_notify, handle=handle)

    async def write_wait_notify(self, handle: int, notify_handle: int, data: bytes) -> bytes:
        return await self._run_cmd(self._write_wait_notify, handle=handle, data=data, notify_handle=notify_handle)

    async def _run_cmd(self, cmd_func: Callable, **kwargs) -> Optional[bytes]:
        # Wait for the peripheral to be ready (not busy)
        timeout = self._cmd_timeout
        while self._busy and timeout > 0:
            await asyncio.sleep(self.TIMEOUT_ATOM)
            timeout -= self.TIMEOUT_ATOM

        if timeout <= 0:
            raise CommandTimeout()

        self._busy = True
        retry = 1
        retry_count = self._retry_count
        while True:
            try:
                response = await asyncio.wait_for(cmd_func(timeout=timeout, **kwargs), timeout)
            except Exception:
                self.error('command execution failed', exc_info=True)

                if retry <= retry_count:
                    await asyncio.sleep(self._retry_delay)
                    self.debug('retry %s/%s', retry, retry_count)
                    retry += 1
                    continue

                self.set_online(False)
                self._busy = False
                raise
            else:
                self.set_online(True)
                self._busy = False
                return response

    async def _read(self, handle: int, timeout: int) -> bytes:
        self.debug('connecting')
        async with bleak.BleakClient(self._address, timeout=timeout) as client:
            self.debug('reading from %04X', handle)
            response = bytes(await client.read_gatt_char(handle))
            self.debug('got response: %s', self.pretty_data(response))
        self.debug('disconnected')

        return response

    async def _write(self, handle: int, data: bytes, timeout: int) -> None:
        self.debug('connecting')
        async with bleak.BleakClient(self._address, timeout=timeout) as client:
            self.debug('writing at %04X: %s', handle, self.pretty_data(data))
            await client.write_gatt_char(handle, data)
        self.debug('disconnected')

    async def _wait_notify(self, handle: int, timeout: int) -> bytes:
        self.debug('connecting')
        async with bleak.BleakClient(self._address, timeout=timeout) as client:
            self.debug('waiting for notification on %04X', handle)
            self._notification_data = None
            await client.start_notify(handle, self._notify_callback)
            try:
                for _ in range(int(timeout / self.TIMEOUT_ATOM)):
                    await asyncio.sleep(self.TIMEOUT_ATOM)
                    if self._notification_data:
                        break
                else:
                    raise NotificationTimeout()
            finally:
                await client.stop_notify(handle)
        self.debug('disconnected')

        return self._notification_data

    async def _write_wait_notify(self, handle: int, notify_handle: int, data: bytes, timeout: int) -> bytes:
        self.debug('connecting')
        async with bleak.BleakClient(self._address, timeout=timeout) as client:
            self.debug('writing at %04X: %s', handle, self.pretty_data(data))
            await client.write_gatt_char(handle, data)
            self.debug('waiting for notification on %04X', notify_handle)
            self._notification_data = None
            await client.start_notify(notify_handle, self._notify_callback)
            try:
                for _ in range(int(timeout / self.TIMEOUT_ATOM)):
                    await asyncio.sleep(self.TIMEOUT_ATOM)
                    if self._notification_data:
                        break
                else:
                    raise NotificationTimeout()
            finally:
                await client.stop_notify(notify_handle)
        self.debug('disconnected')

        return self._notification_data

    def _notify_callback(self, handle: int, data: bytearray) -> None:
        self._notification_data = bytes(data)
        self.debug('got notification on %04X: %s', handle, self.pretty_data(self._notification_data))

    @staticmethod
    def pretty_data(data: bytes) -> str:
        return ' '.join(map(lambda c: f'{c:02X}', data))


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
        except (NotificationTimeout, CommandTimeout) as e:
            raise core_ports.PortTimeout() from e
        except BLEException as e:
            raise core_ports.PortError(str(e)) from e

    return wrapper
