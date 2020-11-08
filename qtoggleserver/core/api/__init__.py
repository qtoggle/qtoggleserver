
from __future__ import annotations

import functools
import logging

from typing import Any, Callable, Dict, Optional

from qtoggleserver.core import responses as core_responses
from qtoggleserver.core.typing import GenericJSONDict


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
    def __init__(self, status: int, code: str, **params) -> None:
        self.status: int = status
        self.code: str = code
        self.params: dict = params

        super().__init__(code)

    @staticmethod
    def from_http_error(http_error: core_responses.HTTPError) -> APIError:
        return APIError(http_error.status, http_error.code, **http_error.params)

    def to_json(self) -> GenericJSONDict:
        return dict(error=self.code, **self.params)


class APIRequest:
    def __init__(self, handler: APIHandler) -> None:
        self.handler: APIHandler = handler

    @property
    def access_level(self) -> int:
        return self.handler.access_level

    @property
    def username(self) -> str:
        return self.handler.username

    @property
    def session_id(self) -> Optional[str]:
        return self.handler.request.headers.get('Session-Id')

    @property
    def method(self) -> str:
        return self.handler.request.method

    @property
    def path(self) -> str:
        return self.handler.request.path

    @property
    def query_arguments(self) -> Dict[str, str]:
        return {k: self.handler.decode_argument(v[0]) for k, v in self.handler.request.query_arguments.items()}

    @property
    def headers(self) -> Dict[str, str]:
        return self.handler.request.headers

    @property
    def body(self) -> bytes:
        return self.handler.request.body


def api_call(access_level: int = ACCESS_LEVEL_NONE) -> Callable:
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(request_handler: APIHandler, *args, **kwargs) -> Any:
            logger.debug('executing API call "%s"', func.__name__)

            if request_handler.access_level < access_level:
                if request_handler.access_level == ACCESS_LEVEL_NONE:  # Indicates missing or invalid auth data
                    raise APIError(401, 'authentication-required')

                else:
                    raise APIError(403, 'forbidden', required_level=ACCESS_LEVEL_MAPPING.get(access_level))

            request = APIRequest(request_handler)

            return func(request, *args, **kwargs)

        return wrapper

    return decorator


# Import this here to prevent errors due to circular imports
from qtoggleserver.web.handlers import APIHandler  # noqa: E402
