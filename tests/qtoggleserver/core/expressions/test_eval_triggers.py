
import datetime

from qtoggleserver.core import main
from qtoggleserver.core import ports as core_ports


async def test_eval_trigger_set_expression(mocker, num_mock_port1, num_mock_port2):
    num_mock_port1.set_value(4)
    num_mock_port2.set_value(5)
    num_mock_port2.set_writable(True)
    mocker.patch.object(num_mock_port2, 'push_value')

    await num_mock_port2.set_attr('expression', 'MUL($nid1, 10)')
    num_mock_port2.push_value.assert_called_once_with(40, reason=core_ports.CHANGE_REASON_EXPRESSION)


async def test_eval_trigger_value_change(mocker, num_mock_port1, num_mock_port2):
    num_mock_port1.set_value(4)
    num_mock_port2.set_value(5)
    num_mock_port2.set_writable(True)
    await num_mock_port2.set_attr('expression', 'MUL($nid1, 10)')

    num_mock_port1.set_next_value(6)
    mocker.patch.object(num_mock_port2, 'push_value')
    await main.update()
    num_mock_port2.push_value.assert_called_once_with(60, reason=core_ports.CHANGE_REASON_EXPRESSION)


async def test_eval_trigger_value_change_self(mocker, num_mock_port1, num_mock_port2):
    num_mock_port1.set_value(4)
    num_mock_port2.set_value(5)
    num_mock_port2.set_writable(True)
    await num_mock_port2.set_attr('expression', 'MUL($nid1, $nid2)')

    num_mock_port1.set_next_value(6)
    mocker.patch.object(num_mock_port2, 'push_value')

    # Call main.update() multiple times to catch possible evaluation loops due to self reference
    await main.update()
    await main.update()
    await main.update()
    num_mock_port2.push_value.assert_called_once_with(30, reason=core_ports.CHANGE_REASON_EXPRESSION)


async def test_eval_trigger_second(freezer, mocker, num_mock_port1, dummy_utc_datetime):
    dummy_utc_datetime = dummy_utc_datetime.replace(microsecond=0)
    freezer.move_to(dummy_utc_datetime)

    num_mock_port1.set_value(4)
    num_mock_port1.set_writable(True)
    await num_mock_port1.set_attr('expression', 'MUL(TIME(), 10)')
    mocker.patch.object(num_mock_port1, 'push_value')

    await main.update()
    num_mock_port1.push_value.assert_not_called()

    freezer.move_to(dummy_utc_datetime + datetime.timedelta(milliseconds=999))
    await main.update()
    num_mock_port1.push_value.assert_not_called()

    freezer.move_to(dummy_utc_datetime + datetime.timedelta(milliseconds=1001))
    await main.update()
    num_mock_port1.push_value.assert_called_once()


async def test_eval_trigger_millisecond(freezer, mocker, num_mock_port1):
    num_mock_port1.set_value(4)
    num_mock_port1.set_writable(True)
    await num_mock_port1.set_attr('expression', 'MUL(TIMEMS(), 10)')
    mocker.patch.object(num_mock_port1, 'push_value')

    await main.update()
    num_mock_port1.push_value.assert_called_once()


async def test_eval_trigger_ignore_disabled_port(mocker, num_mock_port1, num_mock_port2):
    num_mock_port1.set_value(4)
    num_mock_port2.set_value(5)
    num_mock_port2.set_writable(True)
    await num_mock_port2.set_attr('expression', 'MUL($nid1, 10)')
    await num_mock_port2.disable()

    num_mock_port1.set_next_value(6)
    mocker.patch.object(num_mock_port2, 'push_value')
    await main.update()
    num_mock_port2.push_value.assert_not_called()


async def test_eval_trigger_ignore_inexistent_port(mocker, num_mock_port1, num_mock_port2):
    num_mock_port1.set_value(4)
    num_mock_port2.set_value(5)
    num_mock_port2.set_writable(True)
    await num_mock_port2.set_attr('expression', 'MUL($nid1, $inexistent)')

    num_mock_port1.set_next_value(6)
    mocker.patch.object(num_mock_port2, 'push_value')
    await main.update()
    num_mock_port2.push_value.assert_not_called()
