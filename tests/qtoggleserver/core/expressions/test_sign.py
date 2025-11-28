import pytest

from qtoggleserver.core.expressions import Function, Role, sign
from qtoggleserver.core.expressions.exceptions import InvalidNumberOfArguments


class TestAbs:
    async def test_abs(self, literal_two, literal_minus_two, dummy_eval_context):
        result = await sign.AbsFunction([literal_two], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 2

        result = await sign.AbsFunction([literal_minus_two], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 2

    def test_abs_parse(self):
        e = Function.parse(None, "ABS(1)", Role.VALUE, 0)
        assert isinstance(e, sign.AbsFunction)

    def test_abs_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "ABS()", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "ABS(1, 2)", Role.VALUE, 0)


class TestSgn:
    async def test_sgn(self, literal_two, literal_minus_two, dummy_eval_context):
        result = await sign.SgnFunction([literal_two], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 1

        result = await sign.SgnFunction([literal_minus_two], role=Role.VALUE).eval(dummy_eval_context)
        assert result == -1

    def test_sgn_parse(self):
        e = Function.parse(None, "SGN(1)", Role.VALUE, 0)
        assert isinstance(e, sign.SgnFunction)

    def test_sgn_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "SGN()", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "SGN(1, 2)", Role.VALUE, 0)
