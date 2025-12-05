import pytest

from qtoggleserver.core.expressions import EvalContext, Expression, Role
from qtoggleserver.core.expressions.exceptions import ValueUnavailable


class TestableExpression(Expression):
    async def _eval(self, context: EvalContext):
        return 42

    @staticmethod
    def parse(self_port_id: str | None, sexpression: str, role: Role, pos: int) -> Expression:
        pass


class TestExpression:
    async def test_eval(self, dummy_eval_context):
        """Should call `_eval()` with supplied context. Should reset the asap eval pause flag."""

        e = TestableExpression(role=Role.VALUE)
        e._asap_eval_paused_until_ms = 1234
        assert await e.eval(dummy_eval_context) == 42
        assert e._asap_eval_paused_until_ms == 0

    async def test_eval_exception(self, dummy_eval_context, mocker):
        """Should pause asap eval on `ExpressionEvalException` and re-raise."""

        class TempExpression(TestableExpression):
            async def _eval(self, context: EvalContext):
                raise ValueUnavailable("unavailable")

        e = TempExpression(role=Role.VALUE)
        mocker.patch.object(e, "pause_asap_eval")
        with pytest.raises(ValueUnavailable):
            await e.eval(dummy_eval_context)
        e.pause_asap_eval.assert_called_once()
