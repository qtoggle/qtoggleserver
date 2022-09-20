from .base import Event, Handler
from .device import DeviceEvent, DeviceUpdate, FullUpdate
from .handlers import cleanup as cleanup_handlers
from .handlers import disable, enable
from .handlers import init as init_handlers
from .handlers import register_handler, trigger
from .port import PortAdd, PortEvent, PortRemove, PortUpdate, ValueChange


async def trigger_full_update() -> None:
    await trigger(FullUpdate())


async def init() -> None:
    await init_handlers()


async def cleanup() -> None:
    await cleanup_handlers()
