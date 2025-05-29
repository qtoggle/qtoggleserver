from .base import Event, Handler
from .device import DeviceEvent, DeviceUpdate, FullUpdate
from .handlers import cleanup as cleanup_handlers
from .handlers import disable, enable, register_handler, trigger
from .handlers import init as init_handlers
from .port import PortAdd, PortEvent, PortRemove, PortUpdate, ValueChange


__all__ = [
    "DeviceEvent",
    "DeviceUpdate",
    "Event",
    "FullUpdate",
    "Handler",
    "PortAdd",
    "PortEvent",
    "PortRemove",
    "PortUpdate",
    "ValueChange",
    "disable",
    "enable",
    "register_handler",
]


async def trigger_full_update() -> None:
    await trigger(FullUpdate())


async def init() -> None:
    await init_handlers()


async def cleanup() -> None:
    await cleanup_handlers()
