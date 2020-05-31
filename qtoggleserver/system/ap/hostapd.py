
import asyncio
import logging
import psutil
import re
import subprocess
import tempfile
import time

from typing import Optional, TextIO

from .exceptions import APException


BINARY = 'hostapd'
CLI_BINARY = 'hostapd_cli'

CONF_TEMPLATE = (
    'ssid={ssid}\n'
    'wpa_passphrase={psk}\n'
    'wpa=2\n'
    'wpa_key_mgmt=WPA-PSK\n'
    'interface={interface}\n'
    'channel=1\n'
    'driver=nl80211\n'
    'ctrl_interface=/var/run/hostapd\n'
)

CONF_NO_PSK_TEMPLATE = (
    'ssid={ssid}\n'
    'interface={interface}\n'
    'channel=1\n'
    'driver=nl80211\n'
    'ctrl_interface=/var/run/hostapd\n'
)

STOP_TIMEOUT = 2


logger = logging.getLogger(__name__)


class HostAPDException(APException):
    pass


class HostAPD:
    def __init__(
        self,
        ssid: str,
        psk: Optional[str],
        interface: str,
        hostapd_binary: Optional[str] = None,
        hostapd_cli_binary: Optional[str] = None,
        hostapd_log: Optional[str] = None
    ) -> None:

        self._ssid: str = ssid
        self._psk: Optional[str] = psk
        self._interface: str = interface
        self._binary: Optional[str] = hostapd_binary
        self._cli_binary: Optional[str] = hostapd_cli_binary
        self._log: Optional[str] = hostapd_log

        self._conf_file: Optional[TextIO] = None
        self._log_file: Optional[TextIO] = None
        self._process: Optional[subprocess.Popen] = None

    def is_alive(self) -> bool:
        return (self._process is not None) and (self._process.poll() is None)

    def is_running(self) -> bool:
        return self._process is not None

    def start(self) -> None:
        logger.debug(
            'starting hostapd with SSID "%s" and PSK %s',
            self._ssid,
            f'"{self._psk}"' if self._psk else 'empty'
        )

        binary = self._binary or self._find_binary(BINARY)
        if not binary:
            raise HostAPDException('Could not find %s binary', BINARY)

        conf_template = CONF_TEMPLATE if self._psk else CONF_NO_PSK_TEMPLATE
        conf = conf_template.format(ssid=self._ssid, psk=self._psk, interface=self._interface)

        self._log_file = open(self._log, 'wt')
        self._conf_file = tempfile.NamedTemporaryFile(mode='wt')
        self._conf_file.write(conf)
        self._conf_file.flush()

        self._process = subprocess.Popen(
            [binary, self._conf_file.name],
            stdout=self._log_file,
            stderr=subprocess.STDOUT
        )

    async def stop(self) -> None:
        logger.debug('stopping hostapd')

        if self._process:
            self._disassociate_clients()
            await asyncio.sleep(1)  # Allow 1 second for hostapd to honor the command

            self._process.terminate()

            begin_time = time.time()
            while self._process.poll() is None:
                await asyncio.sleep(0.1)
                if time.time() - begin_time > STOP_TIMEOUT:
                    break

            # If process could not be stopped in time, kill it
            if self._process.poll() is None:
                logger.error('failed to stop hostapd within %d seconds, killing it', STOP_TIMEOUT)
                self._process.kill()
                await asyncio.sleep(1)
                self._process.poll()  # We want no zombies

            self._process = None

        if self._conf_file:
            self._conf_file.close()
            self._conf_file = None

        if self._log_file:
            self._log_file.close()
            self._log_file = None

    def _disassociate_clients(self) -> None:
        cli_binary = self._cli_binary or self._find_binary(CLI_BINARY)
        if not cli_binary:
            raise HostAPDException('Could not find %s binary', CLI_BINARY)

        try:
            output = subprocess.check_output([cli_binary, 'list'], stderr=subprocess.DEVNULL).decode().strip()

        except subprocess.CalledProcessError:
            logger.error('command hostapd_cli list failed')
            return

        lines = output.split('\n')
        mac_addresses = [line for line in lines if re.match(r'^[a-f0-9:]{17}$', line)]

        for mac_address in mac_addresses:
            logger.debug('disassociating client with MAC %s', mac_address.upper())
            try:
                subprocess.check_call(
                    [cli_binary, 'disassociate', mac_address],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

            except subprocess.CalledProcessError:
                logger.error('command hostapd_cli disassociate failed')

    def _find_binary(self, binary: str) -> Optional[str]:
        try:
            return subprocess.check_output(['which', binary], stderr=subprocess.DEVNULL).decode().strip()

        except subprocess.CalledProcessError:
            return None

    @staticmethod
    def is_already_running() -> bool:
        return BINARY in (p.name() for p in psutil.process_iter())
