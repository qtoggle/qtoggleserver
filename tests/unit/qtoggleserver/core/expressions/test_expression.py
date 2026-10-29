import pytest

from qtoggleserver.core.expressions import EvalContext, Expression, Role, parse
from qtoggleserver.core.expressions.exceptions import NonFiniteValue, ValueUnavailable


class _TestableExpression(Expression):
    async def _eval(self, context: EvalContext):
        return 42

    @staticmethod
    def parse(self_port_id: str | None, sexpression: str, role: Role, pos: int) -> Expression:
        pass


class TestExpression:
    async def test_eval(self, dummy_eval_context):
        """Should call `_eval()` with supplied context. Should reset the asap eval pause flag."""

        e = _TestableExpression(role=Role.VALUE)
        e._asap_eval_paused_until_ms = 1234
        assert await e.eval(dummy_eval_context) == 42
        assert e._asap_eval_paused_until_ms == 0

    async def test_eval_exception(self, dummy_eval_context, mocker):
        """Should pause asap eval on `ExpressionEvalException` and re-raise."""

        class TempExpression(_TestableExpression):
            async def _eval(self, context: EvalContext):
                raise ValueUnavailable("unavailable")

        e = TempExpression(role=Role.VALUE)
        mocker.patch.object(e, "pause_asap_eval")
        with pytest.raises(ValueUnavailable):
            await e.eval(dummy_eval_context)
        e.pause_asap_eval.assert_called_once()

    @pytest.mark.parametrize("value", [float("inf"), float("-inf"), float("nan")])
    async def test_eval_non_finite(self, dummy_eval_context, mocker, value):
        """Should raise `NonFiniteValue`, which is a `ValueUnavailable`, for a result that is not a finite number, and
        pause asap eval."""

        class TempExpression(_TestableExpression):
            async def _eval(self, context: EvalContext):
                return value

        e = TempExpression(role=Role.VALUE)
        mocker.patch.object(e, "pause_asap_eval")
        with pytest.raises(NonFiniteValue):
            await e.eval(dummy_eval_context)
        e.pause_asap_eval.assert_called_once()
        assert issubclass(NonFiniteValue, ValueUnavailable)

    async def test_eval_non_finite_function_result(self, dummy_eval_context):
        """Should make a function result that is not a finite number unavailable, so that `DEFAULT` can shield it."""

        e = parse(None, "MUL(1e308, 10)", role=Role.VALUE)
        with pytest.raises(ValueUnavailable):
            await e.eval(dummy_eval_context)

        e = parse(None, "DEFAULT(SUB(MUL(1e308, 10), MUL(1e308, 10)), 5)", role=Role.VALUE)
        assert await e.eval(dummy_eval_context) == 5
