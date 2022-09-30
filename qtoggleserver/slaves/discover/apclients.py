from __future__ import annotations

import asyncio
import datetime
import json
import logging
import time

from typing import Optional

from tornado import httpclient

from qtoggleserver.conf import settings
from qtoggleserver.core.device import attrs as core_device_attrs
from qtoggleserver.core.typing import Attributes, GenericJSONDict
from qtoggleserver.slaves import utils as salves_utils
from qtoggleserver.system import ap, dhcp, dns, net
from qtoggleserver.utils import asyncio as asyncio_utils
from qtoggleserver.utils import cmd as cmd_utils

from .exceptions import DiscoverException


_PATH_PREFIXES = ['', '/api']
_INTERFACE_CACHE_TIMEOUT = 60

logger = logging.getLogger(__name__)

_discover_task: Optional[asyncio.Task] = None
_discovered_devices: Optional[dict[str, DiscoveredDevice]] = None
_finish_timer: Optional[asyncio_utils.Timer] = None

# TODO: replace these with a common cache service with integrated timeout management
_interface: Optional[tuple[str]] = None
_interface_time: float = 0


class DiscoveredDevice:
    def __init__(
        self,
        ap_client: ap.APClient,
        scheme: str,
        port: int,
        path: str,
        admin_password: str,
        attrs: Attributes
    ) -> None:

        self.ap_client: ap.APClient = ap_client
        self.scheme: str = scheme
        self.port: int = port
        self.path: str = path
        self.admin_password: str = admin_password
        self.attrs: Attributes = attrs

    def __str__(self) -> str:
        return f'discovered AP device {self.attrs["name"]} at {self.ap_client.ip_address}'

    def to_json(self) -> GenericJSONDict:
        return {
            'mac_address': self.ap_client.mac_address,
            'ip_address': self.ap_client.ip_address,
            'timestamp': datetime.datetime.timestamp(self.ap_client.moment),
            'scheme': self.scheme,
            'hostname': self.ap_client.hostname,
            'port': self.port,
            'path': self.path,
            'admin_password': self.admin_password,
            'attrs': self.attrs
        }


def get_interface() -> Optional[str]:
    global _interface
    global _interface_time

    ap_settings = settings.slaves.discover.ap
    if ap_settings.interface:
        return ap_settings.interface

    if ap_settings.interface_cmd:
        now = time.time()
        if now - _interface_time > _INTERFACE_CACHE_TIMEOUT:
            _interface = None

        if _interface is not None:
            return _interface[0]

        result = cmd_utils.run_get_cmd(
            ap_settings.interface_cmd,
            cmd_name='AP client discover interface',
            exc_class=DiscoverException,
            required_fields=['interface']
        )

        _interface = (result.get('interface') or None,)
        _interface_time = now

        return _interface[0]


async def discover(timeout: int) -> None:
    global _discover_task
    global _discovered_devices
    global _finish_timer

    # If discover task is already running, just await it instead of starting a new one
    if _discover_task:
        await _discover_task
        return

    _discover_task = asyncio.create_task(_discover(timeout))

    if _finish_timer:
        _finish_timer.cancel()

    _finish_timer = asyncio_utils.Timer(settings.slaves.discover.ap.finish_timeout, _finish_timeout)

    devices_list = await _discover_task

    logger.debug('discovered %d devices', len(devices_list))

    _discovered_devices = {d.attrs['name']: d for d in devices_list}


async def finish() -> None:
    global _discover_task
    global _discovered_devices
    global _finish_timer

    logger.debug('finishing')

    if _discover_task:
        _discover_task.cancel()
        try:
            await _discover_task
        except Exception as e:
            logger.error('discover task error: %s', e, exc_info=True)

        _discover_task = None

    if ap.is_running():
        await ap.stop()

    if _finish_timer:
        _finish_timer.cancel()
        _finish_timer = None

    _discovered_devices = None


def get_discovered_devices() -> Optional[dict[str, DiscoveredDevice]]:
    return _discovered_devices


async def configure(discovered_device: DiscoveredDevice, attrs: Attributes) -> DiscoveredDevice:
    ap_client = discovered_device.ap_client

    # Wi-Fi settings of the real (target) network
    if 'wifi_ssid' not in attrs:
        logger.warning('no SSID/PSK available to configure device')

    if 'admin_password' not in attrs:
        logger.debug('generating password for %s', discovered_device)
        discovered_device.admin_password = salves_utils.generate_password(
            core_device_attrs.admin_password_hash,
            discovered_device.ap_client.mac_address,
            'admin'
        )

        attrs['admin_password'] = discovered_device.admin_password

        # Also set normal and view-only password, if exposed
        if 'normal_password' in discovered_device.attrs:
            attrs['normal_password'] = salves_utils.generate_password(
                core_device_attrs.admin_password_hash,
                discovered_device.ap_client.mac_address,
                'normal'
            )

        if 'viewonly_password' in discovered_device.attrs:
            attrs['viewonly_password'] = salves_utils.generate_password(
                core_device_attrs.admin_password_hash,
                discovered_device.ap_client.mac_address,
                'viewonly'
            )
    else:
        logger.debug('using supplied password for %s', discovered_device)
        discovered_device.admin_password = attrs['admin_password']

    network_configured = attrs.get('wifi_ssid') is not None
    if network_configured:
        # Find client's future IP address first
        dhcp_interface = settings.slaves.discover.dhcp_interface or net.get_default_interface()
        if not dhcp_interface:
            raise DiscoverException('No DHCP interface')

        try:
            reply = await dhcp.request(
                interface=dhcp_interface,
                timeout=settings.slaves.discover.dhcp_timeout,
                mac_address=ap_client.mac_address,
                hostname=ap_client.hostname
            )
        except dhcp.DHCPTimeout:
            logger.warning('could not determine future device IP address of %s', discovered_device)
            reply = None

        if reply:
            adjusted_ap_client = ap.APClient(
                mac_address=ap_client.mac_address,
                ip_address=reply.ip_address,
                hostname=ap_client.hostname,
                moment=ap_client.moment
            )

            discovered_device = DiscoveredDevice(
                ap_client=adjusted_ap_client,
                scheme=discovered_device.scheme,
                port=discovered_device.port,
                path=discovered_device.path,
                admin_password=discovered_device.admin_password,
                attrs=discovered_device.attrs
            )

            dns.set_custom_dns_mapping(ap_client.hostname, reply.ip_address, timeout=60)

    logger.debug('configuring %s', discovered_device)
    await ap_client.request('PATCH', f'{discovered_device.path}/device', body=attrs)
    logger.debug('%s successfully configured', discovered_device)

    # Remove configured device from discovered list
    _discovered_devices.pop(discovered_device.attrs['name'])

    if network_configured:
        logger.debug('waiting for %s to connect to new network', discovered_device)
        await asyncio.sleep(5)  # device requires at least 5 seconds to connect to new network
        start_time = time.time()
        while True:
            try:
                await discovered_device.ap_client.request(
                    'GET',
                    '/device',
                    no_log=True,
                    admin_password=discovered_device.admin_password
                )
                logger.debug('%s connected to new network', discovered_device)
                break
            except Exception:
                if time.time() - start_time > settings.slaves.long_timeout:
                    logger.error('timeout waiting for %s to connect to new network', discovered_device)
                    break

                await asyncio.sleep(1)

    return discovered_device


async def _discover(timeout: int) -> list[DiscoveredDevice]:
    logger.debug('starting discovery')

    # (Re)start our AP
    ap_settings = settings.slaves.discover.ap

    if ap.is_running():
        await ap.stop()

    ap.start(
        interface=get_interface(),
        ssid=ap_settings.ssid,
        psk=ap_settings.psk,
        own_ip=ap_settings.own_ip,
        mask_len=ap_settings.mask_len,
        start_ip=ap_settings.start_ip,
        stop_ip=ap_settings.stop_ip,
        hostapd_binary=ap_settings.hostapd_binary,
        hostapd_cli_binary=ap_settings.hostapd_cli_binary,
        dnsmasq_binary=ap_settings.dnsmasq_binary,
        hostapd_log=ap_settings.hostapd_log,
        dnsmasq_log=ap_settings.dnsmasq_log
    )

    # Wait for clients to connect to our AP
    try:
        for _ in range(timeout):
            await asyncio.sleep(1)
            await ap.update()
            if not ap.is_running():
                raise DiscoverException('AP stopped unexpectedly')

        clients = ap.get_clients()
    except asyncio.CancelledError:
        logger.debug('discover task cancelled')
        clients = []

    for client in clients:
        logger.debug(
            'discovered AP client "%s" with IP %s and MAC %s',
            client.hostname,
            client.ip_address,
            client.mac_address
        )

    if not clients:
        logger.debug('no clients discovered')

    # See if we're really dealing with qToggle devices
    discovered_devices = []
    for client in clients:
        try:
            discovered_devices.append(await _query_client(client))
        except Exception as e:
            logger.error('client query failed: %s', e, exc_info=True)

    return discovered_devices


async def _finish_timeout() -> None:
    global _finish_timer

    logger.debug('finish timeout')
    _finish_timer = None
    await finish()


async def _query_client(ap_client: ap.APClient) -> Optional[DiscoveredDevice]:
    logger.debug('querying %s', ap_client)

    for prefix in _PATH_PREFIXES:
        try:
            attrs = await ap_client.request('GET', f'{prefix}/device')
            break
        except (httpclient.HTTPError, json.JSONDecodeError):
            continue
    else:
        raise DiscoverException('Could not find device API endpoint')

    if not isinstance(attrs, dict):
        logger.error('%s has returned invalid device attributes response', ap_client)
        return None

    for field in ['name', 'vendor', 'version']:
        if field not in attrs:
            logger.error('%s has returned invalid device attributes response', ap_client)
            return None

    return DiscoveredDevice(
        ap_client=ap_client,
        scheme='http',  # TODO: add support for HTTPS schemes
        port=80,
        path=prefix,
        admin_password='',
        attrs=attrs
    )


async def init() -> None:
    pass


async def cleanup() -> None:
    await finish()
