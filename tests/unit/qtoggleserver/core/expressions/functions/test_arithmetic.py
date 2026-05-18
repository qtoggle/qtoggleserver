import pytest

from qtoggleserver.core.expressions import Function, Role, arithmetic
from qtoggleserver.core.expressions.exceptions import ExpressionArithmeticError, InvalidNumberOfArguments


class TestAdd:
    async def test_simple(self, literal_one, literal_two, dummy_eval_context):
        result = await arithmetic.AddFunction([literal_one, literal_two], role=Role.VALUE).eval(
            context=dummy_eval_context
        )
        assert result == 3

    async def test_multiple(self, literal_one, literal_two, literal_minus_one, literal_ten, dummy_eval_context):
        expr = arithmetic.AddFunction([literal_one, literal_two, literal_minus_one, literal_ten], role=Role.VALUE)
        result = await expr.eval(context=dummy_eval_context)
        assert result == 12

    async def test_boolean(self, literal_one, literal_true, dummy_eval_context):
        result = await arithmetic.AddFunction([literal_one, literal_true], role=Role.VALUE).eval(
            context=dummy_eval_context
        )
        assert result == 2

    def test_parse(self):
        e = Function.parse(None, "ADD(1, 2)", Role.VALUE, 0)
        assert isinstance(e, arithmetic.AddFunction)

    def test_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "ADD(1)", Role.VALUE, 0)


class TestSub:
    async def test_simple(self, literal_one, literal_two, dummy_eval_context):
        result = await arithmetic.SubFunction([literal_one, literal_two], role=Role.VALUE).eval(
            context=dummy_eval_context
        )
        assert result == -1

    async def test_boolean(self, literal_two, literal_true, dummy_eval_context):
        result = await arithmetic.SubFunction([literal_two, literal_true], role=Role.VALUE).eval(
            context=dummy_eval_context
        )
        assert result == 1

    def test_parse(self):
        e = Function.parse(None, "SUB(1, 2)", Role.VALUE, 0)
        assert isinstance(e, arithmetic.SubFunction)

    def test_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "SUB(1)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "SUB(1, 2, 3)", Role.VALUE, 0)


class TestMul:
    async def test_simple(self, literal_two, literal_ten, dummy_eval_context):
        result = await arithmetic.MulFunction([literal_two, literal_ten], role=Role.VALUE).eval(
            context=dummy_eval_context
        )
        assert result == 20

    async def test_multiple(self, literal_two, literal_ten, literal_minus_one, dummy_eval_context):
        expr = arithmetic.MulFunction([literal_two, literal_ten, literal_minus_one], role=Role.VALUE)
        result = await expr.eval(context=dummy_eval_context)
        assert result == -20

    async def test_boolean(self, literal_two, literal_true, dummy_eval_context):
        result = await arithmetic.MulFunction([literal_two, literal_true], role=Role.VALUE).eval(
            context=dummy_eval_context
        )
        assert result == 2

    def test_parse(self):
        e = Function.parse(None, "MUL(1, 2)", Role.VALUE, 0)
        assert isinstance(e, arithmetic.MulFunction)

    def test_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "MUL(1)", Role.VALUE, 0)


class TestDiv:
    async def test_integer(self, literal_ten, literal_two, dummy_eval_context):
        result = await arithmetic.DivFunction([literal_ten, literal_two], role=Role.VALUE).eval(
            context=dummy_eval_context
        )
        assert result == 5

    async def test_float(self, literal_two, literal_ten, dummy_eval_context):
        result = await arithmetic.DivFunction([literal_two, literal_ten], role=Role.VALUE).eval(
            context=dummy_eval_context
        )
        assert result == 0.2

    async def test_boolean(self, literal_ten, literal_true, literal_false, dummy_eval_context):
        result = await arithmetic.DivFunction([literal_ten, literal_true], role=Role.VALUE).eval(
            context=dummy_eval_context
        )
        assert result == 10

        with pytest.raises(ExpressionArithmeticError):
            await arithmetic.DivFunction([literal_ten, literal_false], role=Role.VALUE).eval(context=dummy_eval_context)

    def test_parse(self):
        e = Function.parse(None, "DIV(1, 2)", Role.VALUE, 0)
        assert isinstance(e, arithmetic.DivFunction)

    def test_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "DIV(1)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "DIV(1, 2, 3)", Role.VALUE, 0)


class TestMod:
    async def test_integer(self, literal_ten, literal_two, dummy_eval_context):
        result = await arithmetic.ModFunction([literal_ten, literal_two], role=Role.VALUE).eval(
            context=dummy_eval_context
        )
        assert result == 0

    async def test_float(self, literal_three, literal_two, dummy_eval_context):
        result = await arithmetic.ModFunction([literal_three, literal_two], role=Role.VALUE).eval(
            context=dummy_eval_context
        )
        assert result == 1

    async def test_boolean(self, literal_ten, literal_true, literal_false, dummy_eval_context):
        result = await arithmetic.ModFunction([literal_ten, literal_true], role=Role.VALUE).eval(
            context=dummy_eval_context
        )
        assert result == 0

        with pytest.raises(ExpressionArithmeticError):
            await arithmetic.ModFunction([literal_ten, literal_false], role=Role.VALUE).eval(context=dummy_eval_context)

    def test_parse(self):
        e = Function.parse(None, "MOD(1, 2)", Role.VALUE, 0)
        assert isinstance(e, arithmetic.ModFunction)

    def test_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "MOD(1)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "MOD(1, 2, 3)", Role.VALUE, 0)


class TestPow:
    async def test_integer(self, literal_ten, literal_two, dummy_eval_context):
        result = await arithmetic.PowFunction([literal_ten, literal_two], role=Role.VALUE).eval(
            context=dummy_eval_context
        )
        assert result == 100

    async def test_sqrt(self, literal_sixteen, literal_zero_point_five, dummy_eval_context):
        result = await arithmetic.PowFunction([literal_sixteen, literal_zero_point_five], role=Role.VALUE).eval(
            context=dummy_eval_context
        )
        assert result == 4

    async def test_boolean(self, literal_ten, literal_true, literal_false, dummy_eval_context):
        result = await arithmetic.PowFunction([literal_ten, literal_true], role=Role.VALUE).eval(
            context=dummy_eval_context
        )
        assert result == 10

        result = await arithmetic.PowFunction([literal_ten, literal_false], role=Role.VALUE).eval(
            context=dummy_eval_context
        )
        assert result == 1

    def test_parse(self):
        e = Function.parse(None, "POW(1, 2)", Role.VALUE, 0)
        assert isinstance(e, arithmetic.PowFunction)

    def test_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "POW(1)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "POW(1, 2, 3)", Role.VALUE, 0)
