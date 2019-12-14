
import jwt
import logging
import re
import time

from qtoggleserver import system
from qtoggleserver.conf import settings
from qtoggleserver.core.device import attrs as core_device_attrs


JWT_ISS = 'qToggle'
JWT_ALG = 'HS256'

ORIGIN_DEVICE = 'device'
ORIGIN_CONSUMER = 'consumer'

_AUTH_TOKEN_RE = re.compile(r'^Bearer\s+([a-z0-9_.-]+)$', re.IGNORECASE)

logger = logging.getLogger(__name__)


class AuthError(Exception):
    pass


def make_auth_header(origin, username, password_hash):
    claims = {
        'iss': JWT_ISS,
        'ori': origin
    }

    if username:
        claims['usr'] = username

    if system.date.has_date_support() and system.date.has_real_date_time():
        claims['iat'] = int(time.time())

    token = jwt.encode(claims, key=password_hash or '', algorithm=JWT_ALG)

    return 'Bearer {}'.format(token.decode())


def parse_auth_header(auth, origin, password_hash_func, require_usr=True):
    m = _AUTH_TOKEN_RE.match(auth)
    if not m:
        raise AuthError('invalid authorization header')

    # decode but don't validate token yet
    token = m.group(1)

    try:
        payload = jwt.decode(token, algorithms=[JWT_ALG], verify=False)

    except jwt.exceptions.InvalidTokenError as e:
        raise AuthError('invalid JWT: {}'.format(e)) from e

    # validate claims
    if payload.get('iss') != JWT_ISS:
        raise AuthError('missing or invalid iss claim in JWT')

    if payload.get('ori') != origin:
        raise AuthError('missing or invalid ori claim in JWT')

    iat = payload.get('iat')
    if (iat is not None) and system.date.has_date_support() and system.date.has_real_date_time():
        delta = time.time() - iat
        if abs(delta) > settings.core.max_client_time_skew:
            raise AuthError('JWT too old or too much in the future')

    usr = payload.get('usr')
    if require_usr:
        if not usr or not isinstance(usr, str):
            raise AuthError('missing or invalid usr claim in JWT')

    # validate username & signature
    password_hash = password_hash_func(usr)
    if not password_hash:
        raise AuthError('unknown usr in JWT: {}'.format(usr))

    # decode again to verify signature
    try:
        jwt.decode(token, key=password_hash, algorithms=[JWT_ALG], verify=True)

    except jwt.exceptions.InvalidSignatureError as e:
        raise AuthError('invalid JWT signature') from e

    except jwt.exceptions.InvalidTokenError as e:
        raise AuthError('invalid JWT: {}'.format(e)) from e

    return usr


def consumer_password_hash_func(usr):
    if usr == 'admin':
        return core_device_attrs.admin_password_hash

    elif usr == 'normal':
        return core_device_attrs.normal_password_hash

    elif usr == 'viewonly':
        return core_device_attrs.viewonly_password_hash

    else:
        return None
