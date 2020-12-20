
import logging

from qtoggleserver.conf import settings
from qtoggleserver.core.api.funcs import backup as backup_api_funcs
from qtoggleserver.core.api.funcs import device as device_api_funcs
from qtoggleserver.core.api.funcs import firmware as firmware_api_funcs
from qtoggleserver.core.api.funcs import ports as ports_api_funcs
from qtoggleserver.core.api.funcs import reverse as reverse_api_funcs
from qtoggleserver.core.api.funcs import various as various_api_funcs
from qtoggleserver.core.api.funcs import webhooks as webhooks_api_funcs
from qtoggleserver.frontend.api import funcs as frontend_api_funcs
from qtoggleserver.slaves.api import funcs as slaves_api_funcs
from qtoggleserver.system.api import funcs as system_api_funcs

from .base import APIHandler, BaseHandler, NoSuchFunction


logger = logging.getLogger(__name__)


class NoSuchFunctionHandler(BaseHandler):
    pass


class DeviceHandler(APIHandler):
    async def get(self) -> None:
        await self.call_api_func(device_api_funcs.get_device)

    async def put(self) -> None:
        await self.call_api_func(device_api_funcs.put_device, default_status=204)

    async def patch(self) -> None:
        await self.call_api_func(device_api_funcs.patch_device, default_status=204)


class ResetHandler(APIHandler):
    async def post(self) -> None:
        await self.call_api_func(various_api_funcs.post_reset, default_status=204)


class FirmwareHandler(APIHandler):
    async def get(self) -> None:
        await self.call_api_func(firmware_api_funcs.get_firmware)

    async def patch(self) -> None:
        await self.call_api_func(firmware_api_funcs.patch_firmware, default_status=204)


class BackupEndpointsHandler(APIHandler):
    async def get(self) -> None:
        await self.call_api_func(backup_api_funcs.get_backup_endpoints)


class AccessHandler(APIHandler):
    async def get(self) -> None:
        await self.call_api_func(various_api_funcs.get_access)


class SlaveDevicesHandler(APIHandler):
    async def get(self) -> None:
        await self.call_api_func(slaves_api_funcs.get_slave_devices)

    async def put(self) -> None:
        await self.call_api_func(slaves_api_funcs.put_slave_devices, default_status=204)

    async def post(self) -> None:
        await self.call_api_func(slaves_api_funcs.post_slave_devices, default_status=201)


class SlaveDeviceHandler(APIHandler):
    async def patch(self, name: str) -> None:
        await self.call_api_func(slaves_api_funcs.patch_slave_device, name=name, default_status=204)

    async def delete(self, name: str) -> None:
        await self.call_api_func(slaves_api_funcs.delete_slave_device, name=name, default_status=204)


class SlaveDeviceEventsHandler(APIHandler):
    AUTH_ENABLED = False  # We'll take care of the authentication inside API call functions

    async def post(self, name: str) -> None:
        await self.call_api_func(slaves_api_funcs.post_slave_device_events, name=name, default_status=204)


class SlaveDeviceForwardHandler(APIHandler):
    async def get(self, name: str, path: str) -> None:
        await self.call_api_func(slaves_api_funcs.slave_device_forward, name=name, path=path)

    post = patch = put = delete = get


class DiscoveredHandler(APIHandler):
    async def get(self) -> None:
        await self.call_api_func(slaves_api_funcs.get_discovered)

    async def delete(self) -> None:
        await self.call_api_func(slaves_api_funcs.delete_discovered, default_status=204)


class DiscoveredDeviceHandler(APIHandler):
    async def patch(self, name: str) -> None:
        await self.call_api_func(slaves_api_funcs.patch_discovered_device, name=name)


class PortsHandler(APIHandler):
    async def get(self) -> None:
        await self.call_api_func(ports_api_funcs.get_ports)

    async def put(self) -> None:
        await self.call_api_func(ports_api_funcs.put_ports, default_status=204)

    async def post(self) -> None:
        if not settings.core.virtual_ports:
            raise NoSuchFunction()

        await self.call_api_func(ports_api_funcs.post_ports, default_status=201)


class PortHandler(APIHandler):
    async def delete(self, port_id: str) -> None:
        if not settings.core.virtual_ports:
            raise NoSuchFunction()

        await self.call_api_func(ports_api_funcs.delete_port, port_id=port_id, default_status=204)

    async def patch(self, port_id: str) -> None:
        await self.call_api_func(ports_api_funcs.patch_port, port_id=port_id, default_status=204)


class PortValueHandler(APIHandler):
    async def get(self, port_id: str) -> None:
        await self.call_api_func(ports_api_funcs.get_port_value, port_id=port_id)

    async def patch(self, port_id: str) -> None:
        await self.call_api_func(ports_api_funcs.patch_port_value, port_id=port_id, default_status=204)


class PortSequenceHandler(APIHandler):
    async def patch(self, port_id: str) -> None:
        await self.call_api_func(ports_api_funcs.patch_port_sequence, port_id=port_id, default_status=204)


class PortHistoryHandler(APIHandler):
    async def get(self, port_id: str) -> None:
        await self.call_api_func(ports_api_funcs.get_port_history, port_id=port_id)

    async def delete(self, port_id: str) -> None:
        await self.call_api_func(ports_api_funcs.delete_port_history, port_id=port_id, default_status=204)


class WebhooksHandler(APIHandler):
    async def get(self) -> None:
        await self.call_api_func(webhooks_api_funcs.get_webhooks)

    async def put(self) -> None:
        await self.call_api_func(webhooks_api_funcs.put_webhooks, default_status=204)


class ListenHandler(APIHandler):
    async def get(self) -> None:
        await self.call_api_func(various_api_funcs.get_listen)


class ReverseHandler(APIHandler):
    async def get(self) -> None:
        await self.call_api_func(reverse_api_funcs.get_reverse)

    async def put(self) -> None:
        await self.call_api_func(reverse_api_funcs.put_reverse, default_status=204)


class DashboardPanelsHandler(APIHandler):
    async def get(self) -> None:
        await self.call_api_func(frontend_api_funcs.get_panels)

    async def put(self) -> None:
        await self.call_api_func(frontend_api_funcs.put_panels, default_status=204)


class PrefsHandler(APIHandler):
    async def get(self) -> None:
        await self.call_api_func(frontend_api_funcs.get_prefs)

    async def put(self) -> None:
        await self.call_api_func(frontend_api_funcs.put_prefs, default_status=204)


class FrontendHandler(APIHandler):
    async def get(self) -> None:
        await self.call_api_func(frontend_api_funcs.get_frontend)

    async def put(self) -> None:
        await self.call_api_func(frontend_api_funcs.put_frontend, default_status=204)


class SystemHandler(APIHandler):
    async def get(self) -> None:
        await self.call_api_func(system_api_funcs.get_system)

    async def put(self) -> None:
        await self.call_api_func(system_api_funcs.put_system, default_status=204)
