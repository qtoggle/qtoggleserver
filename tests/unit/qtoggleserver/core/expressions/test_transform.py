import pytest

from qtoggleserver.core.ports import InvalidAttributeValue


class TestPortTransformRead:
    async def test(self, mock_num_port1):
        await mock_num_port1.set_attr("transform_read", "MUL($, 10)")
        mock_num_port1.set_last_read_value(4)
        mock_num_port1.set_next_value(5)
        assert await mock_num_port1.read_transformed_value() == 50

    async def test_transform_not_supported(self, mock_num_port1):
        """Should raise `TransformNotSupported` when expression depends on another port."""

        with pytest.raises(InvalidAttributeValue) as exc_info:
            await mock_num_port1.set_attr("transform_read", "MUL($another_port, 10)")
        assert exc_info.value.details == {"reason": "transform-not-supported", "token": "$another_port", "pos": 5}

    async def test_port_reference_forbidden(self, mock_num_port1):
        """Should raise `TransformNotSupported` when expression contains a port reference."""

        with pytest.raises(InvalidAttributeValue) as exc_info:
            await mock_num_port1.set_attr("transform_read", "@another_port")
        assert exc_info.value.details == {"reason": "transform-not-supported", "token": "@another_port", "pos": 1}

    async def test_self_port_reference_forbidden(self, mock_num_port1):
        """Should raise `TransformNotSupported` when expression contains a self port reference."""

        with pytest.raises(InvalidAttributeValue) as exc_info:
            await mock_num_port1.set_attr("transform_read", "@")
        assert exc_info.value.details == {"reason": "transform-not-supported", "token": "@", "pos": 1}

    async def test_port_attribute_forbidden(self, mock_num_port1):
        """Should raise `TransformNotSupported` when expression contains a port attribute."""

        with pytest.raises(InvalidAttributeValue) as exc_info:
            await mock_num_port1.set_attr("transform_read", "$another_port:enabled")
        assert exc_info.value.details == {
            "reason": "transform-not-supported",
            "token": "$another_port:enabled",
            "pos": 1,
        }

    async def test_self_port_attribute_forbidden(self, mock_num_port1):
        """Should raise `TransformNotSupported` when expression contains a self port attribute."""

        with pytest.raises(InvalidAttributeValue) as exc_info:
            await mock_num_port1.set_attr("transform_read", "$:enabled")
        assert exc_info.value.details == {"reason": "transform-not-supported", "token": "$:enabled", "pos": 1}

    async def test_device_attribute_forbidden(self, mock_num_port1):
        """Should raise `TransformNotSupported` when expression contains a device attribute."""

        with pytest.raises(InvalidAttributeValue) as exc_info:
            await mock_num_port1.set_attr("transform_read", "#:name")
        assert exc_info.value.details == {"reason": "transform-not-supported", "token": "#:name", "pos": 1}


class TestPortTransformWrite:
    async def test(self, mock_num_port1, mocker):
        mock_num_port1.set_writable(True)
        mocker.patch.object(mock_num_port1, "write_value")

        await mock_num_port1.set_attr("transform_write", "MUL($, 10)")
        mock_num_port1.set_last_read_value(4)
        mock_num_port1.set_next_value(5)

        await mock_num_port1.transform_and_write_value(6)
        mock_num_port1.write_value.assert_called_once_with(60)

    async def test_transform_not_supported(self, mock_num_port1):
        """Should raise `TransformNotSupported` when expression depends on another port."""

        mock_num_port1.set_writable(True)
        with pytest.raises(InvalidAttributeValue) as exc_info:
            await mock_num_port1.set_attr("transform_write", "MUL($another_port, 10)")
        assert exc_info.value.details == {"reason": "transform-not-supported", "token": "$another_port", "pos": 5}

    async def test_port_reference_forbidden(self, mock_num_port1):
        """Should raise `TransformNotSupported` when expression contains a port reference."""

        mock_num_port1.set_writable(True)
        with pytest.raises(InvalidAttributeValue) as exc_info:
            await mock_num_port1.set_attr("transform_write", "@another_port")
        assert exc_info.value.details == {"reason": "transform-not-supported", "token": "@another_port", "pos": 1}

    async def test_device_attribute_forbidden(self, mock_num_port1):
        """Should raise `TransformNotSupported` when expression contains a device attribute."""

        mock_num_port1.set_writable(True)
        with pytest.raises(InvalidAttributeValue) as exc_info:
            await mock_num_port1.set_attr("transform_write", "#:name")
        assert exc_info.value.details == {"reason": "transform-not-supported", "token": "#:name", "pos": 1}
