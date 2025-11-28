import pytest

from qtoggleserver.core.expressions import Function, Role, timeprocessing
from qtoggleserver.core.expressions.exceptions import EvalSkipped, InvalidNumberOfArguments, UnknownFunction
from tests.qtoggleserver.mock.expressions import MockExpression


class TestDelay:
    async def test_delay(self, literal_one_thousand, dummy_eval_context, later_eval_context):
        value_expr = MockExpression(3)
        expr = timeprocessing.DelayFunction([value_expr, literal_one_thousand], Role.VALUE)
        assert await expr.eval(dummy_eval_context) == 3
        assert await expr.eval(later_eval_context(100)) == 3

        value_expr.set_value(16)
        assert await expr.eval(later_eval_context(500)) == 3
        assert await expr.eval(later_eval_context(1499)) == 3
        assert await expr.eval(later_eval_context(1501)) == 16
        assert await expr.eval(later_eval_context(10000)) == 16

    def test_delay_parse(self):
        e = Function.parse(None, "DELAY(1, 2)", Role.VALUE, 0)
        assert isinstance(e, timeprocessing.DelayFunction)

    def test_delay_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "DELAY(1)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "DELAY(1, 2, 3)", Role.VALUE, 0)

    @pytest.mark.parametrize("role", [Role.TRANSFORM_READ, Role.TRANSFORM_WRITE])
    def test_delay_no_transform(self, role):
        with pytest.raises(UnknownFunction):
            Function.parse(None, "DELAY()", role, 0)


class TestTimer:
    async def test_timer_straight(
        self, literal_true, literal_false, literal_one_thousand, dummy_eval_context, later_eval_context
    ):
        value_expr = MockExpression(0)
        expr = timeprocessing.TimerFunction([value_expr, literal_true, literal_false, literal_one_thousand], Role.VALUE)
        assert await expr.eval(dummy_eval_context) == 0
        assert await expr.eval(later_eval_context(500)) == 0
        assert await expr.eval(later_eval_context(1100)) == 0

        value_expr.set_value(1)
        assert await expr.eval(dummy_eval_context) == 1
        assert await expr.eval(later_eval_context(500)) == 1
        assert await expr.eval(later_eval_context(1100)) == 0

    async def test_timer_reset(
        self, literal_true, literal_false, literal_one_thousand, dummy_eval_context, later_eval_context
    ):
        """Should reset the timer when value becomes false."""

        value_expr = MockExpression(1)
        expr = timeprocessing.TimerFunction([value_expr, literal_true, literal_false, literal_one_thousand], Role.VALUE)
        assert await expr.eval(dummy_eval_context) == 1
        assert await expr.eval(later_eval_context(500)) == 1
        value_expr.set_value(0)
        assert await expr.eval(later_eval_context(600)) == 0
        value_expr.set_value(1)
        assert await expr.eval(later_eval_context(700)) == 1
        assert await expr.eval(later_eval_context(1600)) == 1
        assert await expr.eval(later_eval_context(1800)) == 0

    def test_timer_parse(self):
        e = Function.parse(None, "TIMER(1, 2, 3, 4)", Role.VALUE, 0)
        assert isinstance(e, timeprocessing.TimerFunction)

    def test_timer_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "TIMER(1, 2, 3)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "TIMER(1, 2, 3, 4, 5)", Role.VALUE, 0)

    @pytest.mark.parametrize("role", [Role.TRANSFORM_READ, Role.TRANSFORM_WRITE])
    def test_timer_no_transform(self, role):
        with pytest.raises(UnknownFunction):
            Function.parse(None, "TIMER()", role, 0)


class TestSample:
    async def test_sample(self, literal_one_thousand, dummy_eval_context, later_eval_context):
        value_expr = MockExpression(3)
        expr = timeprocessing.SampleFunction([value_expr, literal_one_thousand], Role.VALUE)
        assert await expr.eval(dummy_eval_context) == 3

        value_expr.set_value(16)
        assert await expr.eval(later_eval_context(100)) == 3
        assert await expr.eval(later_eval_context(500)) == 3
        assert await expr.eval(later_eval_context(999)) == 3
        assert await expr.eval(later_eval_context(1001)) == 16
        assert await expr.eval(later_eval_context(10000)) == 16

    def test_sample_parse(self):
        e = Function.parse(None, "SAMPLE(1, 2)", Role.VALUE, 0)
        assert isinstance(e, timeprocessing.SampleFunction)

    def test_sample_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "SAMPLE(1)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "SAMPLE(1, 2, 3)", Role.VALUE, 0)

    @pytest.mark.parametrize("role", [Role.TRANSFORM_READ, Role.TRANSFORM_WRITE])
    def test_sample_no_transform(self, role):
        with pytest.raises(UnknownFunction):
            Function.parse(None, "SAMPLE()", role, 0)


class TestFreeze:
    async def test_freeze(self, dummy_eval_context, later_eval_context):
        value_expr = MockExpression(1)
        time_expr = MockExpression(200)
        expr = timeprocessing.FreezeFunction([value_expr, time_expr], Role.VALUE)
        assert await expr.eval(dummy_eval_context) == 1

        time_expr.set_value(50)
        value_expr.set_value(2)
        assert await expr.eval(later_eval_context(100)) == 1
        assert await expr.eval(later_eval_context(199)) == 1

        time_expr.set_value(200)
        assert await expr.eval(later_eval_context(201)) == 2

        value_expr.set_value(3)
        assert await expr.eval(later_eval_context(500)) == 3

        value_expr.set_value(4)
        assert await expr.eval(later_eval_context(600)) == 3
        assert await expr.eval(later_eval_context(699)) == 3
        assert await expr.eval(later_eval_context(701)) == 4

    def test_freeze_parse(self):
        e = Function.parse(None, "FREEZE(1, 2)", Role.VALUE, 0)
        assert isinstance(e, timeprocessing.FreezeFunction)

    def test_freeze_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "FREEZE(1)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "FREEZE(1, 2, 3)", Role.VALUE, 0)

    @pytest.mark.parametrize("role", [Role.TRANSFORM_READ, Role.TRANSFORM_WRITE])
    def test_freeze_no_transform(self, role):
        with pytest.raises(UnknownFunction):
            Function.parse(None, "FREEZE()", role, 0)


class TestHeld:
    async def test_held_fulfilled(self, literal_sixteen, dummy_eval_context, later_eval_context):
        value_expr = MockExpression(16)
        time_expr = MockExpression(200)
        expr = timeprocessing.HeldFunction([value_expr, literal_sixteen, time_expr], Role.VALUE)
        assert await expr.eval(dummy_eval_context) == 0

        time_expr.set_value(500)
        assert await expr.eval(later_eval_context(499)) == 0
        assert await expr.eval(later_eval_context(501)) == 1

    async def test_held_not_fulfilled(self, literal_sixteen, dummy_eval_context, later_eval_context):
        value_expr = MockExpression(16)
        time_expr = MockExpression(200)
        expr = timeprocessing.HeldFunction([value_expr, literal_sixteen, time_expr], Role.VALUE)
        assert await expr.eval(dummy_eval_context) == 0

        value_expr.set_value(15)
        assert await expr.eval(later_eval_context(100)) == 0
        assert await expr.eval(later_eval_context(201)) == 0

    async def test_held_different_value(self, literal_sixteen, dummy_eval_context, later_eval_context):
        value_expr = MockExpression(15)
        time_expr = MockExpression(200)
        expr = timeprocessing.HeldFunction([value_expr, literal_sixteen, time_expr], Role.VALUE)
        assert await expr.eval(dummy_eval_context) == 0
        assert await expr.eval(later_eval_context(501)) == 0

    def test_held_parse(self):
        e = Function.parse(None, "HELD(1, 2, 3)", Role.VALUE, 0)
        assert isinstance(e, timeprocessing.HeldFunction)

    def test_held_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "HELD(1, 2)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "HELD(1, 2, 3, 4)", Role.VALUE, 0)

    @pytest.mark.parametrize("role", [Role.TRANSFORM_READ, Role.TRANSFORM_WRITE])
    def test_held_no_transform(self, role):
        with pytest.raises(UnknownFunction):
            Function.parse(None, "HELD()", role, 0)


class TestDeriv:
    async def test_deriv(self, dummy_eval_context, later_eval_context):
        value_expr = MockExpression(0)
        time_expr = MockExpression(100)
        expr = timeprocessing.DerivFunction([value_expr, time_expr], Role.VALUE)
        assert round(await expr.eval(dummy_eval_context), 1) == 0

        value_expr.set_value(1)
        assert round(await expr.eval(later_eval_context(200)), 1) == 5

        with pytest.raises(EvalSkipped):
            await expr.eval(later_eval_context(299))

        value_expr.set_value(2)
        assert round(await expr.eval(later_eval_context(400)), 1) == 5

        value_expr.set_value(5)
        time_expr.set_value(200)
        assert round(await expr.eval(later_eval_context(800)), 1) == 7.5

        value_expr.set_value(1)
        time_expr.set_value(100)
        assert round(await expr.eval(later_eval_context(1000)), 1) == -20
        assert round(await expr.eval(later_eval_context(1200)), 1) == 0

    def test_deriv_parse(self):
        e = Function.parse(None, "DERIV(1, 2)", Role.VALUE, 0)
        assert isinstance(e, timeprocessing.DerivFunction)

    def test_deriv_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "DERIV(1)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "DERIV(1, 2, 3)", Role.VALUE, 0)

    @pytest.mark.parametrize("role", [Role.TRANSFORM_READ, Role.TRANSFORM_WRITE])
    def test_deriv_no_transform(self, role):
        with pytest.raises(UnknownFunction):
            Function.parse(None, "DERIV()", role, 0)


class TestInteg:
    async def test_integ(self, dummy_eval_context, later_eval_context):
        acc_expr = MockExpression(0)
        value_expr = MockExpression(0)
        time_expr = MockExpression(100)
        expr = timeprocessing.IntegFunction([value_expr, acc_expr, time_expr], Role.VALUE)
        assert round(await expr.eval(dummy_eval_context), 1) == 0

        value_expr.set_value(10)
        assert round(await expr.eval(later_eval_context(200)), 1) == 1

        with pytest.raises(EvalSkipped):
            await expr.eval(later_eval_context(299))

        acc_expr.set_value(1)
        assert round(await expr.eval(later_eval_context(400)), 1) == 3

        value_expr.set_value(15)
        acc_expr.set_value(3)
        time_expr.set_value(200)
        assert round(await expr.eval(later_eval_context(800)), 1) == 8

        value_expr.set_value(-20)
        acc_expr.set_value(8)
        time_expr.set_value(100)
        assert round(await expr.eval(later_eval_context(1000)), 1) == 7.5

        value_expr.set_value(0)
        acc_expr.set_value(7.5)
        assert round(await expr.eval(later_eval_context(1200)), 1) == 5.5

    def test_integ_parse(self):
        e = Function.parse(None, "INTEG(1, 2, 3)", Role.VALUE, 0)
        assert isinstance(e, timeprocessing.IntegFunction)

    def test_integ_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "INTEG(1, 2)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "INTEG(1, 2, 3, 4)", Role.VALUE, 0)

    @pytest.mark.parametrize("role", [Role.TRANSFORM_READ, Role.TRANSFORM_WRITE])
    def test_integ_no_transform(self, role):
        with pytest.raises(UnknownFunction):
            Function.parse(None, "INTEG()", role, 0)


class TestFMAvg:
    async def test_fmavg(self, dummy_eval_context, later_eval_context):
        value_expr = MockExpression(0)
        width_expr = MockExpression(4)
        time_expr = MockExpression(100)
        expr = timeprocessing.FMAvgFunction([value_expr, width_expr, time_expr], Role.VALUE)
        assert await expr.eval(dummy_eval_context) == 0

        value_expr.set_value(8)
        assert await expr.eval(later_eval_context(101)) == 4

        value_expr.set_value(4)
        with pytest.raises(EvalSkipped):
            await expr.eval(later_eval_context(200))

        assert await expr.eval(later_eval_context(202)) == 4

        value_expr.set_value(-2)
        with pytest.raises(EvalSkipped):
            await expr.eval(later_eval_context(301))

        assert await expr.eval(later_eval_context(303)) == 2.5

        value_expr.set_value(6)
        with pytest.raises(EvalSkipped):
            await expr.eval(later_eval_context(402))

        assert await expr.eval(later_eval_context(504)) == 4

        value_expr.set_value(11)
        width_expr.set_value(3)
        with pytest.raises(EvalSkipped):
            await expr.eval(later_eval_context(603))

        assert await expr.eval(later_eval_context(605)) == 5

        value_expr.set_value(-8)
        time_expr.set_value(200)
        with pytest.raises(EvalSkipped):
            await expr.eval(later_eval_context(804))

        assert await expr.eval(later_eval_context(806)) == 3

    def test_fmavg_parse(self):
        e = Function.parse(None, "FMAVG(1, 2, 3)", Role.VALUE, 0)
        assert isinstance(e, timeprocessing.FMAvgFunction)

    def test_fmavg_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "FMAVG(1, 2)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "FMAVG(1, 2, 3, 4)", Role.VALUE, 0)

    @pytest.mark.parametrize("role", [Role.TRANSFORM_READ, Role.TRANSFORM_WRITE])
    def test_fmavg_no_transform(self, role):
        with pytest.raises(UnknownFunction):
            Function.parse(None, "FMAVG()", role, 0)


class TestFMedian:
    async def test_fmedian(self, dummy_eval_context, later_eval_context):
        value_expr = MockExpression(0)
        width_expr = MockExpression(4)
        time_expr = MockExpression(100)
        expr = timeprocessing.FMedianFunction([value_expr, width_expr, time_expr], Role.VALUE)
        assert await expr.eval(dummy_eval_context) == 0

        value_expr.set_value(8)
        assert await expr.eval(later_eval_context(101)) == 8

        value_expr.set_value(4)
        with pytest.raises(EvalSkipped):
            await expr.eval(later_eval_context(200))

        assert await expr.eval(later_eval_context(202)) == 4

        value_expr.set_value(-2)
        with pytest.raises(EvalSkipped):
            await expr.eval(later_eval_context(301))

        assert await expr.eval(later_eval_context(303)) == 4

        value_expr.set_value(6)
        with pytest.raises(EvalSkipped):
            await expr.eval(later_eval_context(402))

        assert await expr.eval(later_eval_context(504)) == 6

        value_expr.set_value(11)
        width_expr.set_value(3)
        with pytest.raises(EvalSkipped):
            await expr.eval(later_eval_context(603))

        assert await expr.eval(later_eval_context(605)) == 6

        value_expr.set_value(-8)
        time_expr.set_value(200)
        with pytest.raises(EvalSkipped):
            await expr.eval(later_eval_context(804))

        assert await expr.eval(later_eval_context(806)) == 6

    def test_fmedian_parse(self):
        e = Function.parse(None, "FMEDIAN(1, 2, 3)", Role.VALUE, 0)
        assert isinstance(e, timeprocessing.FMedianFunction)

    def test_fmedian_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "FMEDIAN(1, 2)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "FMEDIAN(1, 2, 3, 4)", Role.VALUE, 0)

    @pytest.mark.parametrize("role", [Role.TRANSFORM_READ, Role.TRANSFORM_WRITE])
    def test_fmedian_no_transform(self, role):
        with pytest.raises(UnknownFunction):
            Function.parse(None, "FMEDIAN()", role, 0)
