import pytest

from qtoggleserver.core.expressions import Function, Role, branching
from qtoggleserver.core.expressions.exceptions import InvalidNumberOfArguments
from tests.unit.qtoggleserver.mock.expressions import MockExpression


class TestIf:
    async def test_boolean(self, literal_false, literal_true, literal_one, literal_two, dummy_eval_context):
        result = await branching.IfFunction([literal_false, literal_one, literal_two], role=Role.VALUE).eval(
            dummy_eval_context
        )
        assert result == 2

        result = await branching.IfFunction([literal_true, literal_one, literal_two], role=Role.VALUE).eval(
            dummy_eval_context
        )
        assert result == 1

    async def test_number(self, literal_zero, literal_one, literal_two, dummy_eval_context):
        result = await branching.IfFunction([literal_zero, literal_one, literal_two], role=Role.VALUE).eval(
            dummy_eval_context
        )
        assert result == 2

        result = await branching.IfFunction([literal_two, literal_one, literal_two], role=Role.VALUE).eval(
            dummy_eval_context
        )
        assert result == 1

    async def test_unavailable(self, literal_false, literal_true, literal_ten, literal_unavailable, dummy_eval_context):
        result = await branching.IfFunction([literal_false, literal_unavailable, literal_ten], role=Role.VALUE).eval(
            dummy_eval_context
        )
        assert result == 10

        result = await branching.IfFunction([literal_true, literal_ten, literal_unavailable], role=Role.VALUE).eval(
            dummy_eval_context
        )
        assert result == 10

    def test_parse(self):
        e = Function.parse(None, "IF(1, 2, 3)", Role.VALUE, 0)
        assert isinstance(e, branching.IfFunction)

    def test_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "IF(1, 2)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "IF(1, 2, 3, 4)", Role.VALUE, 0)


class TestLUT:
    async def test(
        self,
        literal_two,
        literal_three,
        literal_sixteen,
        literal_one_hundred,
        literal_two_hundreds,
        literal_one_thousand,
        dummy_eval_context,
    ):
        value_expr = MockExpression(0)
        expr = branching.LUTFunction(
            [
                value_expr,
                literal_three,
                literal_two_hundreds,
                literal_sixteen,
                literal_one_thousand,
                literal_two,
                literal_one_hundred,
            ],
            Role.VALUE,
        )
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

    def test_parse(self):
        e = Function.parse(None, "LUT(1, 2, 3, 4, 5)", Role.VALUE, 0)
        assert isinstance(e, branching.LUTFunction)

    def test_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "LUT(1)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "LUT(1, 2)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "LUT(1, 2, 3, 4)", Role.VALUE, 0)


class TestLUTLI:
    async def test(
        self,
        literal_two,
        literal_three,
        literal_sixteen,
        literal_one_hundred,
        literal_two_hundreds,
        literal_one_thousand,
        dummy_eval_context,
    ):
        value_expr = MockExpression(0)
        expr = branching.LUTLIFunction(
            [
                value_expr,
                literal_three,
                literal_two_hundreds,
                literal_sixteen,
                literal_one_thousand,
                literal_two,
                literal_one_hundred,
            ],
            Role.VALUE,
        )
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

    def test_parse(self):
        e = Function.parse(None, "LUTLI(1, 2, 3, 4, 5)", Role.VALUE, 0)
        assert isinstance(e, branching.LUTLIFunction)

    def test_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "LUTLI(1)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "LUTLI(1, 2)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "LUTLI(1, 2, 3, 4)", Role.VALUE, 0)
