from typing import Optional
from unittest import mock

from qtoggleserver.core.api import APIRequest
from qtoggleserver.web.handlers import APIHandler


class MockAPIRequest(APIRequest):
    def __init__(
        self,
        method: str,
        path: str,
        query: Optional[dict[str, str]] = None,
        headers: Optional[dict[str, str]] = None,
        body: bytes = b'',
        session_id: Optional[str] = None,
        username: Optional[str] = None,
        access_level: Optional[int] = None,
        handler_class: Optional[type[APIHandler]] = None,
    ) -> None:
        query = query or {}
        headers = headers or {}
        if session_id is not None:
            headers['Session-Id'] = session_id

        handler_class = handler_class or APIHandler
        handler = handler_class(
            application=mock.MagicMock(),
            request=mock.MagicMock(
                    headers=headers,
                    method=method,
                    path=path,
                    query=query,
                    body=body,
            )
        )
        if username is not None:
            handler.username = username
        if access_level is not None:
            handler.access_level = access_level

        super().__init__(handler)
