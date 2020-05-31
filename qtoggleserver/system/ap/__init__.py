
import asyncio
import datetime
import logging

from typing import List, Optional

from .client import APClient
from .dnsmasq import DNSMasq
from .exceptions import APException
from .hostapd import HostAPD


logger = logging.getLogger(__name__)

_hostapd: Optional[HostAPD] = None
_dnsmasq: Optional[DNSMasq] = None


async def update() -> None:
    global _hostapd
    global _dnsmasq

    if _hostapd and not _hostapd.is_alive():
        logger.warning('hostapd died unexpectedly')
        await _hostapd.stop()
        _hostapd = None

    if _dnsmasq and not _dnsmasq.is_alive():
        logger.warning('dnsmasq died unexpectedly')
        await _dnsmasq.stop()
        _dnsmasq = None

    if None in [_hostapd, _dnsmasq]:
        # Ensure both daemons are stopped
        if _hostapd:
            logger.warning('dnsmasq is stopped but hostapd is running')
            await _hostapd.stop()
            _hostapd = None

        if _dnsmasq:
            logger.warning('hostapd is stopped but dnsmasq is running')
            await _dnsmasq.stop()
            _dnsmasq = None


def is_running() -> bool:
    return (_hostapd is not None) or (_dnsmasq is not None)


def start(
    interface: str,
    ssid: str,
    psk: Optional[str],
    own_ip: str,
    mask_len: int,
    start_ip: str,
    stop_ip: str,
    hostapd_binary: Optional[str] = None,
    hostapd_cli_binary: Optional[str] = None,
    dnsmasq_binary: Optional[str] = None,
    hostapd_log: Optional[str] = None,
    dnsmasq_log: Optional[str] = None
) -> None:

    global _hostapd
    global _dnsmasq

    logger.debug('starting')

    if is_running():
        raise APException('AP already started')

    if HostAPD.is_already_running():
        raise APException('The hostapd daemon is already running')
    if DNSMasq.is_already_running():
        raise APException('The dnsmasq daemon is already running')

    _hostapd = HostAPD(
        interface=interface,
        ssid=ssid,
        psk=psk,
        hostapd_binary=hostapd_binary,
        hostapd_cli_binary=hostapd_cli_binary,
        hostapd_log=hostapd_log
    )

    _dnsmasq = DNSMasq(
        interface=interface,
        own_ip=own_ip,
        mask_len=mask_len,
        start_ip=start_ip,
        stop_ip=stop_ip,
        dnsmasq_binary=dnsmasq_binary,
        dnsmasq_log=dnsmasq_log
    )

    _dnsmasq.start()
    _hostapd.start()

    logger.debug('started')


async def stop() -> None:
    global _hostapd
    global _dnsmasq

    logger.debug('stopping')

    if not is_running():
        raise APException('AP not started')

    await _hostapd.stop()
    await _dnsmasq.stop()

    _hostapd = None
    _dnsmasq = None

    logger.debug('stopped')


def get_clients() -> List[APClient]:
    if not is_running():
        raise APException('AP not started')

    leases = _dnsmasq.get_leases()

    return [APClient(
        mac_address=lease['mac_address'].upper(),
        ip_address=lease['ip_address'],
        hostname=lease['hostname'],
        moment=datetime.datetime.utcfromtimestamp(lease['timestamp'])
    ) for lease in leases]
