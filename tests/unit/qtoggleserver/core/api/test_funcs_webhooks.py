import hashlib

import jwt
import pytest

from qtoggleserver.core import api as core_api
from qtoggleserver.core import webhooks as core_webhooks
from qtoggleserver.core.api.funcs import webhooks as webhooks_api_funcs
from qtoggleserver.core.device import attrs as core_device_attrs


PARAMS = {
    "enabled": False,
    "scheme": "http",
    "host": "consumer.example.com",
    "port": 80,
    "path": "/webhooks",
    "timeout": 60,
    "retries": 3,
}
SECRET_HASH = hashlib.sha256(b"secret").hexdigest()


@pytest.fixture(autouse=True)
def reset_webhooks():
    yield
    core_webhooks.setup(enabled=False)


@pytest.fixture
def admin_request(mock_api_request_maker) -> core_api.APIRequest:
    return mock_api_request_maker("PUT", "/webhooks", access_level=core_api.ACCESS_LEVEL_ADMIN)


class TestPutWebhooksPassword:
    """Test that `PUT /webhooks` keeps the hash of the given password, and that only one password field is given."""

    async def test_password_is_hashed(self, admin_request, mock_persist_driver) -> None:
        await webhooks_api_funcs.put_webhooks(admin_request, dict(PARAMS, password="secret"))

        result = await webhooks_api_funcs.get_webhooks(admin_request)
        assert result["password_hash"] == SECRET_HASH
        assert "password" not in result

    async def test_password_hash_is_kept(self, admin_request, mock_persist_driver) -> None:
        await webhooks_api_funcs.put_webhooks(admin_request, dict(PARAMS, password_hash=SECRET_HASH))

        result = await webhooks_api_funcs.get_webhooks(admin_request)
        assert result["password_hash"] == SECRET_HASH

    async def test_password_hash_survives_reload(self, admin_request, mock_persist_driver) -> None:
        await webhooks_api_funcs.put_webhooks(admin_request, dict(PARAMS, password="secret"))
        core_webhooks.setup(enabled=False)

        await core_webhooks.load()

        assert core_webhooks.get().to_json()["password_hash"] == SECRET_HASH

    async def test_both_fields_rejected(self, admin_request, mock_persist_driver) -> None:
        with pytest.raises(core_api.APIError) as exc_info:
            await webhooks_api_funcs.put_webhooks(
                admin_request, dict(PARAMS, password="secret", password_hash=SECRET_HASH)
            )

        assert exc_info.value.status == 400
        assert exc_info.value.code == "invalid-field"
        assert exc_info.value.params == {"field": "password"}

    async def test_missing_password_rejected(self, admin_request, mock_persist_driver) -> None:
        with pytest.raises(core_api.APIError) as exc_info:
            await webhooks_api_funcs.put_webhooks(admin_request, dict(PARAMS))

        assert exc_info.value.code == "missing-field"
        assert exc_info.value.params == {"field": "password"}

    async def test_long_password_rejected(self, admin_request, mock_persist_driver) -> None:
        with pytest.raises(core_api.APIError) as exc_info:
            await webhooks_api_funcs.put_webhooks(admin_request, dict(PARAMS, password="x" * 33))

        assert exc_info.value.code == "invalid-field"
        assert exc_info.value.params == {"field": "password"}


class TestWebhooksSigning:
    """Test that webhook requests are signed with the webhooks password, as the spec asks."""

    async def test_signs_with_webhooks_password(self, mocker) -> None:
        mocker.patch.object(core_device_attrs, "normal_password_hash", hashlib.sha256(b"normal").hexdigest())
        http_client = mocker.MagicMock()
        mocker.patch("qtoggleserver.core.webhooks.AsyncHTTPClient", return_value=http_client)
        core_webhooks.setup(**dict(PARAMS, enabled=True, password_hash=SECRET_HASH))

        core_webhooks.get().call({"type": "value-change"})

        request = http_client.fetch.call_args.args[0]
        token = request.headers["Authorization"].removeprefix("Bearer ")
        claims = jwt.decode(token, key=SECRET_HASH, algorithms=["HS256"])
        assert claims["ori"] == "device"
        assert "usr" not in claims
