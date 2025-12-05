import pytest

from qtoggleserver.core.expressions import Function, Role, comparison
from qtoggleserver.core.expressions.exceptions import InvalidNumberOfArguments


class TestGT:
    async def test_boolean(self, literal_false, literal_true, dummy_eval_context):
        result = await comparison.GTFunction([literal_true, literal_false], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 1

        result = await comparison.GTFunction([literal_false, literal_false], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 0

    async def test_number(self, literal_one, literal_two, dummy_eval_context):
        result = await comparison.GTFunction([literal_two, literal_one], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 1

        result = await comparison.GTFunction([literal_one, literal_two], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 0

        result = await comparison.GTFunction([literal_two, literal_two], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 0

    def test_parse(self):
        e = Function.parse(None, "GT(1, 2)", Role.VALUE, 0)
        assert isinstance(e, comparison.GTFunction)

    def test_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "GT(1)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "GT(1, 2, 3)", Role.VALUE, 0)


class TestGTE:
    async def test_boolean(self, literal_false, literal_true, dummy_eval_context):
        result = await comparison.GTEFunction([literal_true, literal_false], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 1

        result = await comparison.GTEFunction([literal_false, literal_false], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 1

        result = await comparison.GTEFunction([literal_false, literal_true], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 0

    async def test_number(self, literal_one, literal_two, dummy_eval_context):
        result = await comparison.GTEFunction([literal_two, literal_one], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 1

        result = await comparison.GTEFunction([literal_one, literal_two], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 0

        result = await comparison.GTEFunction([literal_two, literal_two], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 1

    def test_parse(self):
        e = Function.parse(None, "GTE(1, 2)", Role.VALUE, 0)
        assert isinstance(e, comparison.GTEFunction)

    def test_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "GTE(1)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "GTE(1, 2, 3)", Role.VALUE, 0)


class TestLT:
    async def test_boolean(self, literal_false, literal_true, dummy_eval_context):
        result = await comparison.LTFunction([literal_false, literal_true], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 1

        result = await comparison.LTFunction([literal_false, literal_false], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 0

    async def test_number(self, literal_one, literal_two, dummy_eval_context):
        result = await comparison.LTFunction([literal_one, literal_two], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 1

        result = await comparison.LTFunction([literal_two, literal_one], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 0

        result = await comparison.LTFunction([literal_two, literal_two], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 0

    def test_parse(self):
        e = Function.parse(None, "LT(1, 2)", Role.VALUE, 0)
        assert isinstance(e, comparison.LTFunction)

    def test_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "LT(1)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "LT(1, 2, 3)", Role.VALUE, 0)


class TestLTE:
    async def test_boolean(self, literal_false, literal_true, dummy_eval_context):
        result = await comparison.LTEFunction([literal_false, literal_true], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 1

        result = await comparison.LTEFunction([literal_false, literal_false], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 1

        result = await comparison.LTEFunction([literal_true, literal_false], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 0

    async def test_number(self, literal_one, literal_two, dummy_eval_context):
        result = await comparison.LTEFunction([literal_one, literal_two], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 1

        result = await comparison.LTEFunction([literal_two, literal_one], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 0

        result = await comparison.LTEFunction([literal_two, literal_two], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 1

    def test_parse(self):
        e = Function.parse(None, "LTE(1, 2)", Role.VALUE, 0)
        assert isinstance(e, comparison.LTEFunction)

    def test_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "LTE(1)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "LTE(1, 2, 3)", Role.VALUE, 0)
