import pytest

from qtoggleserver.core import history
from qtoggleserver.core.expressions import DEP_ASAP, DEP_SECOND, EvalContext, Function, Role, various
from qtoggleserver.core.expressions.exceptions import (
    InvalidArgumentKind,
    InvalidNumberOfArguments,
    PortValueUnavailable,
    UnknownFunction,
)
from tests.qtoggleserver.mock.expressions import MockExpression, MockPortRef, MockPortValue


class TestAvailable:
    async def test_available_value_available(self, mock_num_port1, dummy_eval_context):
        """Should return 1 if value is available (not None)."""

        mock_expr = MockExpression(16)
        expr = various.AvailableFunction([mock_expr], Role.VALUE)
        assert await expr.eval(dummy_eval_context) == 1

        mock_expr = MockExpression(16)
        mock_expr.set_value(0)
        assert await expr.eval(dummy_eval_context) == 1

    async def test_available_value_none(self, mock_num_port1, dummy_eval_context):
        """Should return 0 if value is None."""

        mock_expr = MockExpression(None)
        expr = various.AvailableFunction([mock_expr], Role.VALUE)
        assert await expr.eval(dummy_eval_context) == 0

    async def test_available_value_unavailable(self, mock_num_port1, literal_unavailable, dummy_eval_context):
        """Should return 0 if value is unavailable."""

        expr = various.AvailableFunction([literal_unavailable], Role.VALUE)
        assert await expr.eval(dummy_eval_context) == 0

    async def test_available_func(self, mock_num_port1):
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

    def test_available_parse(self):
        e = Function.parse(None, "AVAILABLE(1)", Role.VALUE, 0)
        assert isinstance(e, various.AvailableFunction)

    def test_available_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "AVAILABLE()", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "AVAILABLE(1, 2)", Role.VALUE, 0)


class TestDefault:
    async def test_default_value_available(self, mock_num_port1, dummy_eval_context):
        """Should return value when available (not None)."""

        mock_expr = MockExpression(16)
        def_expr = MockExpression(13)
        expr = various.DefaultFunction([mock_expr, def_expr], Role.VALUE)
        assert await expr.eval(dummy_eval_context) == 16

        mock_expr.set_value(0)
        assert await expr.eval(dummy_eval_context) == 0

    async def test_default_value_none(self, mock_num_port1, dummy_eval_context):
        """Should return default value when value is None."""

        mock_expr = MockExpression(None)
        def_expr = MockExpression(13)
        expr = various.DefaultFunction([mock_expr, def_expr], Role.VALUE)
        assert await expr.eval(dummy_eval_context) == 13

    async def test_default_value_unavailable(self, mock_num_port1, literal_unavailable, dummy_eval_context):
        """Should return default value when value is unavailable."""

        def_expr = MockExpression(13)
        expr = various.DefaultFunction([literal_unavailable, def_expr], Role.VALUE)
        assert await expr.eval(dummy_eval_context) == 13

    def test_default_parse(self):
        e = Function.parse(None, "DEFAULT(1, 2)", Role.VALUE, 0)
        assert isinstance(e, various.DefaultFunction)

    def test_default_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "DEFAULT(1)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "AVAILABLE(1, 2, 3)", Role.VALUE, 0)


class TestRising:
    async def test_rising(self, mock_num_port1):
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

    def test_rising_parse(self):
        e = Function.parse(None, "RISING(1)", Role.VALUE, 0)
        assert isinstance(e, various.RisingFunction)

    def test_rising_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "RISING()", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "RISING(1, 2)", Role.VALUE, 0)


class TestFalling:
    async def test_falling(self, mock_num_port1):
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

    def test_falling_parse(self):
        e = Function.parse(None, "FALLING(1)", Role.VALUE, 0)
        assert isinstance(e, various.FallingFunction)

    def test_falling_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "FALLING()", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "FALLING(1, 2)", Role.VALUE, 0)


class TestAcc:
    async def test_acc(self, dummy_eval_context):
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

    def test_acc_parse(self):
        e = Function.parse(None, "ACC(1, 2)", Role.VALUE, 0)
        assert isinstance(e, various.AccFunction)

    def test_acc_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "ACC(1)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "ACC(1, 2, 3)", Role.VALUE, 0)


class TestAccInc:
    async def test_accinc(self, dummy_eval_context):
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

    def test_accinc_parse(self):
        e = Function.parse(None, "ACCINC(1, 2)", Role.VALUE, 0)
        assert isinstance(e, various.AccIncFunction)

    def test_accinc_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "ACCINC(1)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "ACCINC(1, 2, 3)", Role.VALUE, 0)


class TestHyst:
    async def test_hyst_rise(self, literal_three, literal_sixteen, dummy_eval_context):
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

    async def test_hyst_fall(self, literal_three, literal_sixteen, dummy_eval_context):
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

    def test_hyst_parse(self):
        e = Function.parse(None, "HYST(1, 2, 3)", Role.VALUE, 0)
        assert isinstance(e, various.HystFunction)

    def test_hyst_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "HYST(1, 2)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "HYST(1, 2, 3, 4)", Role.VALUE, 0)


class TestOnOffAuto:
    async def test_onoffauto(self, dummy_eval_context):
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

    def test_onoffauto_parse(self):
        e = Function.parse(None, "ONOFFAUTO(1, 2)", Role.VALUE, 0)
        assert isinstance(e, various.OnOffAutoFunction)

    def test_onoffauto_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "ONOFFAUTO(1)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "ONOFFAUTO(1, 2, 3)", Role.VALUE, 0)


class TestSequence:
    async def test_sequence(
        self,
        literal_two,
        literal_three,
        literal_sixteen,
        literal_one_hundred,
        literal_two_hundreds,
        dummy_eval_context,
        later_eval_context,
    ):
        expr = various.SequenceFunction(
            [
                literal_three,
                literal_one_hundred,
                literal_sixteen,
                literal_two_hundreds,
                literal_two,
                literal_one_hundred,
            ],
            Role.VALUE,
        )
        assert await expr.eval(dummy_eval_context) == 3
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms)
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 99)
        assert await expr.eval(later_eval_context(99)) == 3
        assert not expr.is_asap_eval_paused(dummy_eval_context.now_ms + 101)

        assert await expr.eval(later_eval_context(101)) == 16
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 101)
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 299)
        assert await expr.eval(later_eval_context(200)) == 16
        assert await expr.eval(later_eval_context(299)) == 16
        assert not expr.is_asap_eval_paused(dummy_eval_context.now_ms + 300)

        assert await expr.eval(later_eval_context(301)) == 2
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 301)
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 399)
        assert await expr.eval(later_eval_context(399)) == 2
        assert not expr.is_asap_eval_paused(dummy_eval_context.now_ms + 400)
        assert await expr.eval(later_eval_context(401)) == 3
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 401)
        assert expr.is_asap_eval_paused(dummy_eval_context.now_ms + 499)
        assert not expr.is_asap_eval_paused(dummy_eval_context.now_ms + 500)

    def test_sequence_parse(self):
        e = Function.parse(None, "SEQUENCE(1, 2, 3, 4)", Role.VALUE, 0)
        assert isinstance(e, various.SequenceFunction)

    def test_sequence_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "SEQUENCE(1)", Role.VALUE, 0)

    @pytest.mark.parametrize("role", [Role.TRANSFORM_READ, Role.TRANSFORM_WRITE])
    def test_sequence_no_transform(self, role):
        with pytest.raises(UnknownFunction):
            Function.parse(None, "SEQUENCE(1)", role, 0)

    def test_sequence_deps(self):
        assert various.SequenceFunction.DEPS == {DEP_ASAP}


class TestLUT:
    async def test_lut(
        self,
        literal_two,
        literal_three,
        literal_sixteen,
        literal_one_hundred,
        literal_two_hundreds,
        literal_one_thousand,
        dummy_eval_context,
    ):
        value_expr = MockExpression(0)
        expr = various.LUTFunction(
            [
                value_expr,
                literal_three,
                literal_two_hundreds,
                literal_sixteen,
                literal_one_thousand,
                literal_two,
                literal_one_hundred,
            ],
            Role.VALUE,
        )
        assert await expr.eval(dummy_eval_context) == 100

        value_expr.set_value(2)
        assert await expr.eval(dummy_eval_context) == 100

        value_expr.set_value(2.4)
        assert await expr.eval(dummy_eval_context) == 100

        value_expr.set_value(2.6)
        assert await expr.eval(dummy_eval_context) == 200

        value_expr.set_value(3)
        assert await expr.eval(dummy_eval_context) == 200

        value_expr.set_value(5)
        assert await expr.eval(dummy_eval_context) == 200

        value_expr.set_value(9.4)
        assert await expr.eval(dummy_eval_context) == 200

        value_expr.set_value(9.6)
        assert await expr.eval(dummy_eval_context) == 1000

        value_expr.set_value(100)
        assert await expr.eval(dummy_eval_context) == 1000

    def test_lut_parse(self):
        e = Function.parse(None, "LUT(1, 2, 3, 4, 5)", Role.VALUE, 0)
        assert isinstance(e, various.LUTFunction)

    def test_lut_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "LUT(1)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "LUT(1, 2)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "LUT(1, 2, 3, 4)", Role.VALUE, 0)


class TestLUTLI:
    async def test_lutli(
        self,
        literal_two,
        literal_three,
        literal_sixteen,
        literal_one_hundred,
        literal_two_hundreds,
        literal_one_thousand,
        dummy_eval_context,
    ):
        value_expr = MockExpression(0)
        expr = various.LUTLIFunction(
            [
                value_expr,
                literal_three,
                literal_two_hundreds,
                literal_sixteen,
                literal_one_thousand,
                literal_two,
                literal_one_hundred,
            ],
            Role.VALUE,
        )
        assert await expr.eval(dummy_eval_context) == 100

        value_expr.set_value(2)
        assert await expr.eval(dummy_eval_context) == 100

        value_expr.set_value(2.4)
        assert await expr.eval(dummy_eval_context) == 140

        value_expr.set_value(2.6)
        assert await expr.eval(dummy_eval_context) == 160

        value_expr.set_value(3)
        assert await expr.eval(dummy_eval_context) == 200

        value_expr.set_value(5)
        assert round(await expr.eval(dummy_eval_context), 2) == 323.08

        value_expr.set_value(9.4)
        assert round(await expr.eval(dummy_eval_context), 2) == 593.85

        value_expr.set_value(9.6)
        assert round(await expr.eval(dummy_eval_context), 2) == 606.15

        value_expr.set_value(16)
        assert round(await expr.eval(dummy_eval_context), 2) == 1000

        value_expr.set_value(100)
        assert round(await expr.eval(dummy_eval_context), 2) == 1000

    def test_lutli_parse(self):
        e = Function.parse(None, "LUTLI(1, 2, 3, 4, 5)", Role.VALUE, 0)
        assert isinstance(e, various.LUTLIFunction)

    def test_lutli_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "LUTLI(1)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "LUTLI(1, 2)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "LUTLI(1, 2, 3, 4)", Role.VALUE, 0)


class TestHistory:
    async def test_history_older_past(
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

    async def test_history_older_future(
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

    async def test_history_older_current(
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

    async def test_history_newer_past(
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

    async def test_history_newer_future(
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

    async def test_history_newer_current(
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

    async def test_history_newer_unlimited_past(
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

    async def test_history_newer_unlimited_future(
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

    def test_history_parse(self, mock_persist_driver):
        mock_persist_driver.enable_samples_support()

        e = Function.parse(None, "HISTORY(@some_id, 1, 2)", Role.VALUE, 0)
        assert isinstance(e, various.HistoryFunction)

    def test_history_arg_type(self, mock_persist_driver):
        mock_persist_driver.enable_samples_support()

        with pytest.raises(InvalidArgumentKind) as exc_info:
            Function.parse(None, "HISTORY(1, 2, 3)", Role.VALUE, 0)

        assert exc_info.value.name == "HISTORY"
        assert exc_info.value.num == 1
        assert exc_info.value.pos == 9

    def test_history_num_args(self, mock_persist_driver):
        mock_persist_driver.enable_samples_support()

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "HISTORY(@some_id, 1)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "HISTORY(@some_id, 1, 2, 3)", Role.VALUE, 0)

    @pytest.mark.parametrize("role", [Role.TRANSFORM_READ, Role.TRANSFORM_WRITE])
    def test_history_no_transform(self, role):
        with pytest.raises(UnknownFunction):
            Function.parse(None, "HISTORY(@some_id, 1, 2)", role, 0)

    def test_history_deps(self):
        assert various.HistoryFunction.DEPS == {DEP_SECOND}
