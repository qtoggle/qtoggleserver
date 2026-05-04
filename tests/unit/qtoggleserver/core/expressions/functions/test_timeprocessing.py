import pytest

from qtoggleserver.core.expressions import DEP_ASAP, Function, Role, timeprocessing
from qtoggleserver.core.expressions.exceptions import InvalidNumberOfArguments, UnknownFunction
from tests.unit.qtoggleserver.mock.expressions import MockExpression


class TestDelay:
    async def test(self, dummy_eval_context, later_eval_context):
        value_expr = MockExpression(3)
        delay_expr = MockExpression(1000)
        expr = timeprocessing.DelayFunction([value_expr, delay_expr], Role.VALUE)

        # Initial returned value is 3 and it should stay that way until next value change
        assert await expr.eval(dummy_eval_context) == 3
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms)
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 1e6)
        assert await expr.eval(later_eval_context(100)) == 3
        assert await expr.eval(later_eval_context(1e6)) == 3

        # Now (after 500ms) we change the value to 16, but it should still return 3 until 1000ms later
        value_expr.set_value(16)
        assert await expr.eval(later_eval_context(500)) == 3
        assert await expr.eval(later_eval_context(1499)) == 3
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 500)
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 1499)
        assert not expr.is_asap_eval_paused(dummy_eval_context.now_ms + 1500)

        # After 1000ms, it should return the new value; changing the delay argument should be taken into account
        delay_expr.set_value(1200)
        assert await expr.eval(later_eval_context(1699)) == 3
        assert await expr.eval(later_eval_context(1700)) == 16
        assert await expr.eval(later_eval_context(10000)) == 16

        # Test that eval is paused after the last queued value has been processed
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 1e6)

    def test_parse(self):
        e = Function.parse(None, "DELAY(1, 2)", Role.VALUE, 0)
        assert isinstance(e, timeprocessing.DelayFunction)

    def test_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "DELAY(1)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "DELAY(1, 2, 3)", Role.VALUE, 0)

    @pytest.mark.parametrize("role", [Role.TRANSFORM_READ, Role.TRANSFORM_WRITE])
    def test_no_transform(self, role):
        with pytest.raises(UnknownFunction):
            Function.parse(None, "DELAY()", role, 0)

    def test_deps(self):
        assert timeprocessing.DelayFunction.DEPS == {DEP_ASAP}


class TestTimer:
    async def test(self, literal_true, literal_false, dummy_eval_context, later_eval_context):
        value_expr = MockExpression(0)
        timeout_expr = MockExpression(1000)

        expr = timeprocessing.TimerFunction([value_expr, literal_true, literal_false, timeout_expr], Role.VALUE)
        assert await expr.eval(dummy_eval_context) == 0
        assert await expr.eval(later_eval_context(1100)) == 0
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 1e6)

        value_expr.set_value(1)
        assert await expr.eval(later_eval_context(500)) == 1
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 1499)
        assert not expr.is_asap_eval_paused(dummy_eval_context.now_ms + 1500)
        assert await expr.eval(later_eval_context(1499)) == 1
        assert await expr.eval(later_eval_context(1500)) == 0

        # Should reset the timer when value becomes false
        value_expr.set_value(0)
        assert await expr.eval(later_eval_context(1600)) == 0
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 1e6)

        # Changing the timeout argument should be taken into account
        timeout_expr.set_value(1200)
        value_expr.set_value(1)
        assert await expr.eval(later_eval_context(1700)) == 1
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 2899)
        assert not expr.is_asap_eval_paused(dummy_eval_context.now_ms + 2900)

    def test_parse(self):
        e = Function.parse(None, "TIMER(1, 2, 3, 4)", Role.VALUE, 0)
        assert isinstance(e, timeprocessing.TimerFunction)

    def test_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "TIMER(1, 2, 3)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "TIMER(1, 2, 3, 4, 5)", Role.VALUE, 0)

    @pytest.mark.parametrize("role", [Role.TRANSFORM_READ, Role.TRANSFORM_WRITE])
    def test_no_transform(self, role):
        with pytest.raises(UnknownFunction):
            Function.parse(None, "TIMER()", role, 0)

    def test_deps(self):
        assert timeprocessing.TimerFunction.DEPS == {DEP_ASAP}


class TestSample:
    async def test(self, dummy_eval_context, later_eval_context):
        value_expr = MockExpression(3)
        duration_expr = MockExpression(1000)
        expr = timeprocessing.SampleFunction([value_expr, duration_expr], Role.VALUE)
        assert await expr.eval(dummy_eval_context) == 3
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 999)
        assert not expr.is_asap_eval_paused(dummy_eval_context.now_ms + 1000)

        value_expr.set_value(16)
        assert await expr.eval(later_eval_context(1)) == 3
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 999)
        assert not expr.is_asap_eval_paused(dummy_eval_context.now_ms + 1000)

        assert await expr.eval(later_eval_context(999)) == 3
        assert await expr.eval(later_eval_context(1000)) == 16

        # Changing the duration argument should be taken into account
        value_expr.set_value(23)
        duration_expr.set_value(1200)
        assert await expr.eval(later_eval_context(1001)) == 16
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 2199)
        assert not expr.is_asap_eval_paused(dummy_eval_context.now_ms + 2200)
        assert await expr.eval(later_eval_context(2199)) == 16
        assert await expr.eval(later_eval_context(2200)) == 23

    def test_parse(self):
        e = Function.parse(None, "SAMPLE(1, 2)", Role.VALUE, 0)
        assert isinstance(e, timeprocessing.SampleFunction)

    def test_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "SAMPLE(1)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "SAMPLE(1, 2, 3)", Role.VALUE, 0)

    @pytest.mark.parametrize("role", [Role.TRANSFORM_READ, Role.TRANSFORM_WRITE])
    def test_no_transform(self, role):
        with pytest.raises(UnknownFunction):
            Function.parse(None, "SAMPLE()", role, 0)

    def test_deps(self):
        assert timeprocessing.SampleFunction.DEPS == {DEP_ASAP}


class TestFreeze:
    async def test(self, dummy_eval_context, later_eval_context):
        value_expr = MockExpression(1)
        duration_expr = MockExpression(1000)
        expr = timeprocessing.FreezeFunction([value_expr, duration_expr], Role.VALUE)

        assert await expr.eval(dummy_eval_context) == 1
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 999)
        assert not expr.is_asap_eval_paused(dummy_eval_context.now_ms + 1000)

        value_expr.set_value(2)
        assert await expr.eval(later_eval_context(999)) == 1
        assert await expr.eval(later_eval_context(1000)) == 2
        assert await expr.eval(later_eval_context(3000)) == 2
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 1e6)

        # Changing the duration argument should be taken into account
        duration_expr.set_value(1200)
        value_expr.set_value(3)
        assert await expr.eval(later_eval_context(3500)) == 3

        value_expr.set_value(4)
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 4699)
        assert not expr.is_asap_eval_paused(dummy_eval_context.now_ms + 4700)
        assert await expr.eval(later_eval_context(4699)) == 3
        assert await expr.eval(later_eval_context(4700)) == 4

        # Test that eval is paused while timer is active
        assert await expr.eval(later_eval_context(5000)) == 4
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 5899)
        assert not expr.is_asap_eval_paused(dummy_eval_context.now_ms + 5900)

    def test_parse(self):
        e = Function.parse(None, "FREEZE(1, 2)", Role.VALUE, 0)
        assert isinstance(e, timeprocessing.FreezeFunction)

    def test_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "FREEZE(1)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "FREEZE(1, 2, 3)", Role.VALUE, 0)

    @pytest.mark.parametrize("role", [Role.TRANSFORM_READ, Role.TRANSFORM_WRITE])
    def test_no_transform(self, role):
        with pytest.raises(UnknownFunction):
            Function.parse(None, "FREEZE()", role, 0)

    def test_deps(self):
        assert timeprocessing.FreezeFunction.DEPS == {DEP_ASAP}


class TestHeld:
    async def test(self, literal_sixteen, dummy_eval_context, later_eval_context):
        value_expr = MockExpression(3)
        duration_expr = MockExpression(200)
        expr = timeprocessing.HeldFunction([value_expr, literal_sixteen, duration_expr], Role.VALUE)

        assert await expr.eval(dummy_eval_context) == 0
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 1e6)
        assert await expr.eval(later_eval_context(201)) == 0

        value_expr.set_value(16)
        assert await expr.eval(later_eval_context(1000)) == 0
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 1199)
        assert not expr.is_asap_eval_paused(dummy_eval_context.now_ms + 1200)
        assert await expr.eval(later_eval_context(1199)) == 0
        assert await expr.eval(later_eval_context(1200)) == 1
        assert await expr.eval(later_eval_context(1201)) == 1
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 1e6)

    def test_parse(self):
        e = Function.parse(None, "HELD(1, 2, 3)", Role.VALUE, 0)
        assert isinstance(e, timeprocessing.HeldFunction)

    def test_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "HELD(1, 2)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "HELD(1, 2, 3, 4)", Role.VALUE, 0)

    @pytest.mark.parametrize("role", [Role.TRANSFORM_READ, Role.TRANSFORM_WRITE])
    def test_no_transform(self, role):
        with pytest.raises(UnknownFunction):
            Function.parse(None, "HELD()", role, 0)

    def test_deps(self):
        assert timeprocessing.HeldFunction.DEPS == {DEP_ASAP}


class TestDeriv:
    async def test(self, dummy_eval_context, later_eval_context):
        value_expr = MockExpression(0)
        interval_expr = MockExpression(200)
        expr = timeprocessing.DerivFunction([value_expr, interval_expr], Role.VALUE)

        assert round(await expr.eval(dummy_eval_context), 1) == 0
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 199)
        assert not expr.is_asap_eval_paused(dummy_eval_context.now_ms + 200)

        value_expr.set_value(1)
        assert round(await expr.eval(later_eval_context(199)), 1) == 0
        assert round(await expr.eval(later_eval_context(200)), 1) == 5
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 399)
        assert not expr.is_asap_eval_paused(dummy_eval_context.now_ms + 400)

        value_expr.set_value(2)
        assert round(await expr.eval(later_eval_context(400)), 1) == 5
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 599)
        assert not expr.is_asap_eval_paused(dummy_eval_context.now_ms + 600)

        value_expr.set_value(5)
        interval_expr.set_value(400)
        assert round(await expr.eval(later_eval_context(799)), 1) == 5
        assert round(await expr.eval(later_eval_context(800)), 1) == 7.5
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 1199)
        assert not expr.is_asap_eval_paused(dummy_eval_context.now_ms + 1200)

        value_expr.set_value(1)
        interval_expr.set_value(100)
        assert round(await expr.eval(later_eval_context(1000)), 1) == -20
        assert round(await expr.eval(later_eval_context(1100)), 1) == 0
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 1199)
        assert not expr.is_asap_eval_paused(dummy_eval_context.now_ms + 1200)

    async def test_time_jump_detection(self, dummy_eval_context, later_eval_context):
        value_expr = MockExpression(0)
        interval_expr = MockExpression(200)
        expr = timeprocessing.DerivFunction([value_expr, interval_expr], Role.VALUE)

        assert round(await expr.eval(dummy_eval_context), 1) == 0
        value_expr.set_value(1)
        assert round(await expr.eval(later_eval_context(200)), 1) == 5
        value_expr.set_value(10)

        assert round(await expr.eval(later_eval_context(1e10)), 1) == 0
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 1e10 + 199)
        assert not expr.is_asap_eval_paused(dummy_eval_context.now_ms + 1e10 + 200)

    def test_parse(self):
        e = Function.parse(None, "DERIV(1, 2)", Role.VALUE, 0)
        assert isinstance(e, timeprocessing.DerivFunction)

    def test_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "DERIV(1)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "DERIV(1, 2, 3)", Role.VALUE, 0)

    @pytest.mark.parametrize("role", [Role.TRANSFORM_READ, Role.TRANSFORM_WRITE])
    def test_no_transform(self, role):
        with pytest.raises(UnknownFunction):
            Function.parse(None, "DERIV()", role, 0)

    def test_deps(self):
        assert timeprocessing.DerivFunction.DEPS == {DEP_ASAP}


class TestInteg:
    async def test(self, dummy_eval_context, later_eval_context):
        acc_expr = MockExpression(0)
        value_expr = MockExpression(0)
        interval_expr = MockExpression(200)
        expr = timeprocessing.IntegFunction([value_expr, acc_expr, interval_expr], Role.VALUE)

        assert round(await expr.eval(dummy_eval_context), 1) == 0
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 199)
        assert not expr.is_asap_eval_paused(dummy_eval_context.now_ms + 200)

        value_expr.set_value(10)
        assert round(await expr.eval(later_eval_context(199)), 1) == 0
        assert round(await expr.eval(later_eval_context(200)), 1) == 1
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 399)
        assert not expr.is_asap_eval_paused(dummy_eval_context.now_ms + 400)

        acc_expr.set_value(1)
        assert round(await expr.eval(later_eval_context(400)), 1) == 3
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 599)
        assert not expr.is_asap_eval_paused(dummy_eval_context.now_ms + 600)

        value_expr.set_value(15)
        acc_expr.set_value(3)
        interval_expr.set_value(400)
        assert round(await expr.eval(later_eval_context(799)), 1) == 3
        assert round(await expr.eval(later_eval_context(800)), 1) == 8
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 1199)
        assert not expr.is_asap_eval_paused(dummy_eval_context.now_ms + 1200)

        value_expr.set_value(-20)
        acc_expr.set_value(8)
        interval_expr.set_value(100)
        assert round(await expr.eval(later_eval_context(899)), 1) == 8
        assert round(await expr.eval(later_eval_context(900)), 2) == 7.75
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 999)
        assert not expr.is_asap_eval_paused(dummy_eval_context.now_ms + 1000)

        value_expr.set_value(0)
        acc_expr.set_value(7.5)
        assert round(await expr.eval(later_eval_context(1000)), 1) == 6.5

    async def test_time_jump_detection(self, dummy_eval_context, later_eval_context):
        acc_expr = MockExpression(3)
        value_expr = MockExpression(0)
        interval_expr = MockExpression(200)
        expr = timeprocessing.IntegFunction([value_expr, acc_expr, interval_expr], Role.VALUE)

        assert round(await expr.eval(dummy_eval_context), 1) == 3
        value_expr.set_value(10)
        assert round(await expr.eval(later_eval_context(200)), 1) == 4
        value_expr.set_value(20)

        assert round(await expr.eval(later_eval_context(1e10)), 1) == 3
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 1e10 + 199)
        assert not expr.is_asap_eval_paused(dummy_eval_context.now_ms + 1e10 + 200)

    def test_parse(self):
        e = Function.parse(None, "INTEG(1, 2, 3)", Role.VALUE, 0)
        assert isinstance(e, timeprocessing.IntegFunction)

    def test_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "INTEG(1, 2)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "INTEG(1, 2, 3, 4)", Role.VALUE, 0)

    @pytest.mark.parametrize("role", [Role.TRANSFORM_READ, Role.TRANSFORM_WRITE])
    def test_no_transform(self, role):
        with pytest.raises(UnknownFunction):
            Function.parse(None, "INTEG()", role, 0)

    def test_deps(self):
        assert timeprocessing.IntegFunction.DEPS == {DEP_ASAP}


class TestFMAvg:
    async def test(self, dummy_eval_context, later_eval_context):
        value_expr = MockExpression(0)
        width_expr = MockExpression(4)
        time_expr = MockExpression(100)
        expr = timeprocessing.FMAvgFunction([value_expr, width_expr, time_expr], Role.VALUE)

        assert await expr.eval(dummy_eval_context) == 0
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 99)
        assert not expr.is_asap_eval_paused(dummy_eval_context.now_ms + 100)

        value_expr.set_value(8)
        assert await expr.eval(later_eval_context(99)) == 0
        assert await expr.eval(later_eval_context(100)) == 4
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 199)
        assert not expr.is_asap_eval_paused(dummy_eval_context.now_ms + 200)

        value_expr.set_value(4)
        assert await expr.eval(later_eval_context(199)) == 4
        assert await expr.eval(later_eval_context(200)) == 4
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 299)
        assert not expr.is_asap_eval_paused(dummy_eval_context.now_ms + 300)

        value_expr.set_value(-2)
        assert await expr.eval(later_eval_context(299)) == 4
        assert await expr.eval(later_eval_context(300)) == 2.5
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 399)
        assert not expr.is_asap_eval_paused(dummy_eval_context.now_ms + 400)

        value_expr.set_value(6)
        assert await expr.eval(later_eval_context(399)) == 2.5
        assert await expr.eval(later_eval_context(400)) == 4
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 499)
        assert not expr.is_asap_eval_paused(dummy_eval_context.now_ms + 500)

        value_expr.set_value(11)
        width_expr.set_value(3)
        assert await expr.eval(later_eval_context(499)) == 4
        assert await expr.eval(later_eval_context(500)) == 5
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 599)
        assert not expr.is_asap_eval_paused(dummy_eval_context.now_ms + 600)

        value_expr.set_value(-8)
        time_expr.set_value(200)
        assert await expr.eval(later_eval_context(699)) == 5
        assert await expr.eval(later_eval_context(700)) == 3
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 899)
        assert not expr.is_asap_eval_paused(dummy_eval_context.now_ms + 900)

    def test_parse(self):
        e = Function.parse(None, "FMAVG(1, 2, 3)", Role.VALUE, 0)
        assert isinstance(e, timeprocessing.FMAvgFunction)

    def test_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "FMAVG(1, 2)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "FMAVG(1, 2, 3, 4)", Role.VALUE, 0)

    @pytest.mark.parametrize("role", [Role.TRANSFORM_READ, Role.TRANSFORM_WRITE])
    def test_no_transform(self, role):
        with pytest.raises(UnknownFunction):
            Function.parse(None, "FMAVG()", role, 0)

    def test_deps(self):
        assert timeprocessing.FMAvgFunction.DEPS == {DEP_ASAP}


class TestFMedian:
    async def test(self, dummy_eval_context, later_eval_context):
        value_expr = MockExpression(0)
        width_expr = MockExpression(4)
        time_expr = MockExpression(100)
        expr = timeprocessing.FMedianFunction([value_expr, width_expr, time_expr], Role.VALUE)

        assert await expr.eval(dummy_eval_context) == 0
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 99)
        assert not expr.is_asap_eval_paused(dummy_eval_context.now_ms + 100)

        value_expr.set_value(8)
        assert await expr.eval(later_eval_context(99)) == 0
        assert await expr.eval(later_eval_context(100)) == 8
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 199)
        assert not expr.is_asap_eval_paused(dummy_eval_context.now_ms + 200)

        value_expr.set_value(4)
        assert await expr.eval(later_eval_context(199)) == 8
        assert await expr.eval(later_eval_context(200)) == 4
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 299)
        assert not expr.is_asap_eval_paused(dummy_eval_context.now_ms + 300)

        value_expr.set_value(-2)
        assert await expr.eval(later_eval_context(299)) == 4
        assert await expr.eval(later_eval_context(300)) == 4
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 399)
        assert not expr.is_asap_eval_paused(dummy_eval_context.now_ms + 400)

        value_expr.set_value(6)
        assert await expr.eval(later_eval_context(399)) == 4
        assert await expr.eval(later_eval_context(400)) == 6
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 499)
        assert not expr.is_asap_eval_paused(dummy_eval_context.now_ms + 500)

        value_expr.set_value(11)
        width_expr.set_value(3)
        assert await expr.eval(later_eval_context(499)) == 6
        assert await expr.eval(later_eval_context(500)) == 6
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 599)
        assert not expr.is_asap_eval_paused(dummy_eval_context.now_ms + 600)

        value_expr.set_value(-8)
        time_expr.set_value(200)
        assert await expr.eval(later_eval_context(699)) == 6
        assert await expr.eval(later_eval_context(700)) == 6
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 899)
        assert not expr.is_asap_eval_paused(dummy_eval_context.now_ms + 900)

    def test_parse(self):
        e = Function.parse(None, "FMEDIAN(1, 2, 3)", Role.VALUE, 0)
        assert isinstance(e, timeprocessing.FMedianFunction)

    def test_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "FMEDIAN(1, 2)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "FMEDIAN(1, 2, 3, 4)", Role.VALUE, 0)

    @pytest.mark.parametrize("role", [Role.TRANSFORM_READ, Role.TRANSFORM_WRITE])
    def test_no_transform(self, role):
        with pytest.raises(UnknownFunction):
            Function.parse(None, "FMEDIAN()", role, 0)

    def test_deps(self):
        assert timeprocessing.FMedianFunction.DEPS == {DEP_ASAP}
