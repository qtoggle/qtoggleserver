
from qtoggleserver import version
from qtoggleserver.conf import settings

from . import constants


def make_context() -> dict:
    return {
        'slaves_enabled': settings.slaves.enabled,

        'name': constants.APP_NAME,
        'pretty_name': constants.APP_PRETTY_NAME,
        'description': constants.APP_DESCRIPTION,
        'version': version.VERSION,
        'debug': settings.frontend.debug,
        'static_url': ['static', 'static/app'][settings.frontend.debug],
        'navigation_base_prefix': '/' + constants.FRONTEND_URL_PREFIX,
        'theme': constants.FRONTEND_DEFAULT_THEME,
        'theme_color': constants.BROWSER_THEME_COLOR,
        'background_color': constants.BROWSER_BACKGROUND_COLOR
    }
