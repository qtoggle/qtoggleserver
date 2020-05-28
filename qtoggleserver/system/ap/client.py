
import datetime
import hashlib
import logging

from typing import Any, Optional

from tornado import httpclient

from qtoggleserver.conf import settings
from qtoggleserver.core.api import auth as core_api_auth
from qtoggleserver.utils import json as json_utils
from qtoggleserver.utils import logging as logging_utils


logger = logging.getLogger(__name__)


class APClient(logging_utils.LoggableMixin):
    def __init__(
        self,
        mac_address: str,
        ip_address: str,
        hostname: str,
        moment: datetime
    ) -> None:

        self.mac_address: str = mac_address
        self.ip_address: str = ip_address
        self.hostname: str = hostname
        self.moment: datetime = moment

        super().__init__(self.mac_address, logger)

    def __str__(self) -> str:
        return f'APClient {self.mac_address} at {self.ip_address}'

    async def request(
        self, method: str,
        path: str,
        body: Any = None,
        admin_password: Optional[str] = None,
        no_log: bool = False
    ) -> Any:

        http_client = httpclient.AsyncHTTPClient()
        if admin_password:
            password_hash = hashlib.sha256(admin_password.encode()).hexdigest()

        else:
            password_hash = core_api_auth.EMPTY_PASSWORD_HASH

        headers = {
            'Content-Type': json_utils.JSON_CONTENT_TYPE,
            'Authorization': core_api_auth.make_auth_header(
                core_api_auth.ORIGIN_CONSUMER,
                username='admin',
                password_hash=password_hash
            )
        }

        # TODO: this only tries standard port 80; ideally it should try connecting on a list of known ports

        timeout = settings.slaves.discover.request_timeout
        url = f'http://{self.ip_address}:80{path}'

        body_str = None
        if body is not None:
            body_str = json_utils.dumps(body)

        request = httpclient.HTTPRequest(
            url=url,
            method=method,
            headers=headers,
            body=body_str,
            connect_timeout=timeout,
            request_timeout=timeout
        )

        if not no_log:
            self.debug('requesting %s %s', method, path)

        try:
            response = await http_client.fetch(request, raise_error=True)

        except Exception as e:
            if not no_log:
                self.error('request %s %s failed: %s', method, path, e, exc_info=True)
            raise

        if response.body:
            return json_utils.loads(response.body)
