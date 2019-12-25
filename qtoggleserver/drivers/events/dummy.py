
import logging

from qtoggleserver.core.events import BaseEventHandler


logger = logging.getLogger(__name__)


class DummyEventHandler(BaseEventHandler):
    async def on_event(self, event):
        logger.debug('handling %s', event)

    async def on_value_change(self, event, port, old_value, new_value, attrs):
        logger.debug('handling value-change for %s', port)

    async def on_port_update(self, event, port, old_attrs, new_attrs, changed_attrs, added_attrs, removed_attrs):
        logger.debug('handling port-update for %s', port)

    async def on_port_add(self, event, port, attrs):
        logger.debug('handling port-add for %s', port)

    async def on_port_remove(self, event, port, attrs):
        logger.debug('handling port-remove for %s', port)

    async def on_device_update(self, event, old_attrs, new_attrs, changed_attrs, added_attrs, removed_attrs):
        logger.debug('handling device-update')

    async def on_slave_device_update(self, event, slave, old_attrs, new_attrs, changed_attrs, added_attrs, removed_attrs):
        logger.debug('handling slave-device-update for %s', slave)

    async def on_slave_device_add(self, event, slave, attrs):
        logger.debug('handling slave-device-add for %s', slave)

    async def on_slave_device_remove(self, event, slave, attrs):
        logger.debug('handling slave-device-remove for %s', slave)
