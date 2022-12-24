import asyncio
import time

from qtoggleserver.core import main


async def test_eval_trigger_set_expression(mocker, mock_num_port1, mock_num_port2):
    mock_num_port1.set_last_read_value(4)
    mock_num_port2.set_last_read_value(5)
    mock_num_port2.set_writable(True)
    mocker.patch.object(mock_num_port2, 'transform_and_write_value')

    await mock_num_port2.set_attr('expression', 'MUL($nid1, 10)')
    await asyncio.sleep(0.1)
    mock_num_port2.transform_and_write_value.assert_called_once_with(40)


async def test_eval_trigger_value_change(mocker, mock_num_port1, mock_num_port2):
    mock_num_port1.set_last_read_value(4)
    mock_num_port2.set_last_read_value(5)
    mock_num_port2.set_writable(True)
    await mock_num_port2.set_attr('expression', 'MUL($nid1, 10)')
    await asyncio.sleep(0.1)  # eats up the eval() due to setting an expression

    mock_num_port1.set_next_value(6)
    mocker.patch.object(mock_num_port2, 'transform_and_write_value')
    await main.update()
    await asyncio.sleep(0.1)
    mock_num_port2.transform_and_write_value.assert_called_once_with(60)


async def test_eval_trigger_value_change_self(mocker, mock_num_port1, mock_num_port2):
    mock_num_port1.set_last_read_value(4)
    mock_num_port2.set_last_read_value(5)
    mock_num_port2.set_writable(True)
    await mock_num_port2.set_attr('expression', 'MUL($nid1, $nid2)')
    await asyncio.sleep(0.1)  # eats up the eval() due to setting an expression

    mock_num_port1.set_next_value(6)
    mocker.patch.object(mock_num_port2, 'transform_and_write_value')

    # Call main.update() multiple times to catch possible evaluation loops due to self reference
    await main.update()
    await main.update()
    await main.update()
    await asyncio.sleep(0.1)
    mock_num_port2.transform_and_write_value.assert_called_once_with(30)


# async def test_eval_trigger_second(freezer, mocker, mock_num_port1, dummy_utc_datetime):
#     dummy_utc_datetime = dummy_utc_datetime.replace(microsecond=0)
#     freezer.move_to(dummy_utc_datetime)
#
#     mock_num_port1.set_last_read_value(4)
#     mock_num_port1.set_writable(True)
#     mocker.patch.object(mock_num_port1, 'transform_and_write_value')
#     await mock_num_port1.set_attr('expression', 'MUL(TIME(), 10)')
#     await asyncio.sleep(0.1)
#     mock_num_port1.transform_and_write_value.assert_called_once()
#     mock_num_port1.transform_and_write_value.reset_mock()
#
#     freezer.move_to(dummy_utc_datetime + datetime.timedelta(milliseconds=999))
#     await main.update()
#     await asyncio.sleep(0.1)
#     mock_num_port1.transform_and_write_value.assert_not_called()
#
#     freezer.move_to(dummy_utc_datetime + datetime.timedelta(milliseconds=1001))
#     await main.update()
#     await asyncio.sleep(0.1)
#     mock_num_port1.transform_and_write_value.assert_called_once()
#
#
# async def test_eval_trigger_millisecond(freezer, mocker, mock_num_port1):
#     mock_num_port1.set_last_read_value(4)
#     mock_num_port1.set_writable(True)
#     mocker.patch.object(mock_num_port1, 'transform_and_write_value')
#     await mock_num_port1.set_attr('expression', 'MUL(TIMEMS(), 10)')
#     await asyncio.sleep(0.1)
#     mock_num_port1.transform_and_write_value.assert_called_once()


async def test_eval_trigger_ignore_disabled_port(mocker, mock_num_port1, mock_num_port2):
    mock_num_port1.set_last_read_value(4)
    mock_num_port2.set_last_read_value(5)
    mock_num_port2.set_writable(True)
    await mock_num_port2.set_attr('expression', 'MUL($nid1, 10)')
    await mock_num_port2.disable()
    await asyncio.sleep(0.1)

    mock_num_port1.set_next_value(6)
    mocker.patch.object(mock_num_port2, 'transform_and_write_value')
    await main.update()
    mock_num_port2.transform_and_write_value.assert_not_called()


async def test_eval_trigger_ignore_inexistent_port(mocker, mock_num_port1, mock_num_port2):
    mock_num_port1.set_last_read_value(4)
    mock_num_port2.set_last_read_value(5)
    mock_num_port2.set_writable(True)
    await mock_num_port2.set_attr('expression', 'MUL($nid1, $inexistent)')
    await asyncio.sleep(0.1)

    mock_num_port1.set_next_value(6)
    mocker.patch.object(mock_num_port2, 'transform_and_write_value')
    await main.update()
    mock_num_port2.transform_and_write_value.assert_not_called()


async def test_asap_eval_paused(mocker, mock_num_port1, dummy_eval_context):
    mock_num_port1.set_writable(True)
    await mock_num_port1.set_attr('expression', 'MILLISECOND()')
    e = mock_num_port1.get_expression()

    mocker.patch.object(e, 'eval')
    await main.update()
    await asyncio.sleep(0.1)
    e.eval.assert_called()

    # Reset eval queue
    while True:
        try:
            mock_num_port1._eval_queue.get_nowait()
        except asyncio.QueueEmpty:
            break

    e.pause_asap_eval(time.time() * 1000 + 1000)
    mocker.patch.object(e, 'eval')
    await main.update()
    await asyncio.sleep(0.1)
    e.eval.assert_not_called()


async def test_asap_eval_paused_value_change(mocker, mock_num_port1, mock_num_port2, dummy_eval_context):
    mock_num_port1.set_writable(True)
    mock_num_port2.set_last_read_value(4)
    await mock_num_port1.set_attr('expression', 'ADD(MILLISECOND(), $nid2)')
    e = mock_num_port1.get_expression()

    # Reset eval queue
    while True:
        try:
            mock_num_port1._eval_queue.get_nowait()
        except asyncio.QueueEmpty:
            break

    mock_num_port2.set_next_value(5)
    e.pause_asap_eval(time.time() * 1000 + 1000)
    mocker.patch.object(e, 'eval')
    await main.update()
    await asyncio.sleep(0.1)
    e.eval.assert_called()
