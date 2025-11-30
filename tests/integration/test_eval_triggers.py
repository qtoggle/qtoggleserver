import asyncio

from qtoggleserver.core import main


async def test_eval_trigger_set_expression(mock_num_port1, mock_num_port2, mocker):
    """Should trigger expression evaluation and write resulted value when setting an expression to a port."""

    mock_num_port1.set_last_read_value(4)
    mock_num_port2.set_last_read_value(5)
    mock_num_port2.set_writable(True)
    mocker.patch.object(mock_num_port2, "transform_and_write_value")

    await mock_num_port2.set_attr("expression", "MUL($nid1, 10)")
    await asyncio.sleep(0.1)
    mock_num_port2.transform_and_write_value.assert_called_once_with(40)


async def test_eval_trigger_value_change(mock_num_port1, mock_num_port2, mocker):
    """Should trigger expression evaluation and write resulted value when a dependent port's value changes."""

    mock_num_port1.set_last_read_value(4)
    mock_num_port2.set_last_read_value(5)
    mock_num_port2.set_writable(True)
    mock_num_port2.set_expression("MUL($nid1, 10)")
    mock_num_port1.set_next_value(6)

    mocker.patch.object(mock_num_port2, "transform_and_write_value")
    await main.update()
    await asyncio.sleep(0.1)
    mock_num_port2.transform_and_write_value.assert_called_once_with(60)


async def test_eval_trigger_value_change_own(mock_num_port1, mock_num_port2, mocker):
    """Should trigger expression evaluation and write resulted value when own port value changes, as a regular dep."""

    mock_num_port1.set_last_read_value(4)
    mock_num_port2.set_last_read_value(5)
    mock_num_port2.set_writable(True)
    mock_num_port2.set_expression("MUL($nid1, $nid2)")
    mock_num_port1.set_next_value(6)
    mocker.patch.object(mock_num_port2, "transform_and_write_value")

    await main.update()
    await asyncio.sleep(0.1)
    mock_num_port2.transform_and_write_value.assert_called_once_with(30)


async def test_eval_trigger_ignore_inexistent_port(mock_num_port1, mock_num_port2, mocker):
    """Should not trigger expression evaluation when expression includes an inexistent port."""

    mock_num_port1.set_last_read_value(4)
    mock_num_port2.set_last_read_value(5)
    mock_num_port2.set_writable(True)
    mock_num_port2.set_expression("MUL($nid1, $inexistent)")
    mock_num_port1.set_next_value(6)
    mocker.patch.object(mock_num_port2, "transform_and_write_value")

    await main.update()
    await asyncio.sleep(0.1)
    mock_num_port2.transform_and_write_value.assert_not_called()


async def test_eval_trigger_port_enabled(mock_num_port1, mocker):
    """Should trigger expression evaluation and write resulted value when port becomes enabled."""

    mock_num_port1.set_last_read_value(4)
    mock_num_port1.set_writable(True)
    mock_num_port1.set_expression("MUL($, 10)")
    mock_num_port1.set_next_value(6)
    mocker.patch.object(mock_num_port1, "transform_and_write_value")

    await mock_num_port1.disable()
    await main.update()
    await asyncio.sleep(0.1)
    mock_num_port1.transform_and_write_value.assert_not_called()

    await mock_num_port1.enable()
    await main.update()
    await asyncio.sleep(0.1)
    mock_num_port1.transform_and_write_value.assert_called_once_with(60)
