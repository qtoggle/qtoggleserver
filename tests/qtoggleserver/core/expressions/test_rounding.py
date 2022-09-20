import pytest

from qtoggleserver.core.expressions import ROLE_VALUE, Function, InvalidNumberOfArguments, rounding


async def test_floor_integer(literal_two, dummy_eval_context):
    result = await rounding.FloorFunction([literal_two], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 2


async def test_floor_positive(literal_pi, literal_ten_point_fifty_one, dummy_eval_context):
    result = await rounding.FloorFunction([literal_pi], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 3

    result = await rounding.FloorFunction([literal_ten_point_fifty_one], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 10


async def test_floor_negative(literal_minus_pi, literal_minus_ten_point_fifty_one, dummy_eval_context):
    result = await rounding.FloorFunction([literal_minus_pi], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == -4

    result = await rounding.FloorFunction([literal_minus_ten_point_fifty_one], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == -11


def test_floor_parse():
    e = Function.parse(None, 'FLOOR(1)', ROLE_VALUE, 0)
    assert isinstance(e, rounding.FloorFunction)


def test_floor_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'FLOOR()', ROLE_VALUE, 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'FLOOR(1, 2)', ROLE_VALUE, 0)


async def test_ceil_integer(literal_two, dummy_eval_context):
    result = await rounding.CeilFunction([literal_two], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 2


async def test_ceil_positive(literal_pi, literal_ten_point_fifty_one, dummy_eval_context):
    result = await rounding.CeilFunction([literal_pi], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 4

    result = await rounding.CeilFunction([literal_ten_point_fifty_one], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 11


async def test_ceil_negative(literal_minus_pi, literal_minus_ten_point_fifty_one, dummy_eval_context):
    result = await rounding.CeilFunction([literal_minus_pi], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == -3

    result = await rounding.CeilFunction([literal_minus_ten_point_fifty_one], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == -10


def test_ceil_parse():
    e = Function.parse(None, 'CEIL(1)', ROLE_VALUE, 0)
    assert isinstance(e, rounding.CeilFunction)


def test_ceil_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'CEIL()', ROLE_VALUE, 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'CEIL(1, 2)', ROLE_VALUE, 0)


async def test_round_integer(literal_two, dummy_eval_context):
    result = await rounding.RoundFunction([literal_two], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 2


async def test_round_positive(literal_pi, literal_ten_point_fifty_one, dummy_eval_context):
    result = await rounding.RoundFunction([literal_pi], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 3

    result = await rounding.RoundFunction([literal_ten_point_fifty_one], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 11


async def test_round_negative(literal_minus_pi, literal_minus_ten_point_fifty_one, dummy_eval_context):
    result = await rounding.RoundFunction([literal_minus_pi], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == -3

    result = await rounding.RoundFunction([literal_minus_ten_point_fifty_one], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == -11


async def test_round_decimals(literal_minus_pi, literal_two, dummy_eval_context):
    result = await rounding.RoundFunction([literal_minus_pi, literal_two], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == -3.14


def test_round_parse():
    e = Function.parse(None, 'ROUND(1)', ROLE_VALUE, 0)
    assert isinstance(e, rounding.RoundFunction)


def test_round_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'ROUND()', ROLE_VALUE, 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'ROUND(1, 2, 3)', ROLE_VALUE, 0)
