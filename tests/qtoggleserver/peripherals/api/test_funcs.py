import pytest

from qtoggleserver.core import api as core_api
from qtoggleserver.peripherals.api import funcs as peripherals_api_funcs

from tests.qtoggleserver.mock.peripherals import MockPeripheral


MOCK_PERIPHERAL1_PAYLOAD = {
    'driver': 'tests.qtoggleserver.mock.peripherals.MockPeripheral',
    'dummy_param': 'dummy_value1',
    'name': 'peripheral1',
    'id': 'peripheral1',
    'static': False
}

MOCK_PERIPHERAL2_PAYLOAD = {
    'driver': 'tests.qtoggleserver.mock.peripherals.MockPeripheral',
    'dummy_param': 'dummy_value2',
    'name': 'peripheral2',
    'id': 'peripheral2',
    'static': False
}

MOCK_PERIPHERAL3_PAYLOAD = {
    'driver': 'tests.qtoggleserver.mock.peripherals.MockPeripheral',
    'dummy_param': 'dummy_value3',
    'name': 'peripheral3',
    'id': 'peripheral3',
    'static': False
}


class TestGetPeripherals:
    async def test_ok(self, mock_api_request_maker, mock_peripheral1, mock_peripheral2):
        request = mock_api_request_maker('GET', '/api/peripherals', access_level=core_api.ACCESS_LEVEL_ADMIN)
        result = await peripherals_api_funcs.get_peripherals(request)
        assert result == [MOCK_PERIPHERAL1_PAYLOAD, MOCK_PERIPHERAL2_PAYLOAD]

    async def test_normal_user_permissions(self, mock_api_request_maker, mock_peripheral1, mock_peripheral2):
        request = mock_api_request_maker('GET', '/api/peripherals', access_level=core_api.ACCESS_LEVEL_NORMAL)
        with pytest.raises(core_api.APIError, match='forbidden'):
            await peripherals_api_funcs.get_peripherals(request)

    async def test_viewonly_user_permissions(self, mock_api_request_maker, mock_peripheral1, mock_peripheral2):
        request = mock_api_request_maker('GET', '/api/peripherals', access_level=core_api.ACCESS_LEVEL_VIEWONLY)
        with pytest.raises(core_api.APIError, match='forbidden'):
            await peripherals_api_funcs.get_peripherals(request)

    async def test_anonymous_user_permissions(self, mock_api_request_maker, mock_peripheral1, mock_peripheral2):
        request = mock_api_request_maker('GET', '/api/peripherals', access_level=core_api.ACCESS_LEVEL_NONE)
        with pytest.raises(core_api.APIError, match='authentication-required'):
            await peripherals_api_funcs.get_peripherals(request)


class TestPostPeripherals:
    async def test_ok_with_name_and_id(self, mocker, mock_api_request_maker, mock_peripheral1):
        mock_peripheral2 = MockPeripheral(
            name=MOCK_PERIPHERAL2_PAYLOAD['name'],
            dummy_param=MOCK_PERIPHERAL2_PAYLOAD['dummy_param'],
        )

        payload = dict(MOCK_PERIPHERAL2_PAYLOAD)
        payload.pop('static')
        request = mock_api_request_maker('POST', '/api/peripherals', access_level=core_api.ACCESS_LEVEL_ADMIN)

        spy_add = mocker.patch('qtoggleserver.peripherals.add', return_value=mock_peripheral2)
        spy_init_ports = mocker.patch('qtoggleserver.peripherals.init_ports')
        result = await peripherals_api_funcs.post_peripherals(request, payload)

        spy_add.assert_called_once_with(payload)
        spy_init_ports.assert_called_once_with(mock_peripheral2)

        assert result == MOCK_PERIPHERAL2_PAYLOAD

    async def test_ok_with_name(self, mocker, mock_api_request_maker, mock_peripheral1):
        mock_peripheral2 = MockPeripheral(
            name=MOCK_PERIPHERAL2_PAYLOAD['name'],
            dummy_param=MOCK_PERIPHERAL2_PAYLOAD['dummy_param'],
        )

        payload = dict(MOCK_PERIPHERAL2_PAYLOAD)
        payload.pop('static')
        payload.pop('id')
        request = mock_api_request_maker('POST', '/api/peripherals', access_level=core_api.ACCESS_LEVEL_ADMIN)

        spy_add = mocker.patch('qtoggleserver.peripherals.add', return_value=mock_peripheral2)
        spy_init_ports = mocker.patch('qtoggleserver.peripherals.init_ports')
        result = await peripherals_api_funcs.post_peripherals(request, payload)

        spy_add.assert_called_once_with(payload)
        spy_init_ports.assert_called_once_with(mock_peripheral2)

        assert result == MOCK_PERIPHERAL2_PAYLOAD

    async def test_ok_with_id(self, mocker, mock_api_request_maker, mock_peripheral1):
        mock_peripheral2 = MockPeripheral(
            name=MOCK_PERIPHERAL2_PAYLOAD['name'],
            dummy_param=MOCK_PERIPHERAL2_PAYLOAD['dummy_param'],
        )

        payload = dict(MOCK_PERIPHERAL2_PAYLOAD)
        payload.pop('static')
        payload.pop('name')
        request = mock_api_request_maker('POST', '/api/peripherals', access_level=core_api.ACCESS_LEVEL_ADMIN)

        spy_add = mocker.patch('qtoggleserver.peripherals.add', return_value=mock_peripheral2)
        spy_init_ports = mocker.patch('qtoggleserver.peripherals.init_ports')
        result = await peripherals_api_funcs.post_peripherals(request, payload)

        spy_add.assert_called_once_with(payload)
        spy_init_ports.assert_called_once_with(mock_peripheral2)

        payload = dict(MOCK_PERIPHERAL2_PAYLOAD)
        payload.pop('name')
        assert result == payload

    async def test_ok_no_name_no_id(self, mocker, mock_api_request_maker, mock_peripheral1):
        mock_peripheral2 = MockPeripheral(
            name=MOCK_PERIPHERAL2_PAYLOAD['name'],
            dummy_param=MOCK_PERIPHERAL2_PAYLOAD['dummy_param'],
        )

        payload = dict(MOCK_PERIPHERAL2_PAYLOAD)
        payload.pop('static')
        payload.pop('name')
        payload.pop('id')
        request = mock_api_request_maker('POST', '/api/peripherals', access_level=core_api.ACCESS_LEVEL_ADMIN)

        spy_add = mocker.patch('qtoggleserver.peripherals.add', return_value=mock_peripheral2)
        spy_init_ports = mocker.patch('qtoggleserver.peripherals.init_ports')
        result = await peripherals_api_funcs.post_peripherals(request, payload)

        spy_add.assert_called_once_with(payload)
        spy_init_ports.assert_called_once_with(mock_peripheral2)

        payload = dict(MOCK_PERIPHERAL2_PAYLOAD)
        payload.pop('name')
        payload.pop('id')
        assert result.pop('id')
        assert result == payload

    async def test_normal_user_permissions(self, mock_api_request_maker, mock_peripheral1):
        payload = dict(MOCK_PERIPHERAL2_PAYLOAD)
        payload.pop('static')
        request = mock_api_request_maker('POST', '/api/peripherals', access_level=core_api.ACCESS_LEVEL_NORMAL)

        with pytest.raises(core_api.APIError, match='forbidden'):
            await peripherals_api_funcs.post_peripherals(request, payload)

    async def test_viewonly_user_permissions(self, mock_api_request_maker, mock_peripheral1):
        payload = dict(MOCK_PERIPHERAL2_PAYLOAD)
        payload.pop('static')
        request = mock_api_request_maker('POST', '/api/peripherals', access_level=core_api.ACCESS_LEVEL_VIEWONLY)

        with pytest.raises(core_api.APIError, match='forbidden'):
            await peripherals_api_funcs.post_peripherals(request, payload)

    async def test_anonymous_user_permissions(self, mock_api_request_maker, mock_peripheral1):
        payload = dict(MOCK_PERIPHERAL2_PAYLOAD)
        payload.pop('static')
        request = mock_api_request_maker('POST', '/api/peripherals', access_level=core_api.ACCESS_LEVEL_NONE)

        with pytest.raises(core_api.APIError, match='authentication-required'):
            await peripherals_api_funcs.post_peripherals(request, payload)


class TestDeletePeripheral:
    async def test_ok(self, mocker, mock_api_request_maker, mock_peripheral1):
        request = mock_api_request_maker(
            'DELETE', f'/api/peripherals/{mock_peripheral1.get_id()}', access_level=core_api.ACCESS_LEVEL_ADMIN
        )
        spy_cleanup_ports = mocker.patch('qtoggleserver.peripherals.cleanup_ports')
        spy_remove = mocker.patch('qtoggleserver.peripherals.remove')
        result = await peripherals_api_funcs.delete_peripheral(request, mock_peripheral1.get_id())

        spy_cleanup_ports.assert_called_once_with(mock_peripheral1, persisted_data=True)
        spy_remove.assert_called_once_with(mock_peripheral1.get_id(), persisted_data=True)
        assert result is None

    async def test_normal_user_permissions(self, mock_api_request_maker, mock_peripheral1):
        request = mock_api_request_maker(
            'DELETE', f'/api/peripherals/{mock_peripheral1.get_id()}', access_level=core_api.ACCESS_LEVEL_NORMAL
        )
        with pytest.raises(core_api.APIError, match='forbidden'):
            await peripherals_api_funcs.delete_peripheral(request, mock_peripheral1.get_id())

    async def test_viewonly_user_permissions(self, mock_api_request_maker, mock_peripheral1):
        request = mock_api_request_maker(
            'DELETE', f'/api/peripherals/{mock_peripheral1.get_id()}', access_level=core_api.ACCESS_LEVEL_VIEWONLY
        )
        with pytest.raises(core_api.APIError, match='forbidden'):
            await peripherals_api_funcs.delete_peripheral(request, mock_peripheral1.get_id())

    async def test_anonymous_user_permissions(self, mock_api_request_maker, mock_peripheral1):
        request = mock_api_request_maker(
            'DELETE', f'/api/peripherals/{mock_peripheral1.get_id()}', access_level=core_api.ACCESS_LEVEL_NONE
        )
        with pytest.raises(core_api.APIError, match='authentication-required'):
            await peripherals_api_funcs.delete_peripheral(request, mock_peripheral1.get_id())


class TestPutPeripherals:
    async def test_ok(self, mocker, mock_api_request_maker, mock_peripheral1):
        mock_peripheral2 = MockPeripheral(
            name=MOCK_PERIPHERAL2_PAYLOAD['name'],
            dummy_param=MOCK_PERIPHERAL2_PAYLOAD['dummy_param'],
        )
        mock_peripheral3 = MockPeripheral(
            name=MOCK_PERIPHERAL3_PAYLOAD['name'],
            dummy_param=MOCK_PERIPHERAL3_PAYLOAD['dummy_param'],
        )
        payload2 = dict(MOCK_PERIPHERAL2_PAYLOAD)
        payload3 = dict(MOCK_PERIPHERAL3_PAYLOAD)
        payload2.pop('static')
        payload3.pop('static')

        request = mock_api_request_maker('PUT', '/api/peripherals', access_level=core_api.ACCESS_LEVEL_ADMIN)
        spy_cleanup_ports = mocker.patch('qtoggleserver.peripherals.cleanup_ports')
        spy_remove = mocker.patch('qtoggleserver.peripherals.remove')
        spy_add = mocker.patch('qtoggleserver.peripherals.add', side_effect=[mock_peripheral2, mock_peripheral3])
        spy_init_ports = mocker.patch('qtoggleserver.peripherals.init_ports')

        result = await peripherals_api_funcs.put_peripherals(request, [payload2, payload3])

        spy_cleanup_ports.assert_called_once_with(mock_peripheral1, persisted_data=True)
        spy_remove.assert_called_once_with(mock_peripheral1.get_id(), persisted_data=True)
        spy_add.assert_has_calls([mocker.call(payload2), mocker.call(payload3)])
        spy_init_ports.assert_has_calls([mocker.call(mock_peripheral2), mocker.call(mock_peripheral3)])

        assert result is None

    async def test_normal_user_permissions(self, mock_api_request_maker, mock_peripheral1):
        request = mock_api_request_maker(
            'PUT', f'/api/peripherals', access_level=core_api.ACCESS_LEVEL_NORMAL
        )
        with pytest.raises(core_api.APIError, match='forbidden'):
            await peripherals_api_funcs.put_peripherals(request, [])

    async def test_viewonly_user_permissions(self, mock_api_request_maker, mock_peripheral1):
        request = mock_api_request_maker(
            'PUT', f'/api/peripherals', access_level=core_api.ACCESS_LEVEL_VIEWONLY
        )
        with pytest.raises(core_api.APIError, match='forbidden'):
            await peripherals_api_funcs.put_peripherals(request, [])

    async def test_anonymous_user_permissions(self, mock_api_request_maker, mock_peripheral1):
        request = mock_api_request_maker(
            'PUT', f'/api/peripherals', access_level=core_api.ACCESS_LEVEL_NONE
        )
        with pytest.raises(core_api.APIError, match='authentication-required'):
            await peripherals_api_funcs.put_peripherals(request, [])