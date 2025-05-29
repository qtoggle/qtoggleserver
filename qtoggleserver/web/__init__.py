import logging

import qui

from qtoggleserver import system, version
from qtoggleserver.conf import settings

from .base import APIHandler, BaseHandler


__all__ = ["APIHandler", "BaseHandler"]


logger = logging.getLogger(__name__)


async def init() -> None:
    from qtoggleserver.core import history
    from qtoggleserver.slaves.discover import is_enabled as is_discover_enabled

    if settings.frontend.enabled:
        logger.debug("initializing QUI")

        qui.configure(
            name="qtoggleserver",
            display_name=settings.frontend.display_name,
            display_short_name=settings.frontend.display_short_name,
            description=settings.frontend.description,
            version=version.VERSION,
            debug=settings.frontend.debug,
            static_url=settings.frontend.static_url,
            extra_context=dict(
                slaves_enabled=settings.slaves.enabled,
                discover_enabled=is_discover_enabled(),
                history_enabled=history.is_enabled(),
                setup_mode=system.is_setup_mode(),
            ),
        )


async def cleanup() -> None:
    pass
