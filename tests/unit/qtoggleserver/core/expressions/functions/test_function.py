import asyncio

import pytest

from qtoggleserver.core.expressions import DEP_ASAP, EvalContext, EvalResult, Role
from qtoggleserver.core.expressions.exceptions import ValueUnavailable
from tests.unit.qtoggleserver.mock.expressions import MockExpression, MockFunction


class SlowExpression(MockExpression):
    async def _eval(self, context: EvalContext) -> EvalResult:
        for _ in range(3):
            await asyncio.sleep(0)

        return await super()._eval(context)


class FailingExpression(MockExpression):
    def __init__(self, msg: str) -> None:
        super().__init__()

        self.msg: str = msg

    async def _eval(self, context: EvalContext) -> EvalResult:
        raise ValueUnavailable(self.msg)


class SlowFailingExpression(FailingExpression):
    async def _eval(self, context: EvalContext) -> EvalResult:
        for _ in range(3):
            await asyncio.sleep(0)

        return await super()._eval(context)


class TestFunction:
    def test_is_asap_eval_paused(self):
        f11 = MockFunction(args=[], role=Role.VALUE)
        f12 = MockFunction(args=[], role=Role.VALUE)
        f13 = MockFunction(args=[], role=Role.VALUE)
        f1 = MockFunction(args=[f11, f12, f13], role=Role.VALUE)
        f2 = MockFunction(args=[], role=Role.VALUE)
        e = MockExpression()
        f = MockFunction(args=[f1, f2, e], role=Role.VALUE)

        for func in [f, f11, f12, f1, f2, e]:
            func.DEPS = {DEP_ASAP}

        f11.pause_asap_eval(1000)
        f12.pause_asap_eval(2000)
        f13.pause_asap_eval(500)  # should be ignored because doesn't depend on ASAP
        f1.pause_asap_eval(3000)
        f2.pause_asap_eval(4000)
        f.pause_asap_eval(5000)
        e.pause_asap_eval(400)  # should be ignored because it's not a function

        assert f.is_asap_eval_paused(999)
        assert not f.is_asap_eval_paused(1000)

    async def test_eval_args_waits_for_all(self, dummy_eval_context):
        """Should evaluate all args completely before raising an arg's error."""

        slow = SlowExpression(1)
        f = MockFunction(args=[MockExpression(None), slow], role=Role.VALUE)
        with pytest.raises(ValueUnavailable):
            await f.eval_args(dummy_eval_context)
        assert slow.eval_count == 1

    async def test_eval_args_raises_first_error(self, dummy_eval_context):
        """Should raise the error of the first failing arg in arg order, even when a later one fails sooner."""

        f = MockFunction(args=[SlowFailingExpression("first"), FailingExpression("second")], role=Role.VALUE)
        with pytest.raises(ValueUnavailable, match="first"):
            await f.eval_args(dummy_eval_context)
