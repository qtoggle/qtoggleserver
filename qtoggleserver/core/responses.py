
import errno
import socket

from typing import Any, Optional

from tornado.httpclient import HTTPResponse

from qtoggleserver.core.typing import GenericJSONDict
from qtoggleserver.utils import json as json_utils


class Error(Exception):
    MESSAGE = ''

    def __init__(self, **params) -> None:
        self._params: dict = params

        super().__init__()

    def __str__(self) -> str:
        return self.MESSAGE.format(**self._params)

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}("{self}")'


class HostUnreachable(Error):
    MESSAGE = 'host unreachable'


class NetworkUnreachable(Error):
    MESSAGE = 'network unreachable'


class UnresolvableHostname(Error):
    MESSAGE = 'hostname cannot be resolved'


class ConnectionRefused(Error):
    MESSAGE = 'connection refused'


class Timeout(Error):
    MESSAGE = 'timeout'


class MovedPermanently(Error):
    # HTTP 301
    MESSAGE = 'moved permanently to "{location}"'

    def __init__(self, location: str) -> None:
        self.location: str = location

        super().__init__(location=location)


class Redirect(Error):
    # HTTP 302, 303
    MESSAGE = 'redirected to "{location}"'

    def __init__(self, location: str) -> None:
        self.location: str = location

        super().__init__(location=location)


class HTTPError(Error):
    # 4xx - 5xx
    MESSAGE = '{status} {code}'

    def __init__(self, status: int, code: str, **params) -> None:
        self.status: int = status
        self.code: str = code
        self.params: GenericJSONDict = params

        super().__init__(status=status, code=code)


class InvalidJson(Error):
    # JSON load() failure
    MESSAGE = 'invalid json'


class AuthError(Error):
    MESSAGE = 'authentication error: {msg}'

    def __init__(self, msg: str) -> None:
        super().__init__(msg=msg)


class OtherError(Error):
    # Any other error
    MESSAGE = 'other error: {msg}'

    def __init__(self, msg: str) -> None:
        super().__init__(msg=msg)


def _response_error_errno(eno: Optional[int]) -> Error:
    if eno == errno.ECONNREFUSED:
        return ConnectionRefused()

    elif eno == errno.EHOSTUNREACH:
        return HostUnreachable()

    elif eno == errno.ENETUNREACH:
        return NetworkUnreachable()

    elif eno in (socket.EAI_NONAME, socket.EAI_NODATA):
        return UnresolvableHostname()

    elif eno:
        return OtherError(errno.errorcode.get(eno))

    return OtherError('Unknown error')


def parse(response: HTTPResponse, decode_json: bool = True, resolve_refs: bool = True) -> Any:
    if 100 <= response.code < 599:
        if response.code == 204:
            return  # Happy case - no content

        if decode_json and response.body:
            try:
                body = json_utils.loads(response.body, resolve_refs=resolve_refs)

            except Exception as e:
                raise InvalidJson() from e

        else:
            body = response.body

        if response.code == 200:
            return body  # Happy case with content

        if response.code == 301:
            raise MovedPermanently(response.headers.get('Location', ''))

        if response.code in [302, 303]:
            raise Redirect(response.headers.get('Location', ''))

        if decode_json:
            raise HTTPError(response.code, body.pop('error', ''), **body)

        raise HTTPError(response.code, response.reason)

    elif response.error or response.code == 599:
        if str(response.error).lower().count('timeout'):
            raise Timeout()

        eno = getattr(response.error, 'errno', None)
        if eno:
            raise _response_error_errno(eno)

        raise OtherError(str(response.error))

    raise OtherError(f'Unknown HTTP error ({response.code}: {str(response.error)})')
