
from qtoggleserver.core import events as core_events
from qtoggleserver.core import sessions as core_sessions


def trigger_update():
    core_sessions.push(core_events.DeviceUpdate())
