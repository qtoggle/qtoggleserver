
from .base import Event, Handler
from .device import DeviceEvent, DeviceUpdate, FullUpdate
from .handlers import trigger, register_handler, enable, disable
from .handlers import init as init_handlers, cleanup as cleanup_handlers
from .port import PortEvent, PortAdd, PortRemove, PortUpdate, ValueChange


async def trigger_full_update() -> None:
    await trigger(FullUpdate())


async def init() -> None:
    await init_handlers()


async def cleanup() -> None:
    await cleanup_handlers()
