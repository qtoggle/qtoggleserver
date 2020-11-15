
from qtoggleserver.core import events as core_events


async def trigger_update() -> None:
    await core_events.trigger(core_events.DeviceUpdate())
