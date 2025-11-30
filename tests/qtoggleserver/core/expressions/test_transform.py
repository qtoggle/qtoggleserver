import pytest

from qtoggleserver.core.ports import InvalidAttributeValue


class TestPortTransformRead:
    async def test(self, mock_num_port1):
        await mock_num_port1.set_attr("transform_read", "MUL($, 10)")
        mock_num_port1.set_last_read_value(4)
        mock_num_port1.set_next_value(5)
        assert await mock_num_port1.read_transformed_value() == 50

    async def test_non_self_dependency(self, mock_num_port1):
        """Should (indirectly) raise `NonSelfDependency` when expression depends on another port."""

        with pytest.raises(InvalidAttributeValue) as exc_info:
            await mock_num_port1.set_attr("transform_read", "MUL($another_port, 10)")
        assert exc_info.value.details == {"reason": "non-self-dependency", "token": "another_port", "pos": 4}


class TestPortTransformWrite:
    async def test(self, mock_num_port1, mocker):
        mock_num_port1.set_writable(True)
        mocker.patch.object(mock_num_port1, "write_value")

        await mock_num_port1.set_attr("transform_write", "MUL($, 10)")
        mock_num_port1.set_last_read_value(4)
        mock_num_port1.set_next_value(5)

        await mock_num_port1.transform_and_write_value(6)
        mock_num_port1.write_value.assert_called_once_with(60)

    async def test_non_self_dependency(self, mock_num_port1):
        """Should (indirectly) raise `NonSelfDependency` when expression depends on another port."""

        mock_num_port1.set_writable(True)
        with pytest.raises(InvalidAttributeValue) as exc_info:
            await mock_num_port1.set_attr("transform_write", "MUL($another_port, 10)")
        assert exc_info.value.details == {"reason": "non-self-dependency", "token": "another_port", "pos": 4}
