import pytest

from qtoggleserver.core import history
from qtoggleserver.core.expressions import DEP_ASAP, DEP_SECOND, EvalContext, Function, Role, various
from qtoggleserver.core.expressions.exceptions import (
    InvalidArgumentKind,
    InvalidNumberOfArguments,
    PortValueUnavailable,
    RealDateTimeUnavailable,
    UnknownFunction,
)
from tests.unit.qtoggleserver.mock.expressions import MockExpression, MockPortRef, MockPortValue


class TestAvailable:
    async def test_value_available(self, mock_num_port1, dummy_eval_context):
        """Should return 1 if value is available (not None)."""

        mock_expr = MockExpression(16)
        expr = various.AvailableFunction([mock_expr], Role.VALUE)
        assert await expr.eval(dummy_eval_context) == 1

        mock_expr = MockExpression(16)
        mock_expr.set_value(0)
        assert await expr.eval(dummy_eval_context) == 1

    async def test_value_none(self, mock_num_port1, dummy_eval_context):
        """Should return 0 if value is None."""

        mock_expr = MockExpression(None)
        expr = various.AvailableFunction([mock_expr], Role.VALUE)
        assert await expr.eval(dummy_eval_context) == 0

    async def test_value_unavailable(self, mock_num_port1, literal_unavailable, dummy_eval_context):
        """Should return 0 if value is unavailable."""

        expr = various.AvailableFunction([literal_unavailable], Role.VALUE)
        assert await expr.eval(dummy_eval_context) == 0

    async def test_func(self, mock_num_port1):
        port_expr = MockPortValue(mock_num_port1)
        acc_expr = MockExpression(13)
        func_expr = various.AccFunction([port_expr, acc_expr], Role.VALUE)
        expr = various.AvailableFunction([func_expr], Role.VALUE)
        assert await expr.eval(EvalContext(port_values={"nid1": mock_num_port1.get_last_read_value()}, now_ms=0)) == 0

        mock_num_port1.set_last_read_value(16)
        assert await expr.eval(EvalContext(port_values={"nid1": mock_num_port1.get_last_read_value()}, now_ms=0)) == 1

        port_expr = MockPortValue(None, port_id="inexistent_id")
        func_expr = various.AccFunction([port_expr, acc_expr], Role.VALUE)
        expr = various.AvailableFunction([func_expr], Role.VALUE)
        assert await expr.eval(EvalContext(port_values={"nid1": mock_num_port1.get_last_read_value()}, now_ms=0)) == 0

    def test_parse(self):
        e = Function.parse(None, "AVAILABLE(1)", Role.VALUE, 0)
        assert isinstance(e, various.AvailableFunction)

    def test_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "AVAILABLE()", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "AVAILABLE(1, 2)", Role.VALUE, 0)


class TestDefault:
    async def test_value_available(self, mock_num_port1, dummy_eval_context):
        """Should return value when available (not None)."""

        mock_expr = MockExpression(16)
        def_expr = MockExpression(13)
        expr = various.DefaultFunction([mock_expr, def_expr], Role.VALUE)
        assert await expr.eval(dummy_eval_context) == 16

        mock_expr.set_value(0)
        assert await expr.eval(dummy_eval_context) == 0

    async def test_value_none(self, mock_num_port1, dummy_eval_context):
        """Should return default value when value is None."""

        mock_expr = MockExpression(None)
        def_expr = MockExpression(13)
        expr = various.DefaultFunction([mock_expr, def_expr], Role.VALUE)
        assert await expr.eval(dummy_eval_context) == 13

    async def test_value_unavailable(self, mock_num_port1, literal_unavailable, dummy_eval_context):
        """Should return default value when value is unavailable."""

        def_expr = MockExpression(13)
        expr = various.DefaultFunction([literal_unavailable, def_expr], Role.VALUE)
        assert await expr.eval(dummy_eval_context) == 13

    def test_parse(self):
        e = Function.parse(None, "DEFAULT(1, 2)", Role.VALUE, 0)
        assert isinstance(e, various.DefaultFunction)

    def test_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "DEFAULT(1)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "AVAILABLE(1, 2, 3)", Role.VALUE, 0)


class TestIgnChg:
    async def test(self, dummy_eval_context):
        """Should simply return value."""

        mock_expr = MockExpression(16)
        expr = various.IgnChgFunction([mock_expr], Role.VALUE)
        assert await expr.eval(dummy_eval_context) == 16

    async def test_deps(self):
        mock_expr = MockExpression(16)
        expr = various.IgnChgFunction([mock_expr], Role.VALUE)
        assert len(expr.get_deps()) == 0

    def test_parse(self):
        e = Function.parse(None, "IGNCHG(1)", Role.VALUE, 0)
        assert isinstance(e, various.IgnChgFunction)

    def test_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "IGNCHG(1, 2)", Role.VALUE, 0)


class TestRising:
    async def test(self, mock_num_port1):
        port_expr = MockPortValue(mock_num_port1)
        expr = various.RisingFunction([port_expr], Role.VALUE)

        mock_num_port1.set_last_read_value(10)
        assert await expr.eval(EvalContext(port_values={"nid1": mock_num_port1.get_last_read_value()}, now_ms=0)) == 0
        assert await expr.eval(EvalContext(port_values={"nid1": mock_num_port1.get_last_read_value()}, now_ms=0)) == 0

        mock_num_port1.set_last_read_value(13)
        assert await expr.eval(EvalContext(port_values={"nid1": mock_num_port1.get_last_read_value()}, now_ms=0)) == 1
        assert await expr.eval(EvalContext(port_values={"nid1": mock_num_port1.get_last_read_value()}, now_ms=0)) == 0

        mock_num_port1.set_last_read_value(9)
        assert await expr.eval(EvalContext(port_values={"nid1": mock_num_port1.get_last_read_value()}, now_ms=0)) == 0

    def test_parse(self):
        e = Function.parse(None, "RISING(1)", Role.VALUE, 0)
        assert isinstance(e, various.RisingFunction)

    def test_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "RISING()", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "RISING(1, 2)", Role.VALUE, 0)


class TestFalling:
    async def test(self, mock_num_port1):
        port_expr = MockPortValue(mock_num_port1)
        expr = various.FallingFunction([port_expr], Role.VALUE)

        mock_num_port1.set_last_read_value(13)
        assert await expr.eval(EvalContext(port_values={"nid1": mock_num_port1.get_last_read_value()}, now_ms=0)) == 0
        assert await expr.eval(EvalContext(port_values={"nid1": mock_num_port1.get_last_read_value()}, now_ms=0)) == 0

        mock_num_port1.set_last_read_value(10)
        assert await expr.eval(EvalContext(port_values={"nid1": mock_num_port1.get_last_read_value()}, now_ms=0)) == 1
        assert await expr.eval(EvalContext(port_values={"nid1": mock_num_port1.get_last_read_value()}, now_ms=0)) == 0

        mock_num_port1.set_last_read_value(14)
        assert await expr.eval(EvalContext(port_values={"nid1": mock_num_port1.get_last_read_value()}, now_ms=0)) == 0

    def test_parse(self):
        e = Function.parse(None, "FALLING(1)", Role.VALUE, 0)
        assert isinstance(e, various.FallingFunction)

    def test_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "FALLING()", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "FALLING(1, 2)", Role.VALUE, 0)


class TestAcc:
    async def test(self, dummy_eval_context):
        value_expr = MockExpression(16)
        acc_expr = MockExpression(13)
        expr = various.AccFunction([value_expr, acc_expr], Role.VALUE)
        assert await expr.eval(dummy_eval_context) == 13

        acc_expr.set_value(-5)
        assert await expr.eval(dummy_eval_context) == -5

        value_expr.set_value(26)
        assert await expr.eval(dummy_eval_context) == 5

        value_expr.set_value(20)
        acc_expr.set_value(5)
        assert await expr.eval(dummy_eval_context) == -1

    def test_parse(self):
        e = Function.parse(None, "ACC(1, 2)", Role.VALUE, 0)
        assert isinstance(e, various.AccFunction)

    def test_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "ACC(1)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "ACC(1, 2, 3)", Role.VALUE, 0)


class TestAccInc:
    async def test(self, dummy_eval_context):
        value_expr = MockExpression(16)
        acc_expr = MockExpression(13)
        expr = various.AccIncFunction([value_expr, acc_expr], Role.VALUE)
        assert await expr.eval(dummy_eval_context) == 13

        acc_expr.set_value(-5)
        assert await expr.eval(dummy_eval_context) == -5

        value_expr.set_value(26)
        assert await expr.eval(dummy_eval_context) == 5

        value_expr.set_value(20)
        acc_expr.set_value(5)
        assert await expr.eval(dummy_eval_context) == 5

    def test_parse(self):
        e = Function.parse(None, "ACCINC(1, 2)", Role.VALUE, 0)
        assert isinstance(e, various.AccIncFunction)

    def test_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "ACCINC(1)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "ACCINC(1, 2, 3)", Role.VALUE, 0)


class TestHyst:
    async def test_rise(self, literal_three, literal_sixteen, dummy_eval_context):
        value_expr = MockExpression(1)
        expr = various.HystFunction([value_expr, literal_three, literal_sixteen], Role.VALUE)
        assert await expr.eval(dummy_eval_context) == 0

        value_expr.set_value(2)
        assert await expr.eval(dummy_eval_context) == 0

        value_expr.set_value(3)
        assert await expr.eval(dummy_eval_context) == 0

        value_expr.set_value(4)
        assert await expr.eval(dummy_eval_context) == 0

        value_expr.set_value(16)
        assert await expr.eval(dummy_eval_context) == 0

        value_expr.set_value(10)
        assert await expr.eval(dummy_eval_context) == 0

        value_expr.set_value(2)
        assert await expr.eval(dummy_eval_context) == 0

        value_expr.set_value(17)
        assert await expr.eval(dummy_eval_context) == 1

        value_expr.set_value(20)
        assert await expr.eval(dummy_eval_context) == 1

    async def test_fall(self, literal_three, literal_sixteen, dummy_eval_context):
        value_expr = MockExpression(20)
        expr = various.HystFunction([value_expr, literal_three, literal_sixteen], Role.VALUE)
        assert await expr.eval(dummy_eval_context) == 1

        value_expr.set_value(17)
        assert await expr.eval(dummy_eval_context) == 1

        value_expr.set_value(16)
        assert await expr.eval(dummy_eval_context) == 1

        value_expr.set_value(10)
        assert await expr.eval(dummy_eval_context) == 1

        value_expr.set_value(4)
        assert await expr.eval(dummy_eval_context) == 1

        value_expr.set_value(20)
        assert await expr.eval(dummy_eval_context) == 1

        value_expr.set_value(3)
        assert await expr.eval(dummy_eval_context) == 1

        value_expr.set_value(2)
        assert await expr.eval(dummy_eval_context) == 0

        value_expr.set_value(0)
        assert await expr.eval(dummy_eval_context) == 0

    def test_parse(self):
        e = Function.parse(None, "HYST(1, 2, 3)", Role.VALUE, 0)
        assert isinstance(e, various.HystFunction)

    def test_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "HYST(1, 2)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "HYST(1, 2, 3, 4)", Role.VALUE, 0)


class TestOnOffAuto:
    async def test(self, dummy_eval_context):
        value_expr = MockExpression(0)
        auto_expr = MockExpression(13)
        expr = various.OnOffAutoFunction([value_expr, auto_expr], Role.VALUE)

        value_expr.set_value(0)
        assert await expr.eval(dummy_eval_context) == 13

        value_expr.set_value(-1)
        assert await expr.eval(dummy_eval_context) is False

        value_expr.set_value(-10)
        assert await expr.eval(dummy_eval_context) is False

        value_expr.set_value(1)
        assert await expr.eval(dummy_eval_context) is True

        value_expr.set_value(10)
        assert await expr.eval(dummy_eval_context) is True

    def test_parse(self):
        e = Function.parse(None, "ONOFFAUTO(1, 2)", Role.VALUE, 0)
        assert isinstance(e, various.OnOffAutoFunction)

    def test_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "ONOFFAUTO(1)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "ONOFFAUTO(1, 2, 3)", Role.VALUE, 0)


class TestSequence:
    async def test(
        self,
        literal_two,
        literal_three,
        literal_sixteen,
        literal_one_hundred,
        literal_two_hundreds,
        dummy_eval_context,
        later_eval_context,
    ):
        time_expr = MockExpression(100)
        expr = various.SequenceFunction(
            [
                literal_three,
                literal_one_hundred,
                literal_sixteen,
                literal_two_hundreds,
                literal_two,
                time_expr,
            ],
            Role.VALUE,
        )
        assert await expr.eval(dummy_eval_context) == 3
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms)
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 99)
        assert not expr.is_asap_eval_paused(dummy_eval_context.now_ms + 100)
        assert await expr.eval(later_eval_context(100)) == 3

        assert await expr.eval(later_eval_context(101)) == 16
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 101)
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 299)
        assert not expr.is_asap_eval_paused(dummy_eval_context.now_ms + 300)
        assert await expr.eval(later_eval_context(200)) == 16
        assert await expr.eval(later_eval_context(300)) == 16

        assert await expr.eval(later_eval_context(301)) == 2
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 301)
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 399)
        assert not expr.is_asap_eval_paused(dummy_eval_context.now_ms + 400)
        assert await expr.eval(later_eval_context(399)) == 2

        # Changing the time argument should be taken into account
        time_expr.set_value(200)
        assert await expr.eval(later_eval_context(401)) == 2
        assert await expr.eval(later_eval_context(501)) == 3
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 501)
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 599)
        assert not expr.is_asap_eval_paused(dummy_eval_context.now_ms + 600)

    def test_parse(self):
        e = Function.parse(None, "SEQUENCE(1, 2, 3, 4)", Role.VALUE, 0)
        assert isinstance(e, various.SequenceFunction)

    def test_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "SEQUENCE(1)", Role.VALUE, 0)

    @pytest.mark.parametrize("role", [Role.TRANSFORM_READ, Role.TRANSFORM_WRITE])
    def test_no_transform(self, role):
        with pytest.raises(UnknownFunction):
            Function.parse(None, "SEQUENCE(1)", role, 0)

    def test_deps(self):
        assert various.SequenceFunction.DEPS == {DEP_ASAP}


class TestHistory:
    async def test_older_past(
        self, freezer, mock_persist_driver, dummy_utc_datetime, dummy_timestamp, mock_num_port1, dummy_eval_context
    ):
        freezer.move_to(dummy_utc_datetime)
        mock_persist_driver.enable_samples_support()

        port_expr = MockPortRef(mock_num_port1)
        ts_expr = MockExpression(dummy_timestamp - 3600)
        diff_expr = MockExpression(-3600)

        expr = various.HistoryFunction([port_expr, ts_expr, diff_expr], Role.VALUE)

        mock_num_port1.set_last_read_value(-8)
        await history.save_sample(mock_num_port1, (dummy_timestamp - 8000) * 1000)
        mock_num_port1.set_last_read_value(-2)
        await history.save_sample(mock_num_port1, (dummy_timestamp - 2000) * 1000)
        mock_num_port1.set_last_read_value(0.01)

        with pytest.raises(PortValueUnavailable):
            await expr.eval(dummy_eval_context)

        mock_num_port1.set_last_read_value(-6)
        await history.save_sample(mock_num_port1, (dummy_timestamp - 6000) * 1000)
        assert await expr.eval(dummy_eval_context) == -6

        mock_num_port1.set_last_read_value(-4)
        await history.save_sample(mock_num_port1, (dummy_timestamp - 4000) * 1000)
        diff_expr.set_value(-3601)  # invalidates history expression internal cache
        assert await expr.eval(dummy_eval_context) == -4

    async def test_older_future(
        self, freezer, mock_persist_driver, dummy_utc_datetime, dummy_timestamp, mock_num_port1, dummy_eval_context
    ):
        freezer.move_to(dummy_utc_datetime)
        mock_persist_driver.enable_samples_support()

        port_expr = MockPortRef(mock_num_port1)
        ts_expr = MockExpression(dummy_timestamp + 7200)
        diff_expr = MockExpression(-3600)

        expr = various.HistoryFunction([port_expr, ts_expr, diff_expr], Role.VALUE)

        mock_num_port1.set_last_read_value(-8)
        await history.save_sample(mock_num_port1, (dummy_timestamp - 8000) * 1000)

        mock_num_port1.set_last_read_value(0.01)
        assert await expr.eval(dummy_eval_context) == 0.01

    async def test_older_current(
        self, freezer, mock_persist_driver, dummy_utc_datetime, dummy_timestamp, mock_num_port1, dummy_eval_context
    ):
        freezer.move_to(dummy_utc_datetime)
        mock_persist_driver.enable_samples_support()

        port_expr = MockPortRef(mock_num_port1)
        ts_expr = MockExpression(dummy_timestamp + 1800)
        diff_expr = MockExpression(-3600)

        expr = various.HistoryFunction([port_expr, ts_expr, diff_expr], Role.VALUE)

        mock_num_port1.set_last_read_value(-2)
        await history.save_sample(mock_num_port1, (dummy_timestamp - 2000) * 1000)
        mock_num_port1.set_last_read_value(-1)
        await history.save_sample(mock_num_port1, (dummy_timestamp - 1000) * 1000)

        mock_num_port1.set_last_read_value(0.01)
        assert await expr.eval(dummy_eval_context) == 0.01

    async def test_newer_past(
        self, freezer, mock_persist_driver, dummy_utc_datetime, dummy_timestamp, mock_num_port1, dummy_eval_context
    ):
        freezer.move_to(dummy_utc_datetime)
        mock_persist_driver.enable_samples_support()

        port_expr = MockPortRef(mock_num_port1)
        ts_expr = MockExpression(dummy_timestamp - 7200)
        diff_expr = MockExpression(3600)

        expr = various.HistoryFunction([port_expr, ts_expr, diff_expr], Role.VALUE)

        mock_num_port1.set_last_read_value(-8)
        await history.save_sample(mock_num_port1, (dummy_timestamp - 8000) * 1000)
        mock_num_port1.set_last_read_value(-2)
        await history.save_sample(mock_num_port1, (dummy_timestamp - 2000) * 1000)
        mock_num_port1.set_last_read_value(0.01)

        with pytest.raises(PortValueUnavailable):
            await expr.eval(dummy_eval_context)

        mock_num_port1.set_last_read_value(-4)
        await history.save_sample(mock_num_port1, (dummy_timestamp - 4000) * 1000)
        assert await expr.eval(dummy_eval_context) == -4

        mock_num_port1.set_last_read_value(-6)
        await history.save_sample(mock_num_port1, (dummy_timestamp - 6000) * 1000)
        diff_expr.set_value(3601)  # invalidates history expression internal cache
        assert await expr.eval(dummy_eval_context) == -6

    async def test_newer_future(
        self, freezer, mock_persist_driver, dummy_utc_datetime, dummy_timestamp, mock_num_port1, dummy_eval_context
    ):
        freezer.move_to(dummy_utc_datetime)
        mock_persist_driver.enable_samples_support()

        port_expr = MockPortRef(mock_num_port1)
        ts_expr = MockExpression(dummy_timestamp + 3600)
        diff_expr = MockExpression(3600)

        expr = various.HistoryFunction([port_expr, ts_expr, diff_expr], Role.VALUE)

        mock_num_port1.set_last_read_value(-8)
        await history.save_sample(mock_num_port1, (dummy_timestamp - 8000) * 1000)

        mock_num_port1.set_last_read_value(0.01)
        with pytest.raises(PortValueUnavailable):
            await expr.eval(dummy_eval_context)

    async def test_newer_current(
        self, freezer, mock_persist_driver, dummy_utc_datetime, dummy_timestamp, mock_num_port1, dummy_eval_context
    ):
        freezer.move_to(dummy_utc_datetime)
        mock_persist_driver.enable_samples_support()

        port_expr = MockPortRef(mock_num_port1)
        ts_expr = MockExpression(dummy_timestamp - 1800)
        diff_expr = MockExpression(3600)

        expr = various.HistoryFunction([port_expr, ts_expr, diff_expr], Role.VALUE)

        mock_num_port1.set_last_read_value(-2)
        await history.save_sample(mock_num_port1, (dummy_timestamp - 2000) * 1000)
        mock_num_port1.set_last_read_value(-1)
        await history.save_sample(mock_num_port1, (dummy_timestamp - 1000) * 1000)

        mock_num_port1.set_last_read_value(0.01)
        assert await expr.eval(dummy_eval_context) == -1

    async def test_newer_unlimited_past(
        self, freezer, mock_persist_driver, dummy_utc_datetime, dummy_timestamp, mock_num_port1, dummy_eval_context
    ):
        freezer.move_to(dummy_utc_datetime)
        mock_persist_driver.enable_samples_support()

        port_expr = MockPortRef(mock_num_port1)
        ts_expr = MockExpression(dummy_timestamp - 7200)
        diff_expr = MockExpression(0)

        expr = various.HistoryFunction([port_expr, ts_expr, diff_expr], Role.VALUE)

        mock_num_port1.set_last_read_value(-8)
        await history.save_sample(mock_num_port1, (dummy_timestamp - 8000) * 1000)

        mock_num_port1.set_last_read_value(0.01)
        assert await expr.eval(dummy_eval_context) == 0.01

        mock_num_port1.set_last_read_value(-4)
        await history.save_sample(mock_num_port1, (dummy_timestamp - 4000) * 1000)
        assert await expr.eval(dummy_eval_context) == -4

        mock_num_port1.set_last_read_value(-6)
        await history.save_sample(mock_num_port1, (dummy_timestamp - 6000) * 1000)
        diff_expr.set_value(3601)  # invalidates history expression internal cache
        assert await expr.eval(dummy_eval_context) == -6

    async def test_newer_unlimited_future(
        self, freezer, mock_persist_driver, dummy_utc_datetime, dummy_timestamp, mock_num_port1, dummy_eval_context
    ):
        freezer.move_to(dummy_utc_datetime)
        mock_persist_driver.enable_samples_support()

        port_expr = MockPortRef(mock_num_port1)
        ts_expr = MockExpression(dummy_timestamp + 7200)
        diff_expr = MockExpression(0)

        expr = various.HistoryFunction([port_expr, ts_expr, diff_expr], Role.VALUE)

        mock_num_port1.set_last_read_value(-8)
        await history.save_sample(mock_num_port1, (dummy_timestamp - 8000) * 1000)

        mock_num_port1.set_last_read_value(0.01)
        with pytest.raises(PortValueUnavailable):
            await expr.eval(dummy_eval_context)

    def test_parse(self, mock_persist_driver):
        mock_persist_driver.enable_samples_support()

        e = Function.parse(None, "HISTORY(@some_id, 1, 2)", Role.VALUE, 0)
        assert isinstance(e, various.HistoryFunction)

    def test_arg_type(self, mock_persist_driver):
        mock_persist_driver.enable_samples_support()

        with pytest.raises(InvalidArgumentKind) as exc_info:
            Function.parse(None, "HISTORY(1, 2, 3)", Role.VALUE, 0)

        assert exc_info.value.name == "HISTORY"
        assert exc_info.value.num == 1
        assert exc_info.value.pos == 9

    def test_num_args(self, mock_persist_driver):
        mock_persist_driver.enable_samples_support()

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "HISTORY(@some_id, 1)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "HISTORY(@some_id, 1, 2, 3)", Role.VALUE, 0)

    @pytest.mark.parametrize("role", [Role.TRANSFORM_READ, Role.TRANSFORM_WRITE])
    def test_no_transform(self, role):
        with pytest.raises(UnknownFunction):
            Function.parse(None, "HISTORY(@some_id, 1, 2)", role, 0)

    def test_deps(self):
        assert various.HistoryFunction.DEPS == {DEP_SECOND}

    async def test_real_date_time_unavailable(
        self, mocker, mock_persist_driver, dummy_local_datetime, mock_num_port1, dummy_eval_context
    ):
        port_expr = MockPortRef(mock_num_port1)
        ts_expr = MockExpression()
        diff_expr = MockExpression()
        mocker.patch("qtoggleserver.system.date.has_real_date_time", return_value=False)
        with pytest.raises(RealDateTimeUnavailable):
            await various.HistoryFunction([port_expr, ts_expr, diff_expr], Role.VALUE).eval(dummy_eval_context)
