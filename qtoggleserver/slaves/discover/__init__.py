from .apclients import DiscoveredDevice, DiscoverException
from .apclients import cleanup as apclients_cleanup
from .apclients import configure, discover, finish, get_discovered_devices
from .apclients import get_interface as get_apclients_interface
from .apclients import init as apclients_init


def is_enabled() -> bool:
    # Discover mechanism is enabled if AP clients method is enabled;
    # AP clients method is enabled if it has available interface.
    return get_apclients_interface() is not None


async def init() -> None:
    await apclients_init()


async def cleanup() -> None:
    await apclients_cleanup()
