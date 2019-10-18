
import logging
import subprocess

from qtoggleserver.conf import settings


logger = logging.getLogger(__name__)


class NetError(Exception):
    pass


def has_network_ip_support():
    return bool(settings.system.net.ip.get_cmd and settings.system.net.ip.set_cmd)


def get_ip_config():
    try:
        ip_config = subprocess.check_output(settings.system.net.ip.get_cmd, stderr=subprocess.STDOUT, shell=True)
        ip_config = ip_config.strip().decode()
        logger.debug('IP config = %s', ip_config)

    except Exception as e:
        logger.error('IP config get command failed: %s', e)
        raise NetError('IP config get command failed: {}'.format(e))

    ip_config_parts = ip_config.split()  # Expected format: ip mask gw dns
    if len(ip_config_parts) != 4:
        logger.error('invalid IP config: %s', ip_config)
        raise NetError('invalid IP config: {}'.format(ip_config))

    return {
        'ip': ip_config_parts[0],
        'mask': ip_config_parts[1],
        'gw': ip_config_parts[2],
        'dns': ip_config_parts[3]
    }


def set_ip_config(ip, mask, gw, dns):
    env = {
        'QS_IP': ip,
        'QS_MASK': mask,
        'QS_GW': gw,
        'QS_DNS': dns
    }

    try:
        subprocess.check_output(settings.system.net.ip.set_cmd, env=env, stderr=subprocess.STDOUT, shell=True)
        logger.debug('IP config set to %s/%s:%s:%s', ip, mask, gw, dns)

    except Exception as e:
        logger.error('IP config set command failed: %s', e)
        raise NetError('IP config set command failed: {}'.format(e))

    return True


def has_network_wifi_support():
    return bool(settings.system.net.wifi.get_cmd and settings.system.net.wifi.set_cmd)


def get_wifi_config():
    try:
        wifi_config = subprocess.check_output(settings.system.net.wifi.get_cmd, stderr=subprocess.STDOUT, shell=True)
        wifi_config = wifi_config.strip().decode()
        logger.debug('got WiFi config')  # Don't log WiFi details

    except Exception as e:
        logger.error('WiFi config get command failed: %s', e)
        raise NetError('WiFi config get command failed: {}'.format(e))

    wifi_config_parts = wifi_config.split()  # Expected format: ssid [psk [bssid]]
    if len(wifi_config_parts) < 1 or len(wifi_config_parts) > 3:
        logger.error('invalid WiFi config')
        raise NetError('invalid WiFi config')

    ssid = wifi_config_parts[0]
    psk = wifi_config_parts[1] if len(wifi_config_parts) >= 2 else None
    bssid = wifi_config_parts[2] if len(wifi_config_parts) >= 3 else None

    return {
        'ssid': ssid,
        'psk': psk,
        'bssid': bssid
    }


def set_wifi_config(ssid, psk, bssid):
    env = {
        'QS_SSID': ssid,
        'QS_PSK': psk,
        'QS_BSSID': bssid
    }

    try:
        subprocess.check_output(settings.system.net.wifi.set_cmd, env=env, stderr=subprocess.STDOUT, shell=True)
        logger.debug('WiFi config set')  # Don't log WiFi details

    except Exception as e:
        logger.error('WiFi config set command failed: %s', e)
        raise NetError('WiFi config set command failed: {}'.format(e))
