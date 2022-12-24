import pytest

from qtoggleserver.core import api as core_api
from qtoggleserver.peripherals.api import funcs as peripherals_api_funcs


class TestGetPeripherals:
    async def test_happy_path(self, mock_api_request_maker, mock_peripheral1, mock_peripheral2):
        request = mock_api_request_maker('GET', '/api/peripherals', access_level=core_api.ACCESS_LEVEL_ADMIN)
        #with mock.patch('qtoggleserver.peripherals._registered_peripherals', new={}):
        result = await peripherals_api_funcs.get_peripherals(request)
        assert result
