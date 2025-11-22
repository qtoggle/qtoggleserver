import pytest

from qtoggleserver.core.expressions import Function, Role, time
from qtoggleserver.core.expressions.exceptions import InvalidNumberOfArguments


async def test_time(dummy_utc_datetime, dummy_timestamp, dummy_eval_context):
    result = await time.TimeFunction([], role=Role.VALUE).eval(dummy_eval_context)
    assert result == int(dummy_timestamp)


def test_time_parse():
    e = Function.parse(None, "TIME()", Role.VALUE, 0)
    assert isinstance(e, time.TimeFunction)


def test_time_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, "TIME(1)", Role.VALUE, 0)


async def test_timems(dummy_utc_datetime, dummy_timestamp, dummy_eval_context):
    result = await time.TimeMSFunction([], role=Role.VALUE).eval(dummy_eval_context)
    assert result == int(dummy_timestamp * 1000)


def test_timems_parse():
    e = Function.parse(None, "TIMEMS()", Role.VALUE, 0)
    assert isinstance(e, time.TimeMSFunction)


def test_timems_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, "TIMEMS(1)", Role.VALUE, 0)
