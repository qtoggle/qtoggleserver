
from qtoggleserver.core import events as core_events
from qtoggleserver.core import sessions as core_sessions


def trigger_update():
    event = core_events.DeviceUpdate()
    core_sessions.push(event)
    core_events.handle_event(event)
