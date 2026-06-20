import abc
import asyncio
import functools
import hashlib
import logging

from collections.abc import Callable
from typing import Any, cast

from qtoggleserver.core import events as core_events
from qtoggleserver.core import ports as core_ports
from qtoggleserver.core.typing import GenericJSONDict
from qtoggleserver.utils import asyncio as asyncio_utils
from qtoggleserver.utils import logging as logging_utils
from qtoggleserver.utils import runner as runner_utils
from qtoggleserver.utils.driver_params import DriverParamsMixin

from .exceptions import NotOurPort


logger = logging.getLogger(__package__)


class Peripheral(DriverParamsMixin, logging_utils.LoggableMixin, metaclass=abc.ABCMeta):
    RUNNER_CLASS = runner_utils.ThreadedRunner
    RUNNER_QUEUE_SIZE = 64

    logger = logger

    def __init__(
        self,
        *,
        name: str | None = None,
        display_name: str = "",
        force_enabled: bool | None = None,
        static: bool = False,
        **kwargs,
    ) -> None:
        self._name: str | None = name
        self._id: str = name or ""  # name will always be used as id, if supplied
        if not self._id:
            sorted_params = self._sorted_tuples_dict(self.get_params())
            auto_id_to_hash = f"{self.__class__.__module__}.{self.__class__.__name__}:{name}:{sorted_params}"
            self._id = f"peripheral_{hashlib.sha256(auto_id_to_hash.encode()).hexdigest()[:8]}"
        self._display_name: str = display_name or ""
        self._force_enabled: bool | None = force_enabled
        self._static: bool = static

        self._ports_by_id: dict[str, PeripheralPort] = {}
        self._enabled: bool = False
        self._online: bool = False
        self._runner: runner_utils.ThreadedRunner | None = None
        self._port_update_task: asyncio.Task | None = None

        logging_utils.LoggableMixin.__init__(self, self.get_id(), self.logger)

    @staticmethod
    def _sorted_tuples_dict(params: dict[str, Any]) -> tuple:
        def dict_reorder(d: dict) -> tuple:
            return tuple((k, dict_reorder(v)) if isinstance(v, dict) else v for k, v in sorted(d.items()))

        return dict_reorder(params)

    def __str__(self) -> str:
        return f"peripheral {self.get_id()}"

    def get_id(self) -> str:
        return self._id

    def get_name(self) -> str | None:
        return self._name

    def get_display_name(self) -> str:
        return self._display_name

    def set_display_name(self, display_name: str) -> None:
        self._display_name = display_name

    def is_static(self) -> bool:
        return self._static

    def get_force_enabled(self) -> bool | None:
        return self._force_enabled

    def set_force_enabled(self, force_enabled: bool | None) -> None:
        self._force_enabled = force_enabled

    def to_json(self) -> GenericJSONDict:
        return dict(
            driver=self.get_driver(),
            id=self.get_id(),
            static=self.is_static(),
            name=self.get_name(),
            display_name=self.get_display_name(),
            enabled=self.is_enabled(),
            force_enabled=self.get_force_enabled(),
            params=self.get_params(),
            online=self.is_online(),
        )

    async def get_port_args(self) -> list[dict[str, Any]]:
        port_args = await self.make_port_args()

        # Transform port classes to dicts with drivers
        transformed_port_args: list[dict[str, Any]] = [
            {"driver": pa} if isinstance(pa, type) else pa for pa in port_args
        ]

        # Supply the peripheral argument
        for pa in transformed_port_args:
            pa.setdefault("peripheral", self)

        return transformed_port_args

    @abc.abstractmethod
    async def make_port_args(self) -> list[dict[str, Any] | type[PeripheralPort]]:
        raise NotImplementedError()

    async def init_ports(self) -> None:
        if self._force_enabled is False:
            self.debug("peripheral is explicitly disabled, skipping port initialization")
            await self.disable()
            return

        port_args = await self.get_port_args()
        loaded_ports = await core_ports.load(port_args)
        self._ports_by_id = {cast(PeripheralPort, p).get_initial_id(): p for p in loaded_ports}

        # If no port has been loaded, there's no way for the user to enable the peripheral (via ports) so we have to
        # enable it manually, here.
        if not loaded_ports:
            await self.enable()

        await self._apply_force_enabled()

    async def cleanup_ports(self, persisted_data: bool) -> None:
        tasks = [asyncio.create_task(port.remove(persisted_data=persisted_data)) for port in self._ports_by_id.values()]
        if tasks:
            await asyncio.wait(tasks)

    async def add_port(self, port_args: dict[str, Any]) -> PeripheralPort:
        # Supply the peripheral argument
        port_args = port_args.copy()
        port_args.setdefault("peripheral", self)

        port = cast(PeripheralPort, (await core_ports.load([port_args]))[0])
        self._ports_by_id[port.get_initial_id()] = port
        return port

    async def remove_port(self, port_id: str, persisted_data: bool = False) -> None:
        if self._name and port_id.startswith(f"{self._name}."):
            port_id = port_id[len(self._name) + 1 :]

        try:
            port = self._ports_by_id.pop(port_id)
        except KeyError:
            raise NotOurPort(f"Port {port_id} does not belong to {self}") from None

        await port.remove(persisted_data=persisted_data)

    def get_ports(self) -> list[PeripheralPort]:
        return list(self._ports_by_id.values())

    def get_port(self, port_id: str) -> PeripheralPort | None:
        return self._ports_by_id.get(port_id)

    def is_enabled(self) -> bool:
        return self._enabled

    async def enable(self) -> None:
        if self._enabled:
            return
        if self._force_enabled is False:
            return

        self._enabled = True
        await self.handle_enable()
        self.debug("peripheral enabled")

    async def disable(self) -> None:
        if not self._enabled:
            return
        if self._force_enabled is True:
            return

        self._enabled = False
        await self.handle_disable()
        self.debug("peripheral disabled")

    async def check_disabled(self, exclude_port: PeripheralPort | None = None) -> None:
        if not self._enabled:
            return
        if self._force_enabled is True:
            return

        for port in self._ports_by_id.values():
            if port.is_enabled() and port != exclude_port:
                break
        else:
            self.debug("all ports are disabled, disabling peripheral")
            await self.disable()
            await self.trigger_update()

    async def _apply_force_enabled(self) -> None:
        if self._force_enabled is True:
            await self.enable()
        elif self._force_enabled is False:
            await self.disable()

    def is_online(self) -> bool:
        return self._enabled and self._online

    def set_online(self, online: bool) -> None:
        if online and not self._online:
            self.debug("is online")
            self._online = online
            try:
                self.handle_online()
            except Exception:
                self.error("handle_online failed", exc_info=True)
            self.trigger_update_fire_and_forget()
        elif not online and self._online:
            self.debug("is offline")
            self._online = online
            try:
                self.handle_offline()
            except Exception:
                self.error("handle_offline failed", exc_info=True)
            self.trigger_update_fire_and_forget()

    def handle_offline(self) -> None:
        self.trigger_port_update_fire_and_forget()

    def handle_online(self) -> None:
        self.trigger_port_update_fire_and_forget()

    async def trigger_port_update(self, save: bool = False) -> None:
        self._port_update_task = None
        for port in self._ports_by_id.values():
            port.invalidate_attrs()
            if port.is_enabled():
                await port.trigger_update()
                if save:
                    port.save_asap()

    def trigger_port_update_fire_and_forget(self, save: bool = False) -> None:
        if self._port_update_task:
            return  # already scheduled

        self._port_update_task = asyncio.create_task(self.trigger_port_update(save))

    def trigger_update_fire_and_forget(self) -> None:
        asyncio_utils.fire_and_forget(self.trigger_update())

    def get_runner(self) -> runner_utils.ThreadedRunner:
        if self._runner is None:
            self._runner = self.make_runner()

        return self._runner

    def make_runner(self) -> runner_utils.ThreadedRunner:
        self.debug("starting threaded runner")
        runner = self.RUNNER_CLASS(queue_size=self.RUNNER_QUEUE_SIZE)
        runner.start()

        return runner

    async def run_threaded(self, func: Callable, *args, **kwargs) -> Any:
        future = asyncio.get_running_loop().create_future()

        def callback(result: Any, exception: Exception | None) -> None:
            if future.cancelled():
                return

            if exception:
                future.set_exception(exception)
            else:
                future.set_result(result)

        runner = self.get_runner()
        runner.schedule_func(functools.partial(func, *args, **kwargs), callback)

        return await future

    async def trigger_add(self) -> None:
        from .events import PeripheralAdd

        await core_events.trigger(PeripheralAdd(self))

    async def trigger_remove(self) -> None:
        from .events import PeripheralRemove

        await core_events.trigger(PeripheralRemove(self))

    async def trigger_update(self) -> None:
        from .events import PeripheralUpdate

        await core_events.trigger(PeripheralUpdate(self))

    async def handle_enable(self) -> None:
        pass

    async def handle_disable(self) -> None:
        pass

    async def handle_init(self) -> None:
        pass

    async def handle_cleanup(self) -> None:
        if self._port_update_task:
            await self._port_update_task

        if self._runner:
            self.debug("stopping threaded runner")
            await self._runner.stop()
            self.debug("threaded runner stopped")


# This needs to be imported here to avoid circular import issues
from .peripheralport import PeripheralPort  # noqa: E402
