import asyncio

from qtoggleserver.core import main


async def test_expression_port_write_only_changed(mock_num_port1, mocker):
    """Should only write the expression evaluation result to port if value different from last value."""

    mock_num_port1.set_expression("IF(GT(TIMEMS(), 0), 30, 10)")
    mocker.patch.object(mock_num_port1, "transform_and_write_value")

    mocker.patch.object(mock_num_port1, "get_pending_value", return_value=40)
    await main.update()
    await asyncio.sleep(0.1)
    mock_num_port1.transform_and_write_value.assert_called_once_with(30)

    mocker.patch.object(mock_num_port1, "get_pending_value", return_value=30)
    mock_num_port1.transform_and_write_value.reset_mock()
    await main.update()
    await asyncio.sleep(0.1)
    mock_num_port1.transform_and_write_value.assert_not_called()


async def test_expression_port_self_value(mock_num_port1):
    """Test that a port can reference its own value using `$`."""

    mock_num_port1.set_writable(True)
    mock_num_port1.set_last_read_value(15)
    await mock_num_port1.set_attr("expression", "ADD($, 1)")
    mock_num_port1.set_last_read_value(25)
    await asyncio.sleep(0.1)
    assert mock_num_port1.get_last_written_value() == 16


async def test_expression_port_own_value(mock_num_port1):
    """Test that a port can reference its own value using its id."""

    mock_num_port1.set_writable(True)
    mock_num_port1.set_last_read_value(15)
    await mock_num_port1.set_attr("expression", "ADD($nid1, 1)")
    mock_num_port1.set_last_read_value(25)
    await asyncio.sleep(0.1)
    assert mock_num_port1.get_last_written_value() == 16
