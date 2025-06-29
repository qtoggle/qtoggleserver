# ruff: noqa: ANN001, ANN002, ANN201, F821

from __future__ import annotations

import abc
import asyncio
import functools
import logging

from collections.abc import Callable
from typing import Any

import bleak

from dbus_next import BusType, Variant
from dbus_next.aio import MessageBus
from dbus_next.errors import DBusError
from dbus_next.service import ServiceInterface, method

from qtoggleserver.core import ports as core_ports

from . import polled


BLUEZ_PROPERTIES_IFACE = "org.freedesktop.DBus.Properties"
BLUEZ_BUS_NAME = "org.bluez"
BLUEZ_DEVICE_IFACE = "org.bluez.Device1"
BLUEZ_AGENT_PATH = "/io/qtoggle/agent"
BLUEZ_AGENT_IFACE = "org.bluez.Agent1"
BLUEZ_AGENT_MANAGER_IFACE = "org.bluez.AgentManager1"
BLUEZ_AGENT_MANAGER_PATH = "/org/bluez"
BLUEZ_AGENT_CAPABILITY = "KeyboardDisplay"
BLUEZ_ADAPTER_PATH = "/org/bluez/hci0"
BLUEZ_ADAPTER_IFACE = "org.bluez.Adapter1"

logger = logging.getLogger(__name__)

agent: Agent | None = None


class BLEException(Exception):
    pass


class CommandTimeout(BLEException):
    pass


class NotificationTimeout(BLEException):
    pass


class Agent(ServiceInterface):
    def __init__(self, bus: MessageBus) -> None:
        super().__init__(BLUEZ_AGENT_IFACE)

        self.bus: MessageBus = bus
        self.secrets_by_address: dict[str, str | None] = {}

    async def set_trusted(self, path: str) -> None:
        logger.debug("setting device at BT path %s as trusted", path)

        introspection = await self.bus.introspect(BLUEZ_BUS_NAME, path)
        obj = self.bus.get_proxy_object(BLUEZ_BUS_NAME, path, introspection)
        props = obj.get_interface(BLUEZ_PROPERTIES_IFACE)
        await props.call_set(BLUEZ_DEVICE_IFACE, "Trusted", Variant("b", True))

    def add_device(self, address: str, secret: str | None) -> None:
        self.secrets_by_address[address.lower()] = secret

    def rem_device(self, address: str) -> None:
        self.secrets_by_address.pop(address, None)

    @method()
    async def Release(self):
        logger.debug("BT agent Release() called")

    @method()
    async def Cancel(self):
        logger.debug("BT agent Cancel() called")

    @method()
    async def AuthorizeService(self, device: "o", uuid: "s"):
        logger.debug("BT agent AuthorizeService(%s, %s) called", device, uuid)
        address = self.address_from_device_path(device)
        if address not in self.secrets_by_address:
            logger.warning("got BT service authorization request from unknown device %s", address)
            raise DBusError("org.bluez.Error.Rejected", "unknown device")

    @method()
    async def RequestConfirmation(self, device: "o", passkey: "u"):
        logger.debug("BT agent RequestConfirmation(%s, %s) called", device, passkey)

        _none = {}
        address = self.address_from_device_path(device)
        secret = self.secrets_by_address.get(address, _none)
        if secret is _none:
            logger.warning("got BT request confirmation from unknown device %s", address)
            raise DBusError("org.bluez.Error.Rejected", "unknown device")

        if not secret:
            logger.warning("got BT passkey request from device %s with unconfigured secret", address)
            raise DBusError("org.bluez.Error.Rejected", "unconfigured secret")

        # `passkey` is a 0-padded 6-digit string
        while len(secret) < 6:
            secret = "0" + secret
        if secret != passkey:
            logger.warning("got BT request confirmation from device %s with invalid passkey %s", address, passkey)
            raise DBusError("org.bluez.Error.Rejected", "invalid passkey")

    @method()
    async def RequestAuthorization(self, device: "o"):
        logger.debug("BT agent RequestAuthorization(%s) called", device)
        address = self.address_from_device_path(device)
        if address not in self.secrets_by_address:
            logger.warning("got BT authorization request from unknown device %s", address)
            raise DBusError("org.bluez.Error.Rejected", "unknown device")

    @method()
    async def RequestPasskey(self, device: "o") -> "u":
        logger.debug("BT agent RequestPasskey(%s) called", device)

        _none = {}
        address = self.address_from_device_path(device)
        secret = self.secrets_by_address.get(address, _none)
        if secret is _none:
            logger.warning("got BT passkey request from unknown device %s", address)
            raise DBusError("org.bluez.Error.Rejected", "unknown device")

        if not secret:
            logger.warning("got BT passkey request from device %s with unconfigured secret", address)
            raise DBusError("org.bluez.Error.Rejected", "unconfigured secret")

        await self.set_trusted(device)
        return int(secret)

    @method()
    async def RequestPinCode(self, device: "o") -> "s":
        logger.debug("BT agent RequestPinCode(%s) called", device)

        _none = {}
        address = self.address_from_device_path(device)
        secret = self.secrets_by_address.get(address, _none)
        if secret is _none:
            logger.warning("got BT pin code request from unknown device %s", address)
            raise DBusError("org.bluez.Error.Rejected", "unknown device")

        if not secret:
            logger.warning("got BT passkey request from device %s with unconfigured secret", address)
            raise DBusError("org.bluez.Error.Rejected", "unconfigured secret")

        await self.set_trusted(device)
        return secret

    @method()
    async def DisplayPasskey(self, device: "o", passkey: "u", entered: "q"):
        logger.debug("BT agent DisplayPasskey(%s, %s, %s) called", device, passkey, entered)

    @method()
    async def DisplayPinCode(self, device: "o", pincode: "s", entered: "q"):
        logger.debug("BT agent DisplayPinCode(%s, %s) called", device, pincode)

    @staticmethod
    def address_from_device_path(device_path: str) -> str:
        return ":".join(device_path.split("_")[-6:]).lower()


async def get_agent() -> Agent:
    global agent

    if agent is None:
        logger.debug("initializing BT agent")
        bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
        agent = Agent(bus)

        agent = Agent(bus)
        bus.export(BLUEZ_AGENT_PATH, agent)

        # Register agent
        introspection = await bus.introspect(BLUEZ_BUS_NAME, BLUEZ_AGENT_MANAGER_PATH)
        obj = bus.get_proxy_object(BLUEZ_BUS_NAME, BLUEZ_AGENT_MANAGER_PATH, introspection)
        agent_manager_obj = obj.get_interface(BLUEZ_AGENT_MANAGER_IFACE)

        await agent_manager_obj.call_register_agent(BLUEZ_AGENT_PATH, BLUEZ_AGENT_CAPABILITY)
        await agent_manager_obj.call_request_default_agent(BLUEZ_AGENT_PATH)

        # Make adapter discoverable/pairable
        introspection = await bus.introspect(BLUEZ_BUS_NAME, BLUEZ_ADAPTER_PATH)
        obj = bus.get_proxy_object(BLUEZ_BUS_NAME, BLUEZ_ADAPTER_PATH, introspection)
        props = obj.get_interface(BLUEZ_PROPERTIES_IFACE)

        await props.call_set(BLUEZ_ADAPTER_IFACE, "DiscoverableTimeout", Variant("u", 0))
        await props.call_set(BLUEZ_ADAPTER_IFACE, "Discoverable", Variant("b", True))
        await props.call_set(BLUEZ_ADAPTER_IFACE, "PairableTimeout", Variant("u", 0))
        await props.call_set(BLUEZ_ADAPTER_IFACE, "Pairable", Variant("b", True))

    return agent


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
        secret: str | None = None,
        cmd_timeout: int = DEFAULT_CMD_TIMEOUT,
        retry_count: int = DEFAULT_RETRY_COUNT,
        retry_delay: int = DEFAULT_RETRY_DELAY,
        **kwargs,
    ) -> None:
        self._address: str = address
        self._secret: str | None = secret
        self._cmd_timeout: int = cmd_timeout
        self._retry_count: int = retry_count
        self._retry_delay: int = retry_delay
        self._busy: bool = False
        self._notification_data: bytes | None = None

        super().__init__(**kwargs)

    def __str__(self) -> str:
        return self.get_name()

    async def handle_init(self) -> None:
        agent = await get_agent()
        agent.add_device(self._address, self._secret)

    async def handle_cleanup(self) -> None:
        agent = await get_agent()
        agent.rem_device(self._address)

    async def read(self, handle: int) -> bytes:
        return await self._run_cmd(self._read, handle=handle)

    async def write(self, handle: int, data: bytes) -> None:
        return await self._run_cmd(self._write, handle=handle, data=data)

    async def wait_notify(self, handle: int) -> bytes:
        return await self._run_cmd(self._wait_notify, handle=handle)

    async def write_wait_notify(self, handle: int, notify_handle: int, data: bytes) -> bytes:
        return await self._run_cmd(self._write_wait_notify, handle=handle, data=data, notify_handle=notify_handle)

    async def _run_cmd(self, cmd_func: Callable, **kwargs) -> bytes | None:
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
                self.error("command execution failed", exc_info=True)

                if retry <= retry_count:
                    await asyncio.sleep(self._retry_delay)
                    self.debug("retry %s/%s", retry, retry_count)
                    retry += 1
                    continue

                self.set_online(False)
                self._busy = False
                raise
            else:
                self.set_online(True)
                self._busy = False
                return response

        return None

    async def _read(self, handle: int, timeout: int) -> bytes:
        self.debug("connecting")
        async with bleak.BleakClient(self._address, timeout=timeout) as client:
            self.debug("reading from %04X", handle)
            response = bytes(await client.read_gatt_char(handle))
            self.debug("got response: %s", self.pretty_data(response))
        self.debug("disconnected")

        return response

    async def _write(self, handle: int, data: bytes, timeout: int) -> None:
        self.debug("connecting")
        async with bleak.BleakClient(self._address, timeout=timeout) as client:
            self.debug("writing at %04X: %s", handle, self.pretty_data(data))
            await client.write_gatt_char(handle, data)
        self.debug("disconnected")

    async def _wait_notify(self, handle: int, timeout: int) -> bytes:
        self.debug("connecting")
        async with bleak.BleakClient(self._address, timeout=timeout) as client:
            self.debug("waiting for notification on %04X", handle)
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
        self.debug("disconnected")

        return self._notification_data

    async def _write_wait_notify(self, handle: int, notify_handle: int, data: bytes, timeout: int) -> bytes:
        self.debug("connecting")
        async with bleak.BleakClient(self._address, timeout=timeout) as client:
            self.debug("writing at %04X: %s", handle, self.pretty_data(data))
            await client.write_gatt_char(handle, data)
            self.debug("waiting for notification on %04X", notify_handle)
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
        self.debug("disconnected")

        return self._notification_data

    def _notify_callback(self, handle: int, data: bytearray) -> None:
        self._notification_data = bytes(data)
        self.debug("got notification on %04X: %s", handle, self.pretty_data(self._notification_data))

    @staticmethod
    def pretty_data(data: bytes) -> str:
        return " ".join(map(lambda c: f"{c:02X}", data))


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
