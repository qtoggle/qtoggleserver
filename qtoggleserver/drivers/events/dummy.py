
import logging

from qtoggleserver.core.events import BaseEventHandler
from qtoggleserver.utils import json as json_utils


logger = logging.getLogger(__name__)


class DummyEventHandler(BaseEventHandler):
    async def on_event(self, event):
        logger.debug('handling %s', event)

    async def on_value_change(self, port):
        logger.debug('handling value-change for %s', port)

    async def on_port_update(self, port):
        logger.debug('handling port-update for %s', port)

    async def on_port_add(self, port):
        logger.debug('handling port-add for %s', port)

    async def on_port_remove(self, port):
        logger.debug('handling port-remove for %s', port)

    async def on_device_update(self, attrs):
        logger.debug('handling device-update with attrs %s', json_utils.dumps(attrs))

    async def on_slave_device_update(self, slave):
        logger.debug('handling slave-device-update for %s', slave)

    async def on_slave_device_add(self, slave):
        logger.debug('handling slave-device-add for %s', slave)

    async def on_slave_device_remove(self, slave):
        logger.debug('handling slave-device-remove for %s', slave)
