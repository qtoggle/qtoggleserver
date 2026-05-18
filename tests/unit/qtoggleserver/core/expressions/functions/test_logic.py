import pytest

from qtoggleserver.core.expressions import Function, Role, logic
from qtoggleserver.core.expressions.exceptions import InvalidNumberOfArguments


class TestAnd:
    async def test_simple(self, literal_false, literal_true, dummy_eval_context):
        result = await logic.AndFunction([literal_false, literal_true], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 0

        result = await logic.AndFunction([literal_false, literal_false], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 0

        result = await logic.AndFunction([literal_true, literal_true], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 1

    async def test_multiple(self, literal_false, literal_true, dummy_eval_context):
        result = await logic.AndFunction([literal_false, literal_true, literal_true], role=Role.VALUE).eval(
            dummy_eval_context
        )
        assert result == 0

        result = await logic.AndFunction([literal_true, literal_true, literal_true], role=Role.VALUE).eval(
            dummy_eval_context
        )
        assert result == 1

    async def test_unavailable(self, literal_false, literal_true, literal_unavailable, dummy_eval_context):
        result = await logic.AndFunction([literal_true, literal_false, literal_unavailable], role=Role.VALUE).eval(
            dummy_eval_context
        )
        assert result == 0

    async def test_number(self, literal_zero, literal_ten, literal_true, dummy_eval_context):
        result = await logic.AndFunction([literal_zero, literal_true], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 0

        result = await logic.AndFunction([literal_ten, literal_true], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 1

    def test_parse(self):
        e = Function.parse(None, "AND(false, true)", Role.VALUE, 0)
        assert isinstance(e, logic.AndFunction)

    def test_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "AND(false)", Role.VALUE, 0)


class TestOr:
    async def test_simple(self, literal_false, literal_true, dummy_eval_context):
        result = await logic.OrFunction([literal_false, literal_false], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 0

        result = await logic.OrFunction([literal_false, literal_true], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 1

        result = await logic.OrFunction([literal_true, literal_true], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 1

    async def test_multiple(self, literal_false, literal_true, dummy_eval_context):
        result = await logic.OrFunction([literal_false, literal_false, literal_false], role=Role.VALUE).eval(
            dummy_eval_context
        )
        assert result == 0

        result = await logic.OrFunction([literal_false, literal_true, literal_false], role=Role.VALUE).eval(
            dummy_eval_context
        )
        assert result == 1

    async def test_unavailable(self, literal_false, literal_true, literal_unavailable, dummy_eval_context):
        result = await logic.OrFunction([literal_false, literal_true, literal_unavailable], role=Role.VALUE).eval(
            dummy_eval_context
        )
        assert result == 1

    async def test_number(self, literal_zero, literal_ten, literal_true, literal_false, dummy_eval_context):
        result = await logic.OrFunction([literal_zero, literal_true], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 1

        result = await logic.OrFunction([literal_ten, literal_false], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 1

    def test_parse(self):
        e = Function.parse(None, "OR(false, true)", Role.VALUE, 0)
        assert isinstance(e, logic.OrFunction)

    def test_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "OR(false)", Role.VALUE, 0)


class TestNot:
    async def test_simple(self, literal_false, literal_true, dummy_eval_context):
        result = await logic.NotFunction([literal_false], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 1

        result = await logic.NotFunction([literal_true], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 0

    async def test_number(self, literal_zero, literal_ten, dummy_eval_context):
        result = await logic.NotFunction([literal_zero], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 1

        result = await logic.NotFunction([literal_ten], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 0

    def test_parse(self):
        e = Function.parse(None, "NOT(false)", Role.VALUE, 0)
        assert isinstance(e, logic.NotFunction)

    def test_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "NOT()", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "NOT(false, true)", Role.VALUE, 0)


class TestXOr:
    async def test_simple(self, literal_false, literal_true, dummy_eval_context):
        result = await logic.XOrFunction([literal_false, literal_false], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 0

        result = await logic.XOrFunction([literal_false, literal_true], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 1

        result = await logic.XOrFunction([literal_true, literal_true], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 0

    async def test_number(self, literal_zero, literal_ten, literal_true, literal_false, dummy_eval_context):
        result = await logic.XOrFunction([literal_zero, literal_true], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 1

        result = await logic.XOrFunction([literal_ten, literal_false], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 1

        result = await logic.XOrFunction([literal_ten, literal_true], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 0

    def test_parse(self):
        e = Function.parse(None, "XOR(false, true)", Role.VALUE, 0)
        assert isinstance(e, logic.XOrFunction)

    def test_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "XOR(false)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "XOR(false, true, false)", Role.VALUE, 0)
