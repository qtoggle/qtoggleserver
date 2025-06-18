import asyncio
import logging
import subprocess
import tempfile
import time

from typing import TextIO, cast

import psutil

from .exceptions import APException


BINARY = "dnsmasq"

DNSMASQ_CONF_TEMPLATE = (
    "interface={interface}\ndhcp-range={start_ip},{stop_ip},24h\ndhcp-leasefile={leases_file}\nno-ping\n"
)

STOP_TIMEOUT = 2


logger = logging.getLogger(__name__)


class DNSMasqException(APException):
    pass


class DNSMasq:
    def __init__(
        self,
        interface: str,
        own_ip: str,
        mask_len: int,
        start_ip: str,
        stop_ip: str,
        dnsmasq_binary: str | None = None,
        dnsmasq_log: str | None = None,
    ) -> None:
        self._interface: str = interface
        self._own_ip: str = own_ip
        self._mask_len: int = mask_len
        self._start_ip: str = start_ip
        self._stop_ip: str = stop_ip
        self._binary: str | None = dnsmasq_binary
        self._log: str | None = dnsmasq_log

        self._conf_file: TextIO | None = None
        self._log_file: TextIO | None = None
        self._leases_file: TextIO | None = None
        self._process: subprocess.Popen | None = None

        self._leases: list[dict[str, str | int]] = []

    def is_alive(self) -> bool:
        return (self._process is not None) and (self._process.poll() is None)

    def is_running(self) -> bool:
        return self._process is not None

    def start(self) -> None:
        logger.debug(
            "starting dnsmasq with IP range %s - %s and own IP %s/%d",
            self._start_ip,
            self._stop_ip,
            self._own_ip,
            self._mask_len,
        )

        binary = self._binary or self._find_binary()
        if not binary:
            raise DNSMasqException("Could not find %s binary", BINARY)

        self.ensure_own_ip()

        self._leases_file = cast(TextIO, tempfile.NamedTemporaryFile(mode="w+t"))

        conf = DNSMASQ_CONF_TEMPLATE.format(
            start_ip=self._start_ip,
            stop_ip=self._stop_ip,
            interface=self._interface,
            leases_file=self._leases_file.name,
        )

        if self._log:
            self._log_file = cast(TextIO, open(self._log, "w"))
        self._conf_file = cast(TextIO, tempfile.NamedTemporaryFile(mode="wt"))
        self._conf_file.write(conf)
        self._conf_file.flush()

        self._process = subprocess.Popen(
            [binary, "-d", "-C", self._conf_file.name], stdout=self._log_file, stderr=subprocess.STDOUT
        )

    async def stop(self) -> None:
        logger.debug("stopping dnsmasq")

        if self._process:
            self._process.terminate()

            begin_time = time.time()
            while self._process.poll() is None:
                await asyncio.sleep(0.1)
                if time.time() - begin_time > STOP_TIMEOUT:
                    break

            # If process could not be stopped in time, kill it
            if self._process.poll() is None:
                logger.error("failed to stop hostapd within %d seconds, killing it", STOP_TIMEOUT)
                self._process.kill()
                await asyncio.sleep(1)
                self._process.poll()  # we want no zombies

            self._process = None

        if self._conf_file:
            self._conf_file.close()
            self._conf_file = None

        if self._log_file:
            self._log_file.close()
            self._log_file = None

        if self._leases_file:
            # Read leases file just before removing it
            self._leases = self._read_leases_file()

            self._leases_file.close()
            self._leases_file = None

    def ensure_own_ip(self) -> None:
        try:
            subprocess.check_call(
                ["ip", "addr", "flush", "dev", self._interface], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except subprocess.CalledProcessError:
            raise DNSMasqException("Could not clear current own IP address")

        try:
            subprocess.check_call(
                ["ip", "addr", "add", f"{self._own_ip}/{self._mask_len}", "dev", self._interface],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError:
            raise DNSMasqException("Could not set own IP address")

    def _find_binary(self) -> str | None:
        try:
            return subprocess.check_output(["which", BINARY], stderr=subprocess.DEVNULL).decode().strip()
        except subprocess.CalledProcessError:
            return None

    def _read_leases_file(self) -> list[dict[str, str | int]]:
        if not self._leases_file:
            return []

        self._leases_file.seek(0)
        lines = self._leases_file.readlines()

        leases: list[dict[str, str | int]] = []
        for line in lines:
            line = line.strip()
            if not line:
                continue

            parts = line.split()
            if len(parts) < 4:
                continue

            timestamp, mac_address, ip_address, hostname = parts[:4]
            leases.append(
                {
                    "timestamp": int(timestamp),
                    "mac_address": mac_address,
                    "ip_address": ip_address,
                    "hostname": hostname,
                }
            )

        return leases

    def get_leases(self) -> list[dict[str, str | int]]:
        if self._leases_file:
            self._leases = self._read_leases_file()

        return self._leases

    @staticmethod
    def is_already_running() -> bool:
        return BINARY in (p.name() for p in psutil.process_iter())
