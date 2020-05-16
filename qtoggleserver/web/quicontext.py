
import secrets
import hashlib

from . import constants


_buildHash = None


def get_build_hash(debug: bool, version: str) -> str:
    global _buildHash

    if _buildHash is None:
        if debug:
            _buildHash = secrets.token_hex()[:16]

        else:
            _buildHash = hashlib.sha256(version.encode()).hexdigest()[:16]

    return _buildHash


def make_context(debug: bool, version: str, **kwargs) -> dict:
    return dict({
        'name': constants.FRONTEND_APP_NAME,
        'display_name': constants.FRONTEND_APP_DISPLAY_NAME,
        'theme_color': constants.FRONTEND_APP_THEME_COLOR,
        'background_color': constants.FRONTEND_APP_BACKGROUND_COLOR,
        'description': constants.FRONTEND_APP_DESCRIPTION,
        'enable_pwa': True,
        'version': version,
        'debug': debug,
        'static_url': ['static', 'static/app'][debug],
        'navigation_base_prefix': '/' + constants.FRONTEND_URL_PREFIX,
        'themes': ['dark', 'light'],
        'build_hash': get_build_hash(debug, version)
    }, **kwargs)
