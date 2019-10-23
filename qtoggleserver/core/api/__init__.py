
import functools
import logging


API_VERSION = '1.0'

ACCESS_LEVEL_ADMIN = 30
ACCESS_LEVEL_NORMAL = 20
ACCESS_LEVEL_VIEWONLY = 10
ACCESS_LEVEL_NONE = 0

ACCESS_LEVEL_MAPPING = {
    ACCESS_LEVEL_ADMIN: 'admin',
    ACCESS_LEVEL_NORMAL: 'normal',
    ACCESS_LEVEL_VIEWONLY: 'viewonly',
    ACCESS_LEVEL_NONE: 'none',
    'admin': ACCESS_LEVEL_ADMIN,
    'normal': ACCESS_LEVEL_NORMAL,
    'viewonly': ACCESS_LEVEL_VIEWONLY,
    'none': ACCESS_LEVEL_NONE
}

logger = logging.getLogger(__name__)


class APIError(Exception):
    def __init__(self, status, message, **params):
        self.status = status
        self.message = message
        self.params = params

        super().__init__(message)

    @staticmethod
    def from_http_error(http_error):
        return APIError(http_error.code, http_error.msg)


class APIRequest:
    def __init__(self, handler):
        self.handler = handler

    @property
    def access_level(self):
        return self.handler.access_level

    @property
    def method(self):
        return self.handler.request.method

    @property
    def path(self):
        return self.handler.request.path

    @property
    def query_arguments(self):
        return {k: self.handler.decode_argument(v[0]) for k, v in self.handler.request.query_arguments.items()}

    @property
    def headers(self):
        return self.handler.request.headers

    @property
    def body(self):
        return self.handler.request.body


def api_call(access_level=ACCESS_LEVEL_NONE):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(request_handler, *args, **kwargs):
            logger.debug('executing API call "%s"', func.__name__)

            if request_handler.access_level < access_level:
                if request_handler.access_level == ACCESS_LEVEL_NONE:  # indicates missing or invalid auth data
                    raise APIError(401, 'authentication required')

                else:
                    raise APIError(403, 'forbidden', required_level=ACCESS_LEVEL_MAPPING.get(access_level))

            request = APIRequest(request_handler)

            return func(request, *args, **kwargs)

        return wrapper

    return decorator
