
from qtoggleserver import version
from qtoggleserver.conf import settings

from . import constants


def make_context() -> dict:
    return {
        'slaves_enabled': settings.slaves.enabled,

        'name': constants.FRONTEND_APP_NAME,
        'display_name': constants.FRONTEND_APP_DISPLAY_NAME,
        'version': version.VERSION,
        'debug': settings.frontend.debug,
        'static_url': ['static', 'static/app'][settings.frontend.debug],
        'navigation_base_prefix': '/' + constants.FRONTEND_URL_PREFIX,
        'themes': ['dark', 'light']
    }
