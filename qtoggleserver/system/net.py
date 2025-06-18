import subprocess

from qtoggleserver.conf import settings
from qtoggleserver.utils.cmd import run_get_cmd, run_set_cmd


WIFI_RSSI_EXCELLENT = -50
WIFI_RSSI_GOOD = -60
WIFI_RSSI_FAIR = -70


class NetError(Exception):
    pass


def has_ip_support() -> bool:
    return bool(settings.system.net.ip.get_cmd and settings.system.net.ip.set_cmd)


def get_ip_config() -> dict[str, str]:
    assert settings.system.net.ip.get_cmd

    return run_get_cmd(
        settings.system.net.ip.get_cmd,
        cmd_name="IP config",
        exc_class=NetError,
        required_fields=[
            "address",
            "netmask",
            "gateway",
            "dns",
            "address_current",
            "netmask_current",
            "gateway_current",
            "dns_current",
        ],
    )


def set_ip_config(address: str, netmask: str, gateway: str, dns: str) -> None:
    assert settings.system.net.ip.set_cmd

    run_set_cmd(
        settings.system.net.ip.set_cmd,
        cmd_name="IP config",
        exc_class=NetError,
        address=address,
        netmask=netmask,
        gateway=gateway,
        dns=dns,
    )


def reset_ip_config() -> None:
    set_ip_config(address="", netmask="", gateway="", dns="")


def has_wifi_support() -> bool:
    return bool(settings.system.net.wifi.get_cmd and settings.system.net.wifi.set_cmd)


def get_wifi_config() -> dict[str, str]:
    assert settings.system.net.wifi.get_cmd

    result = run_get_cmd(
        settings.system.net.wifi.get_cmd,
        cmd_name="Wi-Fi config",
        log_values=False,
        exc_class=NetError,
        required_fields=["ssid", "psk", "bssid", "bssid_current", "rssi_current"],
    )

    if result["rssi_current"]:
        rssi = int(result["rssi_current"])
        if rssi >= WIFI_RSSI_EXCELLENT:
            strength = 3
        elif rssi >= WIFI_RSSI_GOOD:
            strength = 2
        elif rssi >= WIFI_RSSI_FAIR:
            strength = 1
        else:
            strength = 0

        result["signal_strength_current"] = str(strength)
    else:
        result["signal_strength_current"] = "0"

    return result


def set_wifi_config(ssid: str, psk: str, bssid: str) -> None:
    assert settings.system.net.wifi.set_cmd

    run_set_cmd(
        settings.system.net.wifi.set_cmd,
        cmd_name="Wi-Fi config",
        exc_class=NetError,
        log_values=False,
        ssid=ssid,
        psk=psk,
        bssid=bssid,
    )


def reset_wifi_config() -> None:
    set_wifi_config(ssid="", psk="", bssid="")


def get_default_interface() -> str | None:
    try:
        output = subprocess.check_output(["ip", "route"]).decode().strip()
    except Exception as e:
        raise NetError("Could not determine default route") from e

    lines = output.split("\n")
    if not lines:
        raise NetError("Could not determine default route")

    line = next((line for line in lines if line.count("default via")), None)
    if not line:
        return None

    return line.split()[4]  # the 5th part is the interface
