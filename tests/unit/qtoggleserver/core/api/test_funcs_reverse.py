import hashlib

import pytest

from qtoggleserver.core import api as core_api
from qtoggleserver.core import reverse as core_reverse
from qtoggleserver.core.api.funcs import reverse as reverse_api_funcs


PARAMS = {
    "enabled": False,
    "scheme": "http",
    "host": "consumer.example.com",
    "port": 80,
    "path": "/reverse",
    "device_id": "device1",
    "timeout": 60,
}
SECRET_HASH = hashlib.sha256(b"secret").hexdigest()


@pytest.fixture(autouse=True)
def reset_reverse():
    yield
    core_reverse.setup(enabled=False)


@pytest.fixture
def admin_request(mock_api_request_maker) -> core_api.APIRequest:
    return mock_api_request_maker("PUT", "/reverse", access_level=core_api.ACCESS_LEVEL_ADMIN)


class TestPutReversePassword:
    """Test that `PUT /reverse` keeps the hash of the given password, and that only one password field is given."""

    async def test_password_is_hashed(self, admin_request, mock_persist_driver) -> None:
        await reverse_api_funcs.put_reverse(admin_request, dict(PARAMS, password="secret"))

        result = await reverse_api_funcs.get_reverse(admin_request)
        assert result["password_hash"] == SECRET_HASH
        assert "password" not in result

    async def test_password_hash_is_kept(self, admin_request, mock_persist_driver) -> None:
        await reverse_api_funcs.put_reverse(admin_request, dict(PARAMS, password_hash=SECRET_HASH))

        result = await reverse_api_funcs.get_reverse(admin_request)
        assert result["password_hash"] == SECRET_HASH

    async def test_password_hash_survives_reload(self, admin_request, mock_persist_driver) -> None:
        await reverse_api_funcs.put_reverse(admin_request, dict(PARAMS, password="secret"))
        core_reverse.setup(enabled=False)

        await core_reverse.load()

        assert core_reverse.get().to_json()["password_hash"] == SECRET_HASH

    async def test_both_fields_rejected(self, admin_request, mock_persist_driver) -> None:
        with pytest.raises(core_api.APIError) as exc_info:
            await reverse_api_funcs.put_reverse(
                admin_request, dict(PARAMS, password="secret", password_hash=SECRET_HASH)
            )

        assert exc_info.value.status == 400
        assert exc_info.value.code == "invalid-field"
        assert exc_info.value.params == {"field": "password"}

    async def test_missing_password_rejected(self, admin_request, mock_persist_driver) -> None:
        with pytest.raises(core_api.APIError) as exc_info:
            await reverse_api_funcs.put_reverse(admin_request, dict(PARAMS))

        assert exc_info.value.code == "missing-field"
        assert exc_info.value.params == {"field": "password"}

    async def test_long_password_rejected(self, admin_request, mock_persist_driver) -> None:
        with pytest.raises(core_api.APIError) as exc_info:
            await reverse_api_funcs.put_reverse(admin_request, dict(PARAMS, password="x" * 33))

        assert exc_info.value.code == "invalid-field"
        assert exc_info.value.params == {"field": "password"}
