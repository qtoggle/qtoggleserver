import pytest

from qtoggleserver.core.expressions import Function, Role, aggregation
from qtoggleserver.core.expressions.exceptions import InvalidNumberOfArguments


class TestMin:
    async def test_min_simple(self, literal_one, literal_two, dummy_eval_context):
        result = await aggregation.MinFunction([literal_two, literal_one], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 1

    async def test_min_multiple(self, literal_one, literal_ten, literal_minus_two, dummy_eval_context):
        result = await aggregation.MinFunction([literal_ten, literal_one, literal_minus_two], role=Role.VALUE).eval(
            dummy_eval_context
        )
        assert result == -2

    def test_min_parse(self):
        e = Function.parse(None, "MIN(1, 2, 3)", Role.VALUE, 0)
        assert isinstance(e, aggregation.MinFunction)

    def test_min_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "MIN(1)", Role.VALUE, 0)


class TestMax:
    async def test_max_simple(self, literal_one, literal_two, dummy_eval_context):
        result = await aggregation.MaxFunction([literal_two, literal_one], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 2

    async def test_max_multiple(self, literal_one, literal_ten, literal_minus_two, dummy_eval_context):
        result = await aggregation.MaxFunction([literal_ten, literal_one, literal_minus_two], role=Role.VALUE).eval(
            dummy_eval_context
        )
        assert result == 10

    def test_max_parse(self):
        e = Function.parse(None, "MAX(1, 2, 3)", Role.VALUE, 0)
        assert isinstance(e, aggregation.MaxFunction)

    def test_max_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "MAX(1)", Role.VALUE, 0)


class TestAvg:
    async def test_avg_simple(self, literal_one, literal_two, dummy_eval_context):
        result = await aggregation.AvgFunction([literal_two, literal_one], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 1.5

    async def test_avg_multiple(self, literal_one, literal_ten, literal_minus_two, dummy_eval_context):
        result = await aggregation.AvgFunction([literal_ten, literal_one, literal_minus_two], role=Role.VALUE).eval(
            dummy_eval_context
        )
        assert result == 3

    def test_avg_parse(self):
        e = Function.parse(None, "AVG(1, 2, 3)", Role.VALUE, 0)
        assert isinstance(e, aggregation.AvgFunction)

    def test_avg_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "AVG(1)", Role.VALUE, 0)
