
import logging

import qui

from qtoggleserver import persist
from qtoggleserver import version
from qtoggleserver.conf import settings

from .base import APIHandler, BaseHandler


logger = logging.getLogger(__name__)


async def init() -> None:
    from qtoggleserver.slaves.discover import is_enabled as is_discover_enabled

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
                discover_enabled=is_discover_enabled(),
                history_enabled=persist.is_history_supported()
            )
        )


async def cleanup() -> None:
    pass
