
from qtoggleserver.core import events as core_events


async def trigger_update() -> None:
    await core_events.handle_event(core_events.DeviceUpdate())
