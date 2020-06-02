
import logging

import qui

from qtoggleserver import version
from qtoggleserver.conf import settings
from qtoggleserver.slaves.discover import is_enabled as is_discover_enabled


logger = logging.getLogger(__name__)


async def init() -> None:
    if settings.frontend.enabled:
        logger.debug('initializing QUI')

        qui.configure(
            name='qtoggleserver',
            display_name='qToggleServer',
            description='qToggleServer',
            version=version.VERSION,
            debug=settings.frontend.debug,
            static_url=settings.frontend.static_url,
            extra_context=dict(
                slaves_enabled=settings.slaves.enabled,
                discover_enabled=is_discover_enabled()
            )
        )


async def cleanup() -> None:
    pass
