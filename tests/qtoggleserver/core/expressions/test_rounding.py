
import pytest

from qtoggleserver.core.expressions import rounding, Function
from qtoggleserver.core.expressions import InvalidNumberOfArguments


async def test_floor_integer(literal_two):
    result = await rounding.FloorFunction([literal_two]).eval()
    assert result == 2


async def test_floor_positive(literal_pi, literal_ten_point_fifty_one):
    result = await rounding.FloorFunction([literal_pi]).eval()
    assert result == 3

    result = await rounding.FloorFunction([literal_ten_point_fifty_one]).eval()
    assert result == 10


async def test_floor_negative(literal_minus_pi, literal_minus_ten_point_fifty_one):
    result = await rounding.FloorFunction([literal_minus_pi]).eval()
    assert result == -4

    result = await rounding.FloorFunction([literal_minus_ten_point_fifty_one]).eval()
    assert result == -11


def test_floor_parse():
    e = Function.parse(None, 'FLOOR(1)', 0)
    assert isinstance(e, rounding.FloorFunction)


def test_floor_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'FLOOR()', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'FLOOR(1, 2)', 0)


async def test_ceil_integer(literal_two):
    result = await rounding.CeilFunction([literal_two]).eval()
    assert result == 2


async def test_ceil_positive(literal_pi, literal_ten_point_fifty_one):
    result = await rounding.CeilFunction([literal_pi]).eval()
    assert result == 4

    result = await rounding.CeilFunction([literal_ten_point_fifty_one]).eval()
    assert result == 11


async def test_ceil_negative(literal_minus_pi, literal_minus_ten_point_fifty_one):
    result = await rounding.CeilFunction([literal_minus_pi]).eval()
    assert result == -3

    result = await rounding.CeilFunction([literal_minus_ten_point_fifty_one]).eval()
    assert result == -10


def test_ceil_parse():
    e = Function.parse(None, 'CEIL(1)', 0)
    assert isinstance(e, rounding.CeilFunction)


def test_ceil_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'CEIL()', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'CEIL(1, 2)', 0)


async def test_round_integer(literal_two):
    result = await rounding.RoundFunction([literal_two]).eval()
    assert result == 2


async def test_round_positive(literal_pi, literal_ten_point_fifty_one):
    result = await rounding.RoundFunction([literal_pi]).eval()
    assert result == 3

    result = await rounding.RoundFunction([literal_ten_point_fifty_one]).eval()
    assert result == 11


async def test_round_negative(literal_minus_pi, literal_minus_ten_point_fifty_one):
    result = await rounding.RoundFunction([literal_minus_pi]).eval()
    assert result == -3

    result = await rounding.RoundFunction([literal_minus_ten_point_fifty_one]).eval()
    assert result == -11


async def test_round_decimals(literal_minus_pi, literal_two):
    result = await rounding.RoundFunction([literal_minus_pi, literal_two]).eval()
    assert result == -3.14


def test_round_parse():
    e = Function.parse(None, 'ROUND(1)', 0)
    assert isinstance(e, rounding.RoundFunction)


def test_round_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'ROUND()', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'ROUND(1, 2, 3)', 0)
