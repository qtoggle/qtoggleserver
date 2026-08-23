import types

import pytest

from qtoggleserver.core import responses as core_responses
from qtoggleserver.slaves.devices import Slave


@pytest.fixture
async def slave() -> Slave:
    return Slave(
        name="slave1",
        scheme="http",
        host="192.168.1.2",
        port=80,
        path="",
        admin_password="",
    )


@pytest.fixture
def mock_http_client(mocker):
    http_client = mocker.MagicMock()
    http_client.fetch = mocker.AsyncMock(return_value=types.SimpleNamespace(error=None, code=200))
    mocker.patch("qtoggleserver.slaves.devices.AsyncHTTPClient", return_value=http_client)

    return http_client


class TestInterceptError:
    """Test Slave.intercept_error() attribute name adaptation."""

    async def test_expression_field(self, slave) -> None:
        """Test that an invalid expression field is prefixed with device_."""
        error = core_responses.HTTPError(400, "invalid-field", field="expression")
        intercepted = slave.intercept_error(error)
        assert isinstance(intercepted, core_responses.HTTPError)
        assert intercepted.params["field"] == "device_expression"

    async def test_history_field(self, slave) -> None:
        """Test that an invalid history_* field is prefixed with device_."""
        error = core_responses.HTTPError(400, "invalid-field", field="history_interval")
        intercepted = slave.intercept_error(error)
        assert intercepted.params["field"] == "device_history_interval"

    async def test_other_field_unchanged(self, slave) -> None:
        """Test that other invalid fields are passed through untouched."""
        error = core_responses.HTTPError(400, "invalid-field", field="name")
        assert slave.intercept_error(error) is error

    async def test_other_code_unchanged(self, slave) -> None:
        """Test that errors with a different code are passed through untouched."""
        error = core_responses.HTTPError(400, "no-such-attribute", field="expression")
        assert slave.intercept_error(error) is error

    async def test_non_http_error_unchanged(self, slave) -> None:
        """Test that non-HTTP errors are passed through untouched."""
        error = core_responses.Timeout()
        assert slave.intercept_error(error) is error


class TestAPICallError:
    """Test error propagation through Slave._api_call()."""

    async def test_intercepted_error_propagated(self, slave, mock_http_client, mocker) -> None:
        """Test that the error adapted by intercept_error() is the one being raised."""
        mocker.patch.object(
            core_responses,
            "parse",
            side_effect=core_responses.HTTPError(400, "invalid-field", field="expression"),
        )

        with pytest.raises(core_responses.HTTPError) as exc_info:
            await slave._api_call("PATCH", "/device", {"expression": "BAD("})

        assert exc_info.value.params["field"] == "device_expression"

    async def test_untouched_error_propagated(self, slave, mock_http_client, mocker) -> None:
        """Test that an error which intercept_error() leaves alone is propagated as-is."""
        error = core_responses.HTTPError(400, "invalid-field", field="name")
        mocker.patch.object(core_responses, "parse", side_effect=error)

        with pytest.raises(core_responses.HTTPError) as exc_info:
            await slave._api_call("PATCH", "/device", {"name": ""})

        assert exc_info.value is error
