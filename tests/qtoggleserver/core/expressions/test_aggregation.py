
import pytest

from qtoggleserver.core.expressions import aggregation, Function
from qtoggleserver.core.expressions import InvalidNumberOfArguments


async def test_min_simple(literal_one, literal_two):
    result = await aggregation.MinFunction([literal_two, literal_one]).eval(context={})
    assert result == 1


async def test_min_multiple(literal_one, literal_ten, literal_minus_two):
    result = await aggregation.MinFunction([literal_ten, literal_one, literal_minus_two]).eval(context={})
    assert result == -2


def test_min_parse():
    e = Function.parse(None, 'MIN(1, 2, 3)', 0)
    assert isinstance(e, aggregation.MinFunction)


def test_min_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'MIN(1)', 0)


async def test_max_simple(literal_one, literal_two):
    result = await aggregation.MaxFunction([literal_two, literal_one]).eval(context={})
    assert result == 2


async def test_max_multiple(literal_one, literal_ten, literal_minus_two):
    result = await aggregation.MaxFunction([literal_ten, literal_one, literal_minus_two]).eval(context={})
    assert result == 10


def test_max_parse():
    e = Function.parse(None, 'MAX(1, 2, 3)', 0)
    assert isinstance(e, aggregation.MaxFunction)


def test_max_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'MAX(1)', 0)


async def test_avg_simple(literal_one, literal_two):
    result = await aggregation.AvgFunction([literal_two, literal_one]).eval(context={})
    assert result == 1.5


async def test_avg_multiple(literal_one, literal_ten, literal_minus_two):
    result = await aggregation.AvgFunction([literal_ten, literal_one, literal_minus_two]).eval(context={})
    assert result == 3


def test_avg_parse():
    e = Function.parse(None, 'AVG(1, 2, 3)', 0)
    assert isinstance(e, aggregation.AvgFunction)


def test_avg_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'AVG(1)', 0)
