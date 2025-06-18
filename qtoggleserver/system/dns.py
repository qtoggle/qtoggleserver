import asyncio
import logging
import time


_CUSTOM_CLEANUP_INTERVAL = 5

logger = logging.getLogger(__name__)

_custom_dns_mapping: dict[str, str] = {}
_custom_dns_mapping_timeouts: dict[str, tuple[int, int]] = {}
_custom_dns_cleanup_task: asyncio.Task | None = None


def get_custom_dns_mapping_dict() -> dict[str, str]:
    return _custom_dns_mapping


def set_custom_dns_mapping(hostname: str, ip_address: str, timeout: int | None = None) -> None:
    logger.debug("setting custom DNS mapping %s -> %s with timeout %s", hostname, ip_address, timeout or "none")

    _custom_dns_mapping[hostname] = ip_address
    if timeout:
        _custom_dns_mapping_timeouts[hostname] = (timeout, int(time.time()))


async def _custom_cleanup_loop() -> None:
    try:
        now = time.time()
        while True:
            for hostname, (timeout, added_time) in list(_custom_dns_mapping_timeouts.items()):
                if now - added_time > timeout:
                    logger.debug("custom DNS mapping for %s expired", hostname)
                    _custom_dns_mapping_timeouts.pop(hostname)
                    _custom_dns_mapping.pop(hostname, None)

            await asyncio.sleep(_CUSTOM_CLEANUP_INTERVAL)
    except asyncio.CancelledError:
        logger.debug("custom DNS mapping cleanup task cancelled")


async def init() -> None:
    global _custom_dns_cleanup_task

    _custom_dns_cleanup_task = asyncio.create_task(_custom_cleanup_loop())


async def cleanup() -> None:
    global _custom_dns_cleanup_task

    if _custom_dns_cleanup_task:
        _custom_dns_cleanup_task.cancel()
        await _custom_dns_cleanup_task
        _custom_dns_cleanup_task = None
