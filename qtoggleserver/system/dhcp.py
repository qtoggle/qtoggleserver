
from __future__ import annotations

import asyncio
import ctypes
import logging
import psutil
import random
import re
import socket
import struct
import time

from typing import List, Optional


DEFAULT_TIMEOUT = 10
MAX_TIMEOUT = 60

ETH_P_ALL = 3
IFF_PROMISC = 0x100
SIOCGIFFLAGS = 0x8913
SIOCSIFFLAGS = 0x8914

DHCP_MESSAGETYPE = 0x35
DHCP_EOF = 0xFF
DHCP_MSGDISCOVER = 0x01
DHCP_HOSTNAME = 0x0c
DHCP_REQUEST = 0x1
DHCP_REPLY = 0x2
DHCP_MAGIC = 0x63825363
DHCP_SRC_PORT = 68
DHCP_DST_PORT = 67

IPV4_PROTO_UDP = 17

ETHERTYPE_IP = 0x0800
ARPHRD_ETHER = 1

logger = logging.getLogger(__name__)

_dhcp_replies: List[DHCPReply] = []


class DHCPException(Exception):
    pass


class DHCPTimeout(DHCPException):
    pass


class DHCPReply:
    def __init__(
        self,
        ip_address: str,
        xid: int,
        timestamp: float
    ) -> None:

        self.ip_address: str = ip_address
        self.xid: int = xid
        self.timestamp: float = timestamp

    def __str__(self) -> str:
        return f'DHCP offer for {self.ip_address}'


class _ifreq(ctypes.Structure):
    _fields_ = [
        ("ifr_ifrn", ctypes.c_char * 16),
        ("ifr_flags", ctypes.c_short)
    ]


def _build_dhcp_options(hostname: Optional[str]) -> bytes:
    dhcp_opts = b''
    dhcp_opts += struct.pack('BBB', DHCP_MESSAGETYPE, 1, DHCP_MSGDISCOVER)  # Message type
    if hostname:
        dhcp_opts += struct.pack('BB', DHCP_HOSTNAME, len(hostname))
        dhcp_opts += hostname.encode()
    dhcp_opts += struct.pack('B', DHCP_EOF)  # EOF

    return dhcp_opts


def _build_dhcp_header(mac_address: str, xid: int, own_ip_address: str) -> bytes:
    own_ip_address = [int(p) for p in own_ip_address.split('.')]

    dhcp_header = struct.pack('B', DHCP_REQUEST)  # Opcode
    dhcp_header += struct.pack('B', ARPHRD_ETHER)  # Hardware address type
    dhcp_header += struct.pack('B', 6)  # Hardware address len
    dhcp_header += struct.pack('B', 0)  # Opcount
    dhcp_header += struct.pack('!L', xid)  # Transaction ID
    dhcp_header += struct.pack('!H', 0)  # Seconds
    dhcp_header += struct.pack('!H', 0)  # Flags
    dhcp_header += struct.pack('BBBB', 0, 0, 0, 0)  # Client IP
    dhcp_header += struct.pack('BBBB', 0, 0, 0, 0)  # Your IP
    dhcp_header += struct.pack('BBBB', 0, 0, 0, 0)  # Server IP
    dhcp_header += struct.pack('BBBB', *own_ip_address)  # Gateway IP
    dhcp_header += bytes.fromhex(re.sub('[^a-fA-F0-9]', '', mac_address))  # Client MAC
    dhcp_header += b'\x00' * 10  # Remaining hardware address space
    dhcp_header += b'\x00' * 64  # Server hostname
    dhcp_header += b'\x00' * 128  # Boot file name
    dhcp_header += struct.pack('!L', DHCP_MAGIC)

    return dhcp_header


def _build_udp_header(dhcp_packet: bytes) -> bytes:
    udp_header = struct.pack('!H', DHCP_SRC_PORT)  # Source port
    udp_header += struct.pack('!H', DHCP_DST_PORT)  # Dest port
    udp_header += struct.pack('!H', 8 + len(dhcp_packet))  # UDP header + DHCP packet
    udp_header += struct.pack('!H', 0)  # Checksum

    return udp_header


def _build_ipv4_header(udp_packet: bytes) -> bytes:
    ipv4_header = b'\x45'   # Version + Length
    ipv4_header += b'\x00'  # ToS
    ipv4_header += struct.pack('!H', 20 + len(udp_packet))  # IP header + UDP packet
    ipv4_header += struct.pack('!H', 0)  # ID
    ipv4_header += struct.pack('!H', 0)  # Fragment offset
    ipv4_header += struct.pack('B', 64)  # TTL
    ipv4_header += struct.pack('B', IPV4_PROTO_UDP)  # Protocol
    ipv4_header += struct.pack('!H', 0)  # Checksum
    ipv4_header += struct.pack('BBBB', 0, 0, 0, 0)  # Source address
    ipv4_header += struct.pack('BBBB', 255, 255, 255, 255)  # Dest address

    ipv4_checksum = 0
    for i in range(6):  # Header length is 10x16 bytes
        word = struct.unpack('!H', ipv4_header[i * 2: i * 2 + 2])[0]
        ipv4_checksum += word

    ipv4_checksum = (ipv4_checksum >> 16) + ipv4_checksum
    ipv4_checksum = (~ipv4_checksum) & 0xFFFF

    ipv4_header = ipv4_header[0:10] + struct.pack('!H', ipv4_checksum) + ipv4_header[12:20]

    return ipv4_header


def _build_ethernet_header(own_mac_address: str) -> bytes:
    ethernet_header = b'\xFF\xFF\xFF\xFF\xFF\xFF'  # Dest MAC
    ethernet_header += bytes.fromhex(re.sub('[^a-fA-F0-9]', '', own_mac_address))
    ethernet_header += struct.pack('!H', ETHERTYPE_IP)

    return ethernet_header


def _check_received_frame(frame: bytes, expected_xid: int) -> Optional[DHCPReply]:
    if len(frame) < 282:
        return

    ethernet_header = frame[:14]
    ipv4_header = frame[14:34]
    udp_header = frame[34:42]
    dhcp_header = frame[42:282]
    # dhcp_opts = frame[282:]

    ethertype = struct.unpack('!H', ethernet_header[12:14])[0]
    if ethertype != ETHERTYPE_IP:
        return

    if ipv4_header[9] != IPV4_PROTO_UDP:
        return

    src_port = struct.unpack('!H', udp_header[0:2])[0]
    if src_port != DHCP_DST_PORT:
        return

    dst_port = struct.unpack('!H', udp_header[2:4])[0]
    if (dst_port != DHCP_SRC_PORT) and (dst_port != DHCP_DST_PORT):
        return

    # At this point we can consider we're dealing with a DHCP reply

    xid = struct.unpack('!L', dhcp_header[4:8])[0]
    your_ip = dhcp_header[16:20]
    your_ip = '{:d}.{:d}.{:d}.{:d}'.format(*your_ip)
    dhcp_reply = DHCPReply(
        ip_address=your_ip,
        xid=xid,
        timestamp=time.time()
    )

    if expected_xid == xid:
        return dhcp_reply

    else:  # Not ours, queue it for other pending requests
        _dhcp_replies.append(dhcp_reply)


def _check_and_prune_pending_dhcp_replies(expected_xid: int) -> Optional[DHCPReply]:
    global _dhcp_replies

    # Prune expired replies
    now = time.time()
    _dhcp_replies = [r for r in _dhcp_replies if now - r.timestamp < MAX_TIMEOUT]

    # Look for our transaction id
    reply = next((r for r in _dhcp_replies if r.xid == expected_xid), None)
    if reply:
        _dhcp_replies.remove(reply)

    return reply


async def request(
    interface: str,
    mac_address: str,
    hostname: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT
) -> DHCPReply:

    logger.debug(
        'sending DHCP discovery for %s (%s) on %s',
        mac_address,
        hostname if hostname else '<no hostname>',
        interface
    )

    # Generate random transaction id
    xid = int(random.random() * 0xFFFFFFFF)

    # Find MAC & IP address of given interface
    try:
        if_addrs = psutil.net_if_addrs()[interface]

    except KeyError:
        raise DHCPException(f'Cannot find own address for interface {interface}')

    own_mac_address = None
    own_ip_address = None
    for addr in if_addrs:
        if addr.family == socket.AF_PACKET:
            own_mac_address = addr.address

        elif addr.family == socket.AF_INET:
            own_ip_address = addr.address

    if not own_ip_address or not own_mac_address:
        raise DHCPException(f'Cannot find own address for interface {interface}')

    dhcp_opts = _build_dhcp_options(hostname)
    dhcp_header = _build_dhcp_header(mac_address, xid, own_ip_address)
    dhcp_packet = dhcp_header + dhcp_opts

    udp_header = _build_udp_header(dhcp_packet)
    udp_packet = udp_header + dhcp_packet

    ipv4_header = _build_ipv4_header(udp_packet)
    ipv4_packet = ipv4_header + udp_packet

    ethernet_header = _build_ethernet_header(own_mac_address)
    ethernet_frame = ethernet_header + ipv4_packet

    # Open sockets
    sock = socket.socket(family=socket.PF_PACKET, type=socket.SOCK_RAW, proto=socket.htons(ETH_P_ALL))
    sock.bind((interface, 0))

    # Actually send packet
    sock.send(ethernet_frame)

    # Wait for data; filter out stuff that we don't need
    start_time = time.time()
    offer = None
    while True:
        try:
            data = sock.recv(1024, socket.MSG_DONTWAIT)

        except BlockingIOError:
            data = None

        if data:
            offer = _check_received_frame(data, xid)
            if offer:
                break

        offer = _check_and_prune_pending_dhcp_replies(xid)
        if offer:
            break

        if time.time() - start_time > timeout:
            break

        await asyncio.sleep(0)

    # Don't forget to close socket
    sock.close()

    if offer:
        logger.debug(
            'received DHCP offer for %s (%s) on %s: %s',
            mac_address,
            hostname if hostname else '<no hostname>',
            interface,
            offer.ip_address
        )

        return offer

    else:
        logger.warning(
            'timeout waiting for DHCP offer for %s (%s) on %s',
            mac_address,
            hostname if hostname else '<no hostname>',
            interface
        )

        raise DHCPTimeout()
