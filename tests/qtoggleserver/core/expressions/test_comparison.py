import pytest

from qtoggleserver.core.expressions import Function, Role, comparison
from qtoggleserver.core.expressions.exceptions import InvalidNumberOfArguments


class TestIf:
    async def test_if_boolean(self, literal_false, literal_true, literal_one, literal_two, dummy_eval_context):
        result = await comparison.IfFunction([literal_false, literal_one, literal_two], role=Role.VALUE).eval(
            dummy_eval_context
        )
        assert result == 2

        result = await comparison.IfFunction([literal_true, literal_one, literal_two], role=Role.VALUE).eval(
            dummy_eval_context
        )
        assert result == 1

    async def test_if_number(self, literal_zero, literal_one, literal_two, dummy_eval_context):
        result = await comparison.IfFunction([literal_zero, literal_one, literal_two], role=Role.VALUE).eval(
            dummy_eval_context
        )
        assert result == 2

        result = await comparison.IfFunction([literal_two, literal_one, literal_two], role=Role.VALUE).eval(
            dummy_eval_context
        )
        assert result == 1

    async def test_if_unavailable(
        self, literal_false, literal_true, literal_ten, literal_unavailable, dummy_eval_context
    ):
        result = await comparison.IfFunction([literal_false, literal_unavailable, literal_ten], role=Role.VALUE).eval(
            dummy_eval_context
        )
        assert result == 10

        result = await comparison.IfFunction([literal_true, literal_ten, literal_unavailable], role=Role.VALUE).eval(
            dummy_eval_context
        )
        assert result == 10

    def test_if_parse(self):
        e = Function.parse(None, "IF(1, 2, 3)", Role.VALUE, 0)
        assert isinstance(e, comparison.IfFunction)

    def test_if_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "IF(1, 2)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "IF(1, 2, 3, 4)", Role.VALUE, 0)


class TestEq:
    async def test_eq_boolean(self, literal_false, literal_true, dummy_eval_context):
        result = await comparison.EqFunction([literal_false, literal_true], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 0

        result = await comparison.EqFunction([literal_false, literal_false], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 1

    async def test_eq_number(self, literal_one, literal_two, dummy_eval_context):
        result = await comparison.EqFunction([literal_one, literal_two], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 0

        result = await comparison.EqFunction([literal_two, literal_two], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 1

    def test_eq_parse(self):
        e = Function.parse(None, "EQ(1, 2)", Role.VALUE, 0)
        assert isinstance(e, comparison.EqFunction)

    def test_eq_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "EQ(1)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "EQ(1, 2, 3)", Role.VALUE, 0)


class TestGT:
    async def test_gt_boolean(self, literal_false, literal_true, dummy_eval_context):
        result = await comparison.GTFunction([literal_true, literal_false], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 1

        result = await comparison.GTFunction([literal_false, literal_false], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 0

    async def test_gt_number(self, literal_one, literal_two, dummy_eval_context):
        result = await comparison.GTFunction([literal_two, literal_one], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 1

        result = await comparison.GTFunction([literal_one, literal_two], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 0

        result = await comparison.GTFunction([literal_two, literal_two], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 0

    def test_gt_parse(self):
        e = Function.parse(None, "GT(1, 2)", Role.VALUE, 0)
        assert isinstance(e, comparison.GTFunction)

    def test_gt_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "GT(1)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "GT(1, 2, 3)", Role.VALUE, 0)


class TestGTE:
    async def test_gte_boolean(self, literal_false, literal_true, dummy_eval_context):
        result = await comparison.GTEFunction([literal_true, literal_false], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 1

        result = await comparison.GTEFunction([literal_false, literal_false], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 1

        result = await comparison.GTEFunction([literal_false, literal_true], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 0

    async def test_gte_number(self, literal_one, literal_two, dummy_eval_context):
        result = await comparison.GTEFunction([literal_two, literal_one], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 1

        result = await comparison.GTEFunction([literal_one, literal_two], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 0

        result = await comparison.GTEFunction([literal_two, literal_two], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 1

    def test_gte_parse(self):
        e = Function.parse(None, "GTE(1, 2)", Role.VALUE, 0)
        assert isinstance(e, comparison.GTEFunction)

    def test_gte_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "GTE(1)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "GTE(1, 2, 3)", Role.VALUE, 0)


class TestLT:
    async def test_lt_boolean(self, literal_false, literal_true, dummy_eval_context):
        result = await comparison.LTFunction([literal_false, literal_true], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 1

        result = await comparison.LTFunction([literal_false, literal_false], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 0

    async def test_lt_number(self, literal_one, literal_two, dummy_eval_context):
        result = await comparison.LTFunction([literal_one, literal_two], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 1

        result = await comparison.LTFunction([literal_two, literal_one], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 0

        result = await comparison.LTFunction([literal_two, literal_two], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 0

    def test_lt_parse(self):
        e = Function.parse(None, "LT(1, 2)", Role.VALUE, 0)
        assert isinstance(e, comparison.LTFunction)

    def test_lt_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "LT(1)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "LT(1, 2, 3)", Role.VALUE, 0)


class TestLTE:
    async def test_lte_boolean(self, literal_false, literal_true, dummy_eval_context):
        result = await comparison.LTEFunction([literal_false, literal_true], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 1

        result = await comparison.LTEFunction([literal_false, literal_false], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 1

        result = await comparison.LTEFunction([literal_true, literal_false], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 0

    async def test_lte_number(self, literal_one, literal_two, dummy_eval_context):
        result = await comparison.LTEFunction([literal_one, literal_two], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 1

        result = await comparison.LTEFunction([literal_two, literal_one], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 0

        result = await comparison.LTEFunction([literal_two, literal_two], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 1

    def test_lte_parse(self):
        e = Function.parse(None, "LTE(1, 2)", Role.VALUE, 0)
        assert isinstance(e, comparison.LTEFunction)

    def test_lte_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "LTE(1)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "LTE(1, 2, 3)", Role.VALUE, 0)
