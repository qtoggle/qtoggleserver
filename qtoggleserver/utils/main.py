from qtoggleserver.core import events as core_events
from qtoggleserver.slaves import events as slaves_events


class AttrChangeHandler(core_events.Handler):
    """Accumulate attribute-related dep strings triggered by port/device change events.

    Listens for structural changes (port/device add, remove, update) and records which expression dependency prefixes
    may be stale. The accumulated set is consumed via `pop_pending` on each evaluation tick so that expressions
    depending on those attrs are re-evaluated.

    Dep strings produced:
    - ``$port_id:`` — for "port-add", "port-remove", "port-update"
    - ``$port_id``  — additionally, for "port-add"/"port-update", when a port's availability attribute (as reported in
      the event's params snapshot) is observed transitioning to `true` — a disabled or offline port's value is
      unavailable, so becoming enabled/online must also be treated as a *port value* dependency change, even when the
      raw value itself is unchanged
    - ``#:``        — for "device-update"
    - ``#name:``    — for "slave-device-add", "slave-device-remove", "slave-device-update"
    """

    FIRE_AND_FORGET = False

    # Attribute names whose transition to `true` makes a port's *value* newly available, and therefore must also be
    # treated as a change of the port's value dependency (`$port_id`), not just its attribute dependency (`$port_id:`).
    AVAILABILITY_ATTRS = ("enabled", "online")

    def __init__(self) -> None:
        super().__init__(name="attribute-changes")
        self._pending: set[str] = set()
        self._last_availability: dict[tuple[str, str], bool] = {}

    def pop_pending(self) -> set[str]:
        """Return the pending changes and clear the internal set."""
        pending = self._pending.copy()
        self._pending.clear()
        return pending

    async def handle_event(self, event: core_events.Event) -> None:
        if isinstance(event, (core_events.PortAdd, core_events.PortRemove, core_events.PortUpdate)):
            port_id = event.get_port().get_id()
            self._pending.add(f"${port_id}:")

            if isinstance(event, core_events.PortRemove):
                for attr_name in self.AVAILABILITY_ATTRS:
                    self._last_availability.pop((port_id, attr_name), None)
            else:
                params = await event.get_params()
                for attr_name in self.AVAILABILITY_ATTRS:
                    # Whenever one of the availability attributes becomes true, induce a `value-change`-like event so
                    # that expressions depending on this port's value are re-evaluated.
                    available = bool(params.get(attr_name))
                    if available and not self._last_availability.get((port_id, attr_name), False):
                        self._pending.add(f"${port_id}")
                    self._last_availability[(port_id, attr_name)] = available
        elif isinstance(event, core_events.DeviceUpdate):
            self._pending.add("#:")
        elif isinstance(
            event,
            (slaves_events.SlaveDeviceAdd, slaves_events.SlaveDeviceRemove, slaves_events.SlaveDeviceUpdate),
        ):
            self._pending.add(f"#{event.get_slave().get_name()}:")
