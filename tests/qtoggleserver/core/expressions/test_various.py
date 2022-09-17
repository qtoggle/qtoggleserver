
import pytest

from qtoggleserver.core import history
from qtoggleserver.core.expressions import various, EvalContext, Function
from qtoggleserver.core.expressions import InvalidNumberOfArguments, InvalidArgumentKind, PortValueUnavailable

from tests.qtoggleserver.mock import MockExpression, MockPortRef, MockPortValue


async def test_available_literal(literal_three, literal_false, dummy_eval_context):
    expr = various.AvailableFunction([literal_three])
    assert await expr.eval(dummy_eval_context) == 1

    expr = various.AvailableFunction([literal_false])
    assert await expr.eval(dummy_eval_context) == 1


async def test_available_port_value(num_mock_port1):
    port_expr = MockPortValue(num_mock_port1)
    expr = various.AvailableFunction([port_expr])
    assert await expr.eval(EvalContext(port_values={'nid1': num_mock_port1.get_last_read_value()}, now_ms=0)) == 0

    num_mock_port1.set_last_read_value(16)
    assert await expr.eval(EvalContext(port_values={'nid1': num_mock_port1.get_last_read_value()}, now_ms=0)) == 1

    port_expr = MockPortValue(None, port_id='some-id')
    expr = various.AvailableFunction([port_expr])
    assert await expr.eval(EvalContext(port_values={'nid1': num_mock_port1.get_last_read_value()}, now_ms=0)) == 0


async def test_available_port_ref(num_mock_port1, dummy_eval_context):
    port_expr = MockPortRef(num_mock_port1)
    expr = various.AvailableFunction([port_expr])
    assert await expr.eval(dummy_eval_context) == 1

    num_mock_port1.set_last_read_value(16)
    assert await expr.eval(dummy_eval_context) == 1

    port_expr = MockPortRef(None, port_id='some-id')
    expr = various.AvailableFunction([port_expr])
    assert await expr.eval(dummy_eval_context) == 0


async def test_available_func(num_mock_port1):
    port_expr = MockPortValue(num_mock_port1)
    acc_expr = MockExpression(13)
    func_expr = various.AccFunction([port_expr, acc_expr])
    expr = various.AvailableFunction([func_expr])
    assert await expr.eval(
        EvalContext(port_values={'nid1': num_mock_port1.get_last_read_value()}, now_ms=0)
    ) == 0

    num_mock_port1.set_last_read_value(16)
    assert await expr.eval(EvalContext(port_values={'nid1': num_mock_port1.get_last_read_value()}, now_ms=0)) == 1

    port_expr = MockPortValue(None, port_id='some-id')
    func_expr = various.AccFunction([port_expr, acc_expr])
    expr = various.AvailableFunction([func_expr])
    assert await expr.eval(EvalContext(port_values={'nid1': num_mock_port1.get_last_read_value()}, now_ms=0)) == 0


def test_available_parse():
    e = Function.parse(None, 'AVAILABLE(1)', 0)
    assert isinstance(e, various.AvailableFunction)


def test_available_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'AVAILABLE()', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'AVAILABLE(1, 2)', 0)


async def test_default(num_mock_port1):
    port_expr = MockPortValue(num_mock_port1)
    def_expr = MockExpression(13)
    expr = various.DefaultFunction([port_expr, def_expr])
    assert await expr.eval(EvalContext(port_values={'nid1': num_mock_port1.get_last_read_value()}, now_ms=0)) == 13

    num_mock_port1.set_last_read_value(16)
    assert await expr.eval(EvalContext(port_values={'nid1': num_mock_port1.get_last_read_value()}, now_ms=0)) == 16


def test_default_parse():
    e = Function.parse(None, 'DEFAULT(1, 2)', 0)
    assert isinstance(e, various.DefaultFunction)


def test_default_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'DEFAULT(1)', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'AVAILABLE(1, 2, 3)', 0)


async def test_rising(num_mock_port1):
    port_expr = MockPortValue(num_mock_port1)
    expr = various.RisingFunction([port_expr])

    num_mock_port1.set_last_read_value(10)
    assert await expr.eval(EvalContext(port_values={'nid1': num_mock_port1.get_last_read_value()}, now_ms=0)) == 0
    assert await expr.eval(EvalContext(port_values={'nid1': num_mock_port1.get_last_read_value()}, now_ms=0)) == 0

    num_mock_port1.set_last_read_value(13)
    assert await expr.eval(EvalContext(port_values={'nid1': num_mock_port1.get_last_read_value()}, now_ms=0)) == 1
    assert await expr.eval(EvalContext(port_values={'nid1': num_mock_port1.get_last_read_value()}, now_ms=0)) == 0

    num_mock_port1.set_last_read_value(9)
    assert await expr.eval(EvalContext(port_values={'nid1': num_mock_port1.get_last_read_value()}, now_ms=0)) == 0


def test_rising_parse():
    e = Function.parse(None, 'RISING(1)', 0)
    assert isinstance(e, various.RisingFunction)


def test_rising_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'RISING()', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'RISING(1, 2)', 0)


async def test_falling(num_mock_port1):
    port_expr = MockPortValue(num_mock_port1)
    expr = various.FallingFunction([port_expr])

    num_mock_port1.set_last_read_value(13)
    assert await expr.eval(EvalContext(port_values={'nid1': num_mock_port1.get_last_read_value()}, now_ms=0)) == 0
    assert await expr.eval(EvalContext(port_values={'nid1': num_mock_port1.get_last_read_value()}, now_ms=0)) == 0

    num_mock_port1.set_last_read_value(10)
    assert await expr.eval(EvalContext(port_values={'nid1': num_mock_port1.get_last_read_value()}, now_ms=0)) == 1
    assert await expr.eval(EvalContext(port_values={'nid1': num_mock_port1.get_last_read_value()}, now_ms=0)) == 0

    num_mock_port1.set_last_read_value(14)
    assert await expr.eval(EvalContext(port_values={'nid1': num_mock_port1.get_last_read_value()}, now_ms=0)) == 0


def test_falling_parse():
    e = Function.parse(None, 'FALLING(1)', 0)
    assert isinstance(e, various.FallingFunction)


def test_falling_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'FALLING()', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'FALLING(1, 2)', 0)


async def test_acc(dummy_eval_context):
    value_expr = MockExpression(16)
    acc_expr = MockExpression(13)
    expr = various.AccFunction([value_expr, acc_expr])
    assert await expr.eval(dummy_eval_context) == 13

    acc_expr.set_value(-5)
    assert await expr.eval(dummy_eval_context) == -5

    value_expr.set_value(26)
    assert await expr.eval(dummy_eval_context) == 5

    value_expr.set_value(20)
    acc_expr.set_value(5)
    assert await expr.eval(dummy_eval_context) == -1


def test_acc_parse():
    e = Function.parse(None, 'ACC(1, 2)', 0)
    assert isinstance(e, various.AccFunction)


def test_acc_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'ACC(1)', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'ACC(1, 2, 3)', 0)


async def test_accinc(dummy_eval_context):
    value_expr = MockExpression(16)
    acc_expr = MockExpression(13)
    expr = various.AccIncFunction([value_expr, acc_expr])
    assert await expr.eval(dummy_eval_context) == 13

    acc_expr.set_value(-5)
    assert await expr.eval(dummy_eval_context) == -5

    value_expr.set_value(26)
    assert await expr.eval(dummy_eval_context) == 5

    value_expr.set_value(20)
    acc_expr.set_value(5)
    assert await expr.eval(dummy_eval_context) == 5


def test_accinc_parse():
    e = Function.parse(None, 'ACCINC(1, 2)', 0)
    assert isinstance(e, various.AccIncFunction)


def test_accinc_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'ACCINC(1)', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'ACCINC(1, 2, 3)', 0)


async def test_hyst_rise(literal_three, literal_sixteen, dummy_eval_context):
    value_expr = MockExpression(1)
    expr = various.HystFunction([value_expr, literal_three, literal_sixteen])
    assert await expr.eval(dummy_eval_context) == 0

    value_expr.set_value(2)
    assert await expr.eval(dummy_eval_context) == 0

    value_expr.set_value(3)
    assert await expr.eval(dummy_eval_context) == 0

    value_expr.set_value(4)
    assert await expr.eval(dummy_eval_context) == 0

    value_expr.set_value(16)
    assert await expr.eval(dummy_eval_context) == 0

    value_expr.set_value(10)
    assert await expr.eval(dummy_eval_context) == 0

    value_expr.set_value(2)
    assert await expr.eval(dummy_eval_context) == 0

    value_expr.set_value(17)
    assert await expr.eval(dummy_eval_context) == 1

    value_expr.set_value(20)
    assert await expr.eval(dummy_eval_context) == 1


async def test_hyst_fall(literal_three, literal_sixteen, dummy_eval_context):
    value_expr = MockExpression(20)
    expr = various.HystFunction([value_expr, literal_three, literal_sixteen])
    assert await expr.eval(dummy_eval_context) == 1

    value_expr.set_value(17)
    assert await expr.eval(dummy_eval_context) == 1

    value_expr.set_value(16)
    assert await expr.eval(dummy_eval_context) == 1

    value_expr.set_value(10)
    assert await expr.eval(dummy_eval_context) == 1

    value_expr.set_value(4)
    assert await expr.eval(dummy_eval_context) == 1

    value_expr.set_value(20)
    assert await expr.eval(dummy_eval_context) == 1

    value_expr.set_value(3)
    assert await expr.eval(dummy_eval_context) == 1

    value_expr.set_value(2)
    assert await expr.eval(dummy_eval_context) == 0

    value_expr.set_value(0)
    assert await expr.eval(dummy_eval_context) == 0


def test_hyst_parse():
    e = Function.parse(None, 'HYST(1, 2, 3)', 0)
    assert isinstance(e, various.HystFunction)


def test_hyst_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'HYST(1, 2)', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'HYST(1, 2, 3, 4)', 0)


async def test_onoffauto(dummy_eval_context):
    value_expr = MockExpression(0)
    auto_expr = MockExpression(13)
    expr = various.OnOffAutoFunction([value_expr, auto_expr])

    value_expr.set_value(0)
    assert await expr.eval(dummy_eval_context) == 13

    value_expr.set_value(-1)
    assert await expr.eval(dummy_eval_context) is False

    value_expr.set_value(-10)
    assert await expr.eval(dummy_eval_context) is False

    value_expr.set_value(1)
    assert await expr.eval(dummy_eval_context) is True

    value_expr.set_value(10)
    assert await expr.eval(dummy_eval_context) is True


def test_onoffauto_parse():
    e = Function.parse(None, 'ONOFFAUTO(1, 2)', 0)
    assert isinstance(e, various.OnOffAutoFunction)


def test_onoffauto_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'ONOFFAUTO(1)', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'ONOFFAUTO(1, 2, 3)', 0)


async def test_sequence(
    dummy_local_datetime,
    literal_two,
    literal_three,
    literal_sixteen,
    literal_one_hundred,
    literal_two_hundreds,
    dummy_eval_context,
    later_eval_context,
):
    expr = various.SequenceFunction([
        literal_three,
        literal_one_hundred,
        literal_sixteen,
        literal_two_hundreds,
        literal_two,
        literal_one_hundred
    ])
    assert await expr.eval(dummy_eval_context) == 3
    assert await expr.eval(later_eval_context(99)) == 3
    assert await expr.eval(later_eval_context(101)) == 16
    assert await expr.eval(later_eval_context(200)) == 16
    assert await expr.eval(later_eval_context(299)) == 16
    assert await expr.eval(later_eval_context(301)) == 2
    assert await expr.eval(later_eval_context(399)) == 2
    assert await expr.eval(later_eval_context(401)) == 3


def test_sequence_parse():
    e = Function.parse(None, 'SEQUENCE(1, 2, 3, 4)', 0)
    assert isinstance(e, various.SequenceFunction)


def test_sequence_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'SEQUENCE(1)', 0)


async def test_lut(
    literal_two,
    literal_three,
    literal_sixteen,
    literal_one_hundred,
    literal_two_hundreds,
    literal_one_thousand,
    dummy_eval_context,
):
    value_expr = MockExpression(0)
    expr = various.LUTFunction([
        value_expr,
        literal_three,
        literal_two_hundreds,
        literal_sixteen,
        literal_one_thousand,
        literal_two,
        literal_one_hundred
    ])
    assert await expr.eval(dummy_eval_context) == 100

    value_expr.set_value(2)
    assert await expr.eval(dummy_eval_context) == 100

    value_expr.set_value(2.4)
    assert await expr.eval(dummy_eval_context) == 100

    value_expr.set_value(2.6)
    assert await expr.eval(dummy_eval_context) == 200

    value_expr.set_value(3)
    assert await expr.eval(dummy_eval_context) == 200

    value_expr.set_value(5)
    assert await expr.eval(dummy_eval_context) == 200

    value_expr.set_value(9.4)
    assert await expr.eval(dummy_eval_context) == 200

    value_expr.set_value(9.6)
    assert await expr.eval(dummy_eval_context) == 1000

    value_expr.set_value(100)
    assert await expr.eval(dummy_eval_context) == 1000


def test_lut_parse():
    e = Function.parse(None, 'LUT(1, 2, 3, 4, 5)', 0)
    assert isinstance(e, various.LUTFunction)


def test_lut_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'LUT(1)', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'LUT(1, 2)', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'LUT(1, 2, 3, 4)', 0)


async def test_lutli(
    literal_two,
    literal_three,
    literal_sixteen,
    literal_one_hundred,
    literal_two_hundreds,
    literal_one_thousand,
    dummy_eval_context,
):
    value_expr = MockExpression(0)
    expr = various.LUTLIFunction([
        value_expr,
        literal_three,
        literal_two_hundreds,
        literal_sixteen,
        literal_one_thousand,
        literal_two,
        literal_one_hundred
    ])
    assert await expr.eval(dummy_eval_context) == 100

    value_expr.set_value(2)
    assert await expr.eval(dummy_eval_context) == 100

    value_expr.set_value(2.4)
    assert await expr.eval(dummy_eval_context) == 140

    value_expr.set_value(2.6)
    assert await expr.eval(dummy_eval_context) == 160

    value_expr.set_value(3)
    assert await expr.eval(dummy_eval_context) == 200

    value_expr.set_value(5)
    assert round(await expr.eval(dummy_eval_context), 2) == 323.08

    value_expr.set_value(9.4)
    assert round(await expr.eval(dummy_eval_context), 2) == 593.85

    value_expr.set_value(9.6)
    assert round(await expr.eval(dummy_eval_context), 2) == 606.15

    value_expr.set_value(16)
    assert round(await expr.eval(dummy_eval_context), 2) == 1000

    value_expr.set_value(100)
    assert round(await expr.eval(dummy_eval_context), 2) == 1000


def test_lutli_parse():
    e = Function.parse(None, 'LUTLI(1, 2, 3, 4, 5)', 0)
    assert isinstance(e, various.LUTLIFunction)


def test_lutli_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'LUTLI(1)', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'LUTLI(1, 2)', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'LUTLI(1, 2, 3, 4)', 0)


async def test_history_older_past(
    freezer, mock_persist_driver, dummy_utc_datetime, dummy_timestamp, num_mock_port1, dummy_eval_context
):
    freezer.move_to(dummy_utc_datetime)
    mock_persist_driver.enable_history_support()

    port_expr = MockPortRef(num_mock_port1)
    ts_expr = MockExpression(dummy_timestamp - 3600)
    diff_expr = MockExpression(-3600)

    expr = various.HistoryFunction([port_expr, ts_expr, diff_expr])

    num_mock_port1.set_last_read_value(-8)
    await history.save_sample(num_mock_port1, (dummy_timestamp - 8000) * 1000)
    num_mock_port1.set_last_read_value(-2)
    await history.save_sample(num_mock_port1, (dummy_timestamp - 2000) * 1000)
    num_mock_port1.set_last_read_value(0.01)

    with pytest.raises(PortValueUnavailable):
        await expr.eval(dummy_eval_context)

    num_mock_port1.set_last_read_value(-6)
    await history.save_sample(num_mock_port1, (dummy_timestamp - 6000) * 1000)
    assert await expr.eval(dummy_eval_context) == -6

    num_mock_port1.set_last_read_value(-4)
    await history.save_sample(num_mock_port1, (dummy_timestamp - 4000) * 1000)
    diff_expr.set_value(-3601)  # Invalidates history expression internal cache
    assert await expr.eval(dummy_eval_context) == -4


async def test_history_older_future(
    freezer, mock_persist_driver, dummy_utc_datetime, dummy_timestamp, num_mock_port1, dummy_eval_context
):
    freezer.move_to(dummy_utc_datetime)
    mock_persist_driver.enable_history_support()

    port_expr = MockPortRef(num_mock_port1)
    ts_expr = MockExpression(dummy_timestamp + 7200)
    diff_expr = MockExpression(-3600)

    expr = various.HistoryFunction([port_expr, ts_expr, diff_expr])

    num_mock_port1.set_last_read_value(-8)
    await history.save_sample(num_mock_port1, (dummy_timestamp - 8000) * 1000)

    num_mock_port1.set_last_read_value(0.01)
    assert await expr.eval(dummy_eval_context) == 0.01


async def test_history_older_current(
    freezer, mock_persist_driver, dummy_utc_datetime, dummy_timestamp, num_mock_port1, dummy_eval_context
):
    freezer.move_to(dummy_utc_datetime)
    mock_persist_driver.enable_history_support()

    port_expr = MockPortRef(num_mock_port1)
    ts_expr = MockExpression(dummy_timestamp + 1800)
    diff_expr = MockExpression(-3600)

    expr = various.HistoryFunction([port_expr, ts_expr, diff_expr])

    num_mock_port1.set_last_read_value(-2)
    await history.save_sample(num_mock_port1, (dummy_timestamp - 2000) * 1000)
    num_mock_port1.set_last_read_value(-1)
    await history.save_sample(num_mock_port1, (dummy_timestamp - 1000) * 1000)

    num_mock_port1.set_last_read_value(0.01)
    assert await expr.eval(dummy_eval_context) == 0.01


async def test_history_newer_past(
    freezer, mock_persist_driver, dummy_utc_datetime, dummy_timestamp, num_mock_port1, dummy_eval_context
):
    freezer.move_to(dummy_utc_datetime)
    mock_persist_driver.enable_history_support()

    port_expr = MockPortRef(num_mock_port1)
    ts_expr = MockExpression(dummy_timestamp - 7200)
    diff_expr = MockExpression(3600)

    expr = various.HistoryFunction([port_expr, ts_expr, diff_expr])

    num_mock_port1.set_last_read_value(-8)
    await history.save_sample(num_mock_port1, (dummy_timestamp - 8000) * 1000)
    num_mock_port1.set_last_read_value(-2)
    await history.save_sample(num_mock_port1, (dummy_timestamp - 2000) * 1000)
    num_mock_port1.set_last_read_value(0.01)

    with pytest.raises(PortValueUnavailable):
        await expr.eval(dummy_eval_context)

    num_mock_port1.set_last_read_value(-4)
    await history.save_sample(num_mock_port1, (dummy_timestamp - 4000) * 1000)
    assert await expr.eval(dummy_eval_context) == -4

    num_mock_port1.set_last_read_value(-6)
    await history.save_sample(num_mock_port1, (dummy_timestamp - 6000) * 1000)
    diff_expr.set_value(3601)  # Invalidates history expression internal cache
    assert await expr.eval(dummy_eval_context) == -6


async def test_history_newer_future(
    freezer, mock_persist_driver, dummy_utc_datetime, dummy_timestamp, num_mock_port1, dummy_eval_context
):
    freezer.move_to(dummy_utc_datetime)
    mock_persist_driver.enable_history_support()

    port_expr = MockPortRef(num_mock_port1)
    ts_expr = MockExpression(dummy_timestamp + 3600)
    diff_expr = MockExpression(3600)

    expr = various.HistoryFunction([port_expr, ts_expr, diff_expr])

    num_mock_port1.set_last_read_value(-8)
    await history.save_sample(num_mock_port1, (dummy_timestamp - 8000) * 1000)

    num_mock_port1.set_last_read_value(0.01)
    with pytest.raises(PortValueUnavailable):
        await expr.eval(dummy_eval_context)


async def test_history_newer_current(
    freezer, mock_persist_driver, dummy_utc_datetime, dummy_timestamp, num_mock_port1, dummy_eval_context
):
    freezer.move_to(dummy_utc_datetime)
    mock_persist_driver.enable_history_support()

    port_expr = MockPortRef(num_mock_port1)
    ts_expr = MockExpression(dummy_timestamp - 1800)
    diff_expr = MockExpression(3600)

    expr = various.HistoryFunction([port_expr, ts_expr, diff_expr])

    num_mock_port1.set_last_read_value(-2)
    await history.save_sample(num_mock_port1, (dummy_timestamp - 2000) * 1000)
    num_mock_port1.set_last_read_value(-1)
    await history.save_sample(num_mock_port1, (dummy_timestamp - 1000) * 1000)

    num_mock_port1.set_last_read_value(0.01)
    assert await expr.eval(dummy_eval_context) == -1


async def test_history_newer_unlimited_past(
    freezer, mock_persist_driver, dummy_utc_datetime, dummy_timestamp, num_mock_port1, dummy_eval_context
):
    freezer.move_to(dummy_utc_datetime)
    mock_persist_driver.enable_history_support()

    port_expr = MockPortRef(num_mock_port1)
    ts_expr = MockExpression(dummy_timestamp - 7200)
    diff_expr = MockExpression(0)

    expr = various.HistoryFunction([port_expr, ts_expr, diff_expr])

    num_mock_port1.set_last_read_value(-8)
    await history.save_sample(num_mock_port1, (dummy_timestamp - 8000) * 1000)

    num_mock_port1.set_last_read_value(0.01)
    assert await expr.eval(dummy_eval_context) == 0.01

    num_mock_port1.set_last_read_value(-4)
    await history.save_sample(num_mock_port1, (dummy_timestamp - 4000) * 1000)
    assert await expr.eval(dummy_eval_context) == -4

    num_mock_port1.set_last_read_value(-6)
    await history.save_sample(num_mock_port1, (dummy_timestamp - 6000) * 1000)
    diff_expr.set_value(3601)  # Invalidates history expression internal cache
    assert await expr.eval(dummy_eval_context) == -6


async def test_history_newer_unlimited_future(
    freezer, mock_persist_driver, dummy_utc_datetime, dummy_timestamp, num_mock_port1, dummy_eval_context
):
    freezer.move_to(dummy_utc_datetime)
    mock_persist_driver.enable_history_support()

    port_expr = MockPortRef(num_mock_port1)
    ts_expr = MockExpression(dummy_timestamp + 7200)
    diff_expr = MockExpression(0)

    expr = various.HistoryFunction([port_expr, ts_expr, diff_expr])

    num_mock_port1.set_last_read_value(-8)
    await history.save_sample(num_mock_port1, (dummy_timestamp - 8000) * 1000)

    num_mock_port1.set_last_read_value(0.01)
    with pytest.raises(PortValueUnavailable):
        await expr.eval(dummy_eval_context)


def test_history_parse(mock_persist_driver):
    mock_persist_driver.enable_history_support()

    e = Function.parse(None, 'HISTORY(@some_id, 1, 2)', 0)
    assert isinstance(e, various.HistoryFunction)


def test_history_arg_type(mock_persist_driver):
    mock_persist_driver.enable_history_support()

    with pytest.raises(InvalidArgumentKind) as exc_info:
        Function.parse(None, 'HISTORY(1, 2, 3)', 0)

    assert exc_info.value.name == 'HISTORY'
    assert exc_info.value.num == 1
    assert exc_info.value.pos == 9


def test_history_num_args(mock_persist_driver):
    mock_persist_driver.enable_history_support()

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'HISTORY(@some_id, 1)', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'HISTORY(@some_id, 1, 2, 3)', 0)
