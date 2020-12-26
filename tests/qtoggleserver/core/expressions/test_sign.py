
import pytest

from qtoggleserver.core.expressions import sign, Function
from qtoggleserver.core.expressions import InvalidNumberOfArguments


async def test_abs(literal_two, literal_minus_two):
    result = await sign.AbsFunction([literal_two]).eval()
    assert result == 2

    result = await sign.AbsFunction([literal_minus_two]).eval()
    assert result == 2


def test_abs_parse():
    e = Function.parse(None, 'ABS(1)', 0)
    assert isinstance(e, sign.AbsFunction)


def test_abs_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'ABS()', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'ABS(1, 2)', 0)


async def test_sgn(literal_two, literal_minus_two):
    result = await sign.SgnFunction([literal_two]).eval()
    assert result == 1

    result = await sign.SgnFunction([literal_minus_two]).eval()
    assert result == -1


def test_sgn_parse():
    e = Function.parse(None, 'SGN(1)', 0)
    assert isinstance(e, sign.SgnFunction)


def test_sgn_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'SGN()', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'SGN(1, 2)', 0)
