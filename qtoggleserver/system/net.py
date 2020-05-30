
import subprocess

from typing import Dict, Optional

from qtoggleserver.conf import settings
from qtoggleserver.utils.cmd import run_get_cmd, run_set_cmd


class NetError(Exception):
    pass


def has_ip_support() -> bool:
    return bool(settings.system.net.ip.get_cmd and settings.system.net.ip.set_cmd)


def get_ip_config() -> Dict[str, str]:
    return run_get_cmd(
        settings.system.net.ip.get_cmd,
        cmd_name='IP config',
        exc_class=NetError,
        required_fields=[
            'address',
            'netmask',
            'gateway',
            'dns',
            'address_current',
            'netmask_current',
            'gateway_current',
            'dns_current'
        ]
    )


def set_ip_config(address: str, netmask: str, gateway: str, dns: str) -> None:
    run_set_cmd(
        settings.system.net.ip.set_cmd,
        cmd_name='IP config',
        exc_class=NetError,
        address=address,
        netmask=netmask,
        gateway=gateway,
        dns=dns
    )


def has_wifi_support() -> bool:
    return bool(settings.system.net.wifi.get_cmd and settings.system.net.wifi.set_cmd)


def get_wifi_config() -> Dict[str, str]:
    return run_get_cmd(
        settings.system.net.wifi.get_cmd,
        cmd_name='WiFi config',
        log_values=False,
        exc_class=NetError,
        required_fields=['ssid', 'psk', 'bssid', 'bssid_current', 'rssi_current']
    )


def set_wifi_config(ssid: str, psk: str, bssid: str) -> None:
    run_set_cmd(
        settings.system.net.wifi.set_cmd,
        cmd_name='WiFi config',
        exc_class=NetError,
        log_values=False,
        ssid=ssid,
        psk=psk,
        bssid=bssid
    )


def get_default_interface() -> Optional[str]:
    try:
        output = subprocess.check_output(['ip', 'route']).decode().strip()

    except Exception as e:
        raise NetError('Could not determine default route') from e

    lines = output.split('\n')
    if not lines:
        raise NetError('Could not determine default route')

    line = next((line for line in lines if line.count('default via')), None)
    if not line:
        return

    return line.split()[4]  # The 5th part is the interface
