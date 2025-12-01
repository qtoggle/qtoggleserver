import asyncio

from qtoggleserver.core import main


async def test_expression_port_write_only_changed(mock_num_port1, mocker):
    """Should only write the expression evaluation result to port if value different from previously written value."""

    mock_num_port1.set_expression("IF(GT(TIMEMS(), 0), 30, 10)")
    mocker.patch.object(mock_num_port1, "transform_and_write_value")

    mock_num_port1._last_write_value = 40
    await main.update()
    await asyncio.sleep(0.1)
    mock_num_port1.transform_and_write_value.assert_called_once_with(30)

    mock_num_port1._last_write_value = 30
    mock_num_port1.transform_and_write_value.reset_mock()
    await main.update()
    await asyncio.sleep(0.1)
    mock_num_port1.transform_and_write_value.assert_not_called()
