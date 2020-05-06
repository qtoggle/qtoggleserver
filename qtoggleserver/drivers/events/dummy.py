
import logging

from typing import Dict, Tuple

from qtoggleserver.core import events as core_events
from qtoggleserver.core import ports as core_ports
from qtoggleserver.core.typing import Attribute, Attributes, NullablePortValue
from qtoggleserver.lib import filtereventhandler
from qtoggleserver.slaves import devices as slaves_devices


logger = logging.getLogger(__name__)


class DummyEventHandler(filtereventhandler.FilterEventHandler):
    async def on_event(self, event: core_events.Event) -> None:
        logger.debug('handling %s', event)

    async def on_value_change(
        self,
        event: core_events.Event,
        port: core_ports.BasePort,
        old_value: NullablePortValue,
        new_value: NullablePortValue,
        attrs: Attributes
    ) -> None:

        logger.debug('handling value-change for %s', port)

    async def on_port_update(
        self,
        event: core_events.Event,
        port: core_ports.BasePort,
        old_attrs: Attributes,
        new_attrs: Attributes,
        changed_attrs: Dict[str, Tuple[Attribute, Attribute]],
        added_attrs: Attributes,
        removed_attrs: Attributes
    ) -> None:

        logger.debug('handling port-update for %s', port)

    async def on_port_add(self, event: core_events.Event, port: core_ports.BasePort, attrs: Attributes) -> None:
        logger.debug('handling port-add for %s', port)

    async def on_port_remove(self, event: core_events.Event, port: core_ports.BasePort, attrs: Attributes) -> None:
        logger.debug('handling port-remove for %s', port)

    async def on_device_update(
        self,
        event: core_events.Event,
        old_attrs: Attributes,
        new_attrs: Attributes,
        changed_attrs: Dict[str, Tuple[Attribute, Attribute]],
        added_attrs: Attributes,
        removed_attrs: Attributes
    ) -> None:

        logger.debug('handling device-update')

    async def on_full_update(self, event: core_events.Event) -> None:
        logger.debug('handling full-update')

    async def on_slave_device_update(
        self,
        event: core_events.Event,
        slave: slaves_devices.Slave,
        old_attrs: Attributes,
        new_attrs: Attributes,
        changed_attrs: Dict[str, Tuple[Attribute, Attribute]],
        added_attrs: Attributes,
        removed_attrs: Attributes
    ) -> None:

        logger.debug('handling slave-device-update for %s', slave)

    async def on_slave_device_add(
        self,
        event: core_events.Event,
        slave: slaves_devices.Slave,
        attrs: Attributes
    ) -> None:

        logger.debug('handling slave-device-add for %s', slave)

    async def on_slave_device_remove(
        self,
        event: core_events.Event,
        slave: slaves_devices.Slave, attrs: Attributes
    ) -> None:

        logger.debug('handling slave-device-remove for %s', slave)
