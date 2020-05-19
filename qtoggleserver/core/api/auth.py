
import hashlib
import jwt
import logging
import re
import time

from typing import Callable, Optional

from qtoggleserver import system
from qtoggleserver.conf import settings
from qtoggleserver.core.device import attrs as core_device_attrs


JWT_ISS = 'qToggle'
JWT_ALG = 'HS256'

ORIGIN_DEVICE = 'device'
ORIGIN_CONSUMER = 'consumer'

EMPTY_PASSWORD_HASH = hashlib.sha256(b'').hexdigest()

_AUTH_TOKEN_RE = re.compile(r'^Bearer\s+([a-z0-9_.-]+)$', re.IGNORECASE)

logger = logging.getLogger(__name__)


class AuthError(Exception):
    pass


def make_auth_header(origin: str, username: Optional[str], password_hash: str) -> str:
    claims = {
        'iss': JWT_ISS,
        'ori': origin
    }

    if username:
        claims['usr'] = username

    if system.date.has_real_date_time():
        claims['iat'] = int(time.time())

    token = jwt.encode(claims, key=password_hash or '', algorithm=JWT_ALG)

    return f'Bearer {token.decode()}'


def parse_auth_header(auth: str, origin: str, password_hash_func: Callable, require_usr: bool = True) -> str:
    m = _AUTH_TOKEN_RE.match(auth)
    if not m:
        raise AuthError('Invalid authorization header')

    # Decode but don't validate token yet
    token = m.group(1)

    try:
        payload = jwt.decode(token, algorithms=[JWT_ALG], verify=False)

    except jwt.exceptions.InvalidTokenError as e:
        raise AuthError(f'Invalid JWT: {e}') from e

    # Validate claims
    if payload.get('iss') != JWT_ISS:
        raise AuthError('Missing or invalid iss claim in JWT')

    if payload.get('ori') != origin:
        raise AuthError('Missing or invalid ori claim in JWT')

    iat = payload.get('iat')
    if (iat is not None) and system.date.has_real_date_time():
        delta = time.time() - iat
        if abs(delta) > settings.core.max_client_time_skew:
            raise AuthError('JWT too old or too much in the future')

    usr = payload.get('usr')
    if require_usr:
        if not usr or not isinstance(usr, str):
            raise AuthError('Missing or invalid usr claim in JWT')

    # Validate username & signature
    password_hash = password_hash_func(usr)
    if not password_hash:
        raise AuthError(f'Unknown usr in JWT: {usr}')

    # Decode again to verify signature
    try:
        jwt.decode(token, key=password_hash, algorithms=[JWT_ALG], verify=True)

    except jwt.exceptions.InvalidSignatureError as e:
        raise AuthError('Invalid JWT signature') from e

    except jwt.exceptions.InvalidTokenError as e:
        raise AuthError(f'Invalid JWT: {e}') from e

    return usr


def consumer_password_hash_func(usr: str) -> Optional[str]:
    if usr == 'admin':
        return core_device_attrs.admin_password_hash

    elif usr == 'normal':
        return core_device_attrs.normal_password_hash

    elif usr == 'viewonly':
        return core_device_attrs.viewonly_password_hash

    else:
        return None
