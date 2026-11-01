from qtoggleserver.core import events as core_events
from qtoggleserver.core.expressions.base import VALUE_AVAILABILITY_ATTRS
from qtoggleserver.slaves import events as slaves_events


class AttrChangeHandler(core_events.Handler):
    """Flag the expression deps that port, device and slave events change, through `core.main.add_dep_change()`.

    Listens for structural changes (port/device add, remove, update), so that expressions depending on the attrs, or
    on the availability, of those objects are re-evaluated.

    Dep strings produced:
    - ``$port_id:`` — for "port-add", "port-remove", "port-update"
    - ``$port_id``  — additionally, for "port-add"/"port-remove"/"port-update", whenever a port's availability
      (`enabled`/`online`) transitions, in either direction, relative to its last known state — so that value
      expressions and functions like `AVAILABLE()`/`DEFAULT()` pick up the new state
    - ``#:``        — for "device-update"
    - ``#name:``    — for "slave-device-add", "slave-device-remove", "slave-device-update"
    """

    FIRE_AND_FORGET = False

    def __init__(self) -> None:
        super().__init__(name="attribute-changes")
        self._last_availability: dict[tuple[str, str], bool] = {}

    async def handle_event(self, event: core_events.Event) -> None:
        from qtoggleserver.core import main as core_main  # imported here, as core.main imports this module

        if isinstance(event, (core_events.PortAdd, core_events.PortRemove, core_events.PortUpdate)):
            port_id = event.get_port().get_id()
            core_main.add_dep_change(f"${port_id}:")

            if isinstance(event, core_events.PortRemove):
                for attr_name in VALUE_AVAILABILITY_ATTRS:
                    # Whenever one of the availability attributes changes, induce a `value-change`-like event so that
                    # expressions depending on this port's value are re-evaluated.
                    was_available = self._last_availability.pop((port_id, attr_name), False)
                    if was_available:
                        core_main.add_dep_change(f"${port_id}")
            else:
                # Also covers "port-add" — see class docstring.
                params = event.get_params()
                for attr_name in VALUE_AVAILABILITY_ATTRS:
                    # Whenever one of the availability attributes changes, induce a `value-change`-like event so that
                    # expressions depending on this port's value are re-evaluated.
                    available = bool(params.get(attr_name))
                    if available != self._last_availability.get((port_id, attr_name), False):
                        core_main.add_dep_change(f"${port_id}")
                    self._last_availability[(port_id, attr_name)] = available
        elif isinstance(event, core_events.DeviceUpdate):
            core_main.add_dep_change("#:")
        elif isinstance(
            event,
            (slaves_events.SlaveDeviceAdd, slaves_events.SlaveDeviceRemove, slaves_events.SlaveDeviceUpdate),
        ):
            core_main.add_dep_change(f"#{event.get_slave().get_name()}:")
