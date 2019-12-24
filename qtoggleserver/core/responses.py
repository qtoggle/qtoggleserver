
import errno
import socket


from qtoggleserver.utils import json as json_utils


class Error(Exception):
    MESSAGE = ''

    def __init__(self, **params):
        self._params = params

        super().__init__()

    def __str__(self):
        return self.MESSAGE.format(**self._params)

    def __repr__(self):
        return '{}("{}")'.format(self.__class__.__name__, self)


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

    def __init__(self, location):
        self.location = location

        super().__init__(location=location)


class Redirect(Error):
    # HTTP 302, 303
    MESSAGE = 'redirected to "{location}"'

    def __init__(self, location):
        self.location = location

        super().__init__(location=location)


class HTTPError(Error):
    # 4xx - 5xx
    MESSAGE = '{code} {msg}'

    def __init__(self, code, msg):
        self.code = code
        self.msg = msg

        super().__init__(code=code, msg=msg)


class InvalidJson(Error):
    # JSON load() failure
    MESSAGE = 'invalid json'


class AuthError(Error):
    MESSAGE = 'authentication error: {msg}'

    def __init__(self, msg):
        super().__init__(msg=msg)


class OtherError(Error):
    # any other error
    MESSAGE = 'other error: {msg}'

    def __init__(self, msg):
        super().__init__(msg=msg)


def _response_error_errno(eno):
    if eno == errno.ECONNREFUSED:
        return ConnectionRefused()

    elif eno == errno.EHOSTUNREACH:
        return HostUnreachable()

    elif eno == errno.ENETUNREACH:
        return NetworkUnreachable()

    elif eno == socket.EAI_NONAME:
        return UnresolvableHostname()

    elif eno:
        return OtherError(errno.errorcode.get(eno))

    return OtherError('unknown error')


def parse(response, decode_json=True, resolve_refs=True):
    if 100 <= response.code < 599:
        if response.code == 204:
            return  # happy case - no content

        if decode_json and response.body:
            try:
                body = json_utils.loads(response.body, resolve_refs=resolve_refs)

            except Exception as e:
                raise InvalidJson() from e

        else:
            body = response.body

        if response.code == 200:
            return body  # happy case with content

        if response.code == 301:
            raise MovedPermanently(response.headers.get('Location', ''))

        if response.code in [302, 303]:
            raise Redirect(response.headers.get('Location', ''))

        if decode_json:
            raise HTTPError(response.code, body.get('error', ''))

        raise HTTPError(response.code, response.reason)

    elif response.error or response.code == 599:
        if str(response.error).lower().count('timeout'):
            raise Timeout()

        eno = getattr(response.error, 'errno', None)
        if eno:
            raise _response_error_errno(eno)

        raise OtherError(str(response.error))

    raise OtherError('unknown HTTP error ({}: {})'.format(response.code, str(response.error)))
