from qtoggleserver.core import events as core_events
from qtoggleserver.slaves import events as slaves_events


class AttrChangeHandler(core_events.Handler):
    """Accumulate attribute-related dep strings triggered by port/device change events.

    Listens for structural changes (port/device add, remove, update) and records which expression dependency prefixes
    may be stale. The accumulated set is consumed via `pop_pending` on each evaluation tick so that expressions
    depending on those attrs are re-evaluated.

    Dep strings produced:
    - ``$port_id:`` — for "port-add", "port-remove", "port-update"
    - ``#:``        — for "device-update"
    - ``#name:``    — for "slave-device-add", "slave-device-remove", "slave-device-update"
    """

    FIRE_AND_FORGET = False

    def __init__(self) -> None:
        super().__init__(name="attribute-changes")
        self._pending: set[str] = set()

    def pop_pending(self) -> set[str]:
        """Return the pending changes and clear the internal set."""
        pending = self._pending.copy()
        self._pending.clear()
        return pending

    async def handle_event(self, event: core_events.Event) -> None:
        if isinstance(event, (core_events.PortAdd, core_events.PortRemove, core_events.PortUpdate)):
            self._pending.add(f"${event.get_port().get_id()}:")
        elif isinstance(event, core_events.DeviceUpdate):
            self._pending.add("#:")
        elif isinstance(
            event,
            (slaves_events.SlaveDeviceAdd, slaves_events.SlaveDeviceRemove, slaves_events.SlaveDeviceUpdate),
        ):
            self._pending.add(f"#{event.get_slave().get_name()}:")
