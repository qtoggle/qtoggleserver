
from typing import Dict

from qtoggleserver.conf import settings
from qtoggleserver.utils.cmd import run_get_cmd, run_set_cmd


class NetError(Exception):
    pass


def has_network_ip_support() -> bool:
    return bool(settings.system.net.ip.get_cmd and settings.system.net.ip.set_cmd)


def get_ip_config() -> Dict[str, str]:
    return run_get_cmd(
        settings.system.net.ip.get_cmd,
        cmd_name='IP config',
        exc_class=NetError,
        required_fields=['ip', 'mask', 'gw', 'dns']
    )


def set_ip_config(ip: str, mask: str, gw: str, dns: str) -> None:
    run_set_cmd(
        settings.system.net.ip.set_cmd,
        cmd_name='IP config',
        exc_class=NetError,
        ip=ip,
        mask=mask,
        gw=gw,
        dns=dns
    )


def has_network_wifi_support() -> bool:
    return bool(settings.system.net.wifi.get_cmd and settings.system.net.wifi.set_cmd)


def get_wifi_config() -> Dict[str, str]:
    return run_get_cmd(
        settings.system.net.wifi.get_cmd,
        cmd_name='WiFi config',
        log_values=False,
        exc_class=NetError,
        required_fields=['ssid', 'psk', 'bssid']
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
