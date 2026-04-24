from qtoggleserver.conf import settings
from qtoggleserver.core import ports as core_ports
from qtoggleserver.core.device import attrs as core_device_attrs
from qtoggleserver.core.expressions import EvalContext
from qtoggleserver.slaves import devices as slaves_devices


async def build_context(now_ms: int) -> EvalContext:
    port_values = {}
    port_attrs = {}
    for port in core_ports.get_all():
        if not port.is_enabled():
            continue

        port_id = port.get_id()
        port_values[port_id] = port.get_last_value()
        port_attrs[port_id] = await port.get_attrs()

    device_attrs = await core_device_attrs.get_attrs()

    # Add slave device attrs
    if settings.slaves.enabled:
        for slave in slaves_devices.get_all():
            slave_name = slave.get_name()
            slave_attrs = slave.get_cached_attrs()
            device_attrs.update(
                {f"{slave_name}.{attr_name}": attr_value for attr_name, attr_value in slave_attrs.items()}
            )

    return EvalContext(port_values, port_attrs, device_attrs, now_ms)
