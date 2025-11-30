import pytest

from qtoggleserver.core.expressions import Function, Role, rounding
from qtoggleserver.core.expressions.exceptions import InvalidNumberOfArguments


class TestFloor:
    async def test_integer(self, literal_two, dummy_eval_context):
        result = await rounding.FloorFunction([literal_two], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 2

    async def test_positive(self, literal_pi, literal_ten_point_fifty_one, dummy_eval_context):
        result = await rounding.FloorFunction([literal_pi], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 3

        result = await rounding.FloorFunction([literal_ten_point_fifty_one], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 10

    async def test_negative(self, literal_minus_pi, literal_minus_ten_point_fifty_one, dummy_eval_context):
        result = await rounding.FloorFunction([literal_minus_pi], role=Role.VALUE).eval(dummy_eval_context)
        assert result == -4

        result = await rounding.FloorFunction([literal_minus_ten_point_fifty_one], role=Role.VALUE).eval(
            dummy_eval_context
        )
        assert result == -11

    def test_parse(self):
        e = Function.parse(None, "FLOOR(1)", Role.VALUE, 0)
        assert isinstance(e, rounding.FloorFunction)

    def test_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "FLOOR()", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "FLOOR(1, 2)", Role.VALUE, 0)


class TestCeil:
    async def test_integer(self, literal_two, dummy_eval_context):
        result = await rounding.CeilFunction([literal_two], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 2

    async def test_positive(self, literal_pi, literal_ten_point_fifty_one, dummy_eval_context):
        result = await rounding.CeilFunction([literal_pi], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 4

        result = await rounding.CeilFunction([literal_ten_point_fifty_one], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 11

    async def test_negative(self, literal_minus_pi, literal_minus_ten_point_fifty_one, dummy_eval_context):
        result = await rounding.CeilFunction([literal_minus_pi], role=Role.VALUE).eval(dummy_eval_context)
        assert result == -3

        result = await rounding.CeilFunction([literal_minus_ten_point_fifty_one], role=Role.VALUE).eval(
            dummy_eval_context
        )
        assert result == -10

    def test_parse(self):
        e = Function.parse(None, "CEIL(1)", Role.VALUE, 0)
        assert isinstance(e, rounding.CeilFunction)

    def test_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "CEIL()", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "CEIL(1, 2)", Role.VALUE, 0)


class TestRound:
    async def test_integer(self, literal_two, dummy_eval_context):
        result = await rounding.RoundFunction([literal_two], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 2

    async def test_positive(self, literal_pi, literal_ten_point_fifty_one, dummy_eval_context):
        result = await rounding.RoundFunction([literal_pi], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 3

        result = await rounding.RoundFunction([literal_ten_point_fifty_one], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 11

    async def test_negative(self, literal_minus_pi, literal_minus_ten_point_fifty_one, dummy_eval_context):
        result = await rounding.RoundFunction([literal_minus_pi], role=Role.VALUE).eval(dummy_eval_context)
        assert result == -3

        result = await rounding.RoundFunction([literal_minus_ten_point_fifty_one], role=Role.VALUE).eval(
            dummy_eval_context
        )
        assert result == -11

    async def test_decimals(self, literal_minus_pi, literal_two, dummy_eval_context):
        result = await rounding.RoundFunction([literal_minus_pi, literal_two], role=Role.VALUE).eval(dummy_eval_context)
        assert result == -3.14

    def test_parse(self):
        e = Function.parse(None, "ROUND(1)", Role.VALUE, 0)
        assert isinstance(e, rounding.RoundFunction)

    def test_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "ROUND()", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "ROUND(1, 2, 3)", Role.VALUE, 0)
