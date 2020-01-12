
from qtoggleserver.core import events as core_events


def trigger_update() -> None:
    core_events.handle_event(core_events.DeviceUpdate())
