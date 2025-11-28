from datetime import datetime

import pytest

from qtoggleserver.core.expressions import Function, Role, date, literalvalues
from qtoggleserver.core.expressions.exceptions import InvalidNumberOfArguments, UnknownFunction


class TestYear:
    async def test_year_simple(self, dummy_local_datetime, dummy_eval_context):
        result = await date.YearFunction([], role=Role.VALUE).eval(dummy_eval_context)
        assert result == dummy_local_datetime.year

    async def test_year_argument(self, dummy_local_datetime, literal_dummy_timestamp, dummy_eval_context):
        result = await date.YearFunction([literal_dummy_timestamp], role=Role.VALUE).eval(dummy_eval_context)
        assert result == dummy_local_datetime.year

    def test_year_parse(self):
        e = Function.parse(None, "YEAR()", Role.VALUE, 0)
        assert isinstance(e, date.YearFunction)

    def test_year_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "YEAR(1, 2)", Role.VALUE, 0)

    @pytest.mark.parametrize("role", [Role.TRANSFORM_READ, Role.TRANSFORM_WRITE])
    def test_year_no_transform(self, role):
        with pytest.raises(UnknownFunction):
            Function.parse(None, "YEAR()", role, 0)


class TestMonth:
    async def test_month_simple(self, dummy_local_datetime, dummy_eval_context):
        result = await date.MonthFunction([], role=Role.VALUE).eval(dummy_eval_context)
        assert result == dummy_local_datetime.month

    async def test_month_argument(self, dummy_local_datetime, literal_dummy_timestamp, dummy_eval_context):
        result = await date.MonthFunction([literal_dummy_timestamp], role=Role.VALUE).eval(dummy_eval_context)
        assert result == dummy_local_datetime.month

    def test_month_parse(self):
        e = Function.parse(None, "MONTH()", Role.VALUE, 0)
        assert isinstance(e, date.MonthFunction)

    def test_month_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "MONTH(1, 2)", Role.VALUE, 0)

    @pytest.mark.parametrize("role", [Role.TRANSFORM_READ, Role.TRANSFORM_WRITE])
    def test_month_no_transform(self, role):
        with pytest.raises(UnknownFunction):
            Function.parse(None, "MONTH()", role, 0)


class TestDay:
    async def test_day_simple(self, dummy_local_datetime, dummy_eval_context):
        result = await date.DayFunction([], role=Role.VALUE).eval(dummy_eval_context)
        assert result == dummy_local_datetime.day

    async def test_day_argument(self, dummy_local_datetime, literal_dummy_timestamp, dummy_eval_context):
        result = await date.DayFunction([literal_dummy_timestamp], role=Role.VALUE).eval(dummy_eval_context)
        assert result == dummy_local_datetime.day

    def test_day_parse(self):
        e = Function.parse(None, "DAY()", Role.VALUE, 0)
        assert isinstance(e, date.DayFunction)

    def test_day_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "DAY(1, 2)", Role.VALUE, 0)

    @pytest.mark.parametrize("role", [Role.TRANSFORM_READ, Role.TRANSFORM_WRITE])
    def test_day_no_transform(self, role):
        with pytest.raises(UnknownFunction):
            Function.parse(None, "DAY()", role, 0)


class TestDOW:
    async def test_dow_simple(self, dummy_local_datetime, dummy_eval_context):
        result = await date.DOWFunction([], role=Role.VALUE).eval(dummy_eval_context)
        assert result == dummy_local_datetime.weekday()

    async def test_dow_argument(self, dummy_local_datetime, literal_dummy_timestamp, dummy_eval_context):
        result = await date.DOWFunction([literal_dummy_timestamp], role=Role.VALUE).eval(dummy_eval_context)
        assert result == dummy_local_datetime.weekday()

    def test_dow_parse(self):
        e = Function.parse(None, "DOW()", Role.VALUE, 0)
        assert isinstance(e, date.DOWFunction)

    def test_dow_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "DOW(1, 2)", Role.VALUE, 0)

    @pytest.mark.parametrize("role", [Role.TRANSFORM_READ, Role.TRANSFORM_WRITE])
    def test_dow_no_transform(self, role):
        with pytest.raises(UnknownFunction):
            Function.parse(None, "DOW()", role, 0)


class TestLDOM:
    async def test_ldom_simple(self, dummy_local_datetime, dummy_eval_context):
        result = await date.LDOMFunction([], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 31

    async def test_ldom_argument(self, dummy_local_datetime, literal_dummy_timestamp, dummy_eval_context):
        result = await date.LDOMFunction([literal_dummy_timestamp], role=Role.VALUE).eval(dummy_eval_context)
        assert result == 31

    def test_ldom_parse(self):
        e = Function.parse(None, "LDOM()", Role.VALUE, 0)
        assert isinstance(e, date.LDOMFunction)

    def test_ldom_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "LDOM(1, 2)", Role.VALUE, 0)

    @pytest.mark.parametrize("role", [Role.TRANSFORM_READ, Role.TRANSFORM_WRITE])
    def test_ldom_no_transform(self, role):
        with pytest.raises(UnknownFunction):
            Function.parse(None, "LDOM()", role, 0)


class TestHour:
    async def test_hour_simple(self, dummy_local_datetime, dummy_eval_context):
        result = await date.HourFunction([], role=Role.VALUE).eval(dummy_eval_context)
        assert result == dummy_local_datetime.hour

    async def test_hour_argument(self, dummy_local_datetime, literal_dummy_timestamp, dummy_eval_context):
        result = await date.HourFunction([literal_dummy_timestamp], role=Role.VALUE).eval(dummy_eval_context)
        assert result == dummy_local_datetime.hour

    def test_hour_parse(self):
        e = Function.parse(None, "HOUR()", Role.VALUE, 0)
        assert isinstance(e, date.HourFunction)

    def test_hour_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "HOUR(1, 2)", Role.VALUE, 0)

    @pytest.mark.parametrize("role", [Role.TRANSFORM_READ, Role.TRANSFORM_WRITE])
    def test_hour_no_transform(self, role):
        with pytest.raises(UnknownFunction):
            Function.parse(None, "HOUR()", role, 0)


class TestMinute:
    async def test_minute_simple(self, dummy_local_datetime, dummy_eval_context):
        result = await date.MinuteFunction([], role=Role.VALUE).eval(dummy_eval_context)
        assert result == dummy_local_datetime.minute

    async def test_minute_argument(self, dummy_local_datetime, literal_dummy_timestamp, dummy_eval_context):
        result = await date.MinuteFunction([literal_dummy_timestamp], role=Role.VALUE).eval(dummy_eval_context)
        assert result == dummy_local_datetime.minute

    def test_minute_parse(self):
        e = Function.parse(None, "MINUTE()", Role.VALUE, 0)
        assert isinstance(e, date.MinuteFunction)

    def test_minute_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "MINUTE(1, 2)", Role.VALUE, 0)

    @pytest.mark.parametrize("role", [Role.TRANSFORM_READ, Role.TRANSFORM_WRITE])
    def test_minute_no_transform(self, role):
        with pytest.raises(UnknownFunction):
            Function.parse(None, "MINUTE()", role, 0)


class TestSecond:
    async def test_second_simple(self, dummy_local_datetime, dummy_eval_context):
        result = await date.SecondFunction([], role=Role.VALUE).eval(dummy_eval_context)
        assert result == dummy_local_datetime.second

    async def test_second_argument(self, dummy_local_datetime, literal_dummy_timestamp, dummy_eval_context):
        result = await date.SecondFunction([literal_dummy_timestamp], role=Role.VALUE).eval(dummy_eval_context)
        assert result == dummy_local_datetime.second

    def test_second_parse(self):
        e = Function.parse(None, "SECOND()", Role.VALUE, 0)
        assert isinstance(e, date.SecondFunction)

    def test_second_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "SECOND(1, 2)", Role.VALUE, 0)

    @pytest.mark.parametrize("role", [Role.TRANSFORM_READ, Role.TRANSFORM_WRITE])
    def test_second_no_transform(self, role):
        with pytest.raises(UnknownFunction):
            Function.parse(None, "SECOND()", role, 0)


class TestMillisecond:
    async def test_millisecond(self, dummy_local_datetime, dummy_eval_context):
        result = await date.MillisecondFunction([], role=Role.VALUE).eval(dummy_eval_context)
        assert result == dummy_local_datetime.microsecond // 1000

    def test_millisecond_parse(self):
        e = Function.parse(None, "MILLISECOND()", Role.VALUE, 0)
        assert isinstance(e, date.MillisecondFunction)

    def test_millisecond_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "MILLISECOND(1)", Role.VALUE, 0)

    @pytest.mark.parametrize("role", [Role.TRANSFORM_READ, Role.TRANSFORM_WRITE])
    def test_millisecond_no_transform(self, role):
        with pytest.raises(UnknownFunction):
            Function.parse(None, "MILLISECOND()", role, 0)


class TestMinuteOfDay:
    async def test_minute_of_day_simple(self, dummy_local_datetime, dummy_eval_context):
        result = await date.MinuteOfDayFunction([], role=Role.VALUE).eval(dummy_eval_context)
        assert result == dummy_local_datetime.hour * 60 + dummy_local_datetime.minute

    async def test_minute_of_day_argument(self, dummy_local_datetime, literal_dummy_timestamp, dummy_eval_context):
        result = await date.MinuteOfDayFunction([literal_dummy_timestamp], role=Role.VALUE).eval(dummy_eval_context)
        assert result == dummy_local_datetime.hour * 60 + dummy_local_datetime.minute

    def test_minute_of_day_parse(self):
        e = Function.parse(None, "MINUTEOFDAY()", Role.VALUE, 0)
        assert isinstance(e, date.MinuteOfDayFunction)

    def test_minute_of_day_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "MINUTEOFDAY(1, 2)", Role.VALUE, 0)

    @pytest.mark.parametrize("role", [Role.TRANSFORM_READ, Role.TRANSFORM_WRITE])
    def test_minute_of_day_no_transform(self, role):
        with pytest.raises(UnknownFunction):
            Function.parse(None, "MINUTEOFDAY()", role, 0)


class TestSecondOfDay:
    async def test_second_of_day_simple(self, dummy_local_datetime, dummy_eval_context):
        result = await date.SecondOfDayFunction([], role=Role.VALUE).eval(dummy_eval_context)
        assert (
            result == dummy_local_datetime.hour * 3600 + dummy_local_datetime.minute * 60 + dummy_local_datetime.second
        )

    async def test_second_of_day_argument(self, dummy_local_datetime, literal_dummy_timestamp, dummy_eval_context):
        result = await date.SecondOfDayFunction([literal_dummy_timestamp], role=Role.VALUE).eval(dummy_eval_context)
        assert (
            result == dummy_local_datetime.hour * 3600 + dummy_local_datetime.minute * 60 + dummy_local_datetime.second
        )

    def test_second_of_day_parse(self):
        e = Function.parse(None, "SECONDOFDAY()", Role.VALUE, 0)
        assert isinstance(e, date.SecondOfDayFunction)

    def test_second_of_day_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "SECONDOFDAY(1, 2)", Role.VALUE, 0)

    @pytest.mark.parametrize("role", [Role.TRANSFORM_READ, Role.TRANSFORM_WRITE])
    def test_second_of_day_no_transform(self, role):
        with pytest.raises(UnknownFunction):
            Function.parse(None, "SECONDOFDAY()", role, 0)


class TestDate:
    async def test_date(self, dummy_local_datetime, dummy_timestamp, dummy_eval_context):
        result = await date.DateFunction(
            [
                literalvalues.LiteralValue(dummy_local_datetime.year, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.month, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.day, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.hour, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.minute, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.second, "", Role.VALUE),
            ],
            role=Role.VALUE,
        ).eval(dummy_eval_context)
        assert result == int(dummy_timestamp)

    def test_date_parse(self):
        e = Function.parse(None, "DATE(2019, 3, 14, 1, 2, 3)", Role.VALUE, 0)
        assert isinstance(e, date.DateFunction)

    def test_date_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "DATE(2019, 3, 14, 1, 2)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "DATE(2019, 3, 14, 1, 2, 3, 4)", Role.VALUE, 0)


class TestBOY:
    async def test_boy_simple(self, dummy_local_datetime, local_tz_info, dummy_eval_context):
        result = await date.BOYFunction([], role=Role.VALUE).eval(dummy_eval_context)

        dt = dummy_local_datetime.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        dt = dt.astimezone(local_tz_info)
        assert result == dt.timestamp()

    async def test_boy_negative(self, dummy_local_datetime, dummy_timestamp, local_tz_info, dummy_eval_context):
        result = await date.BOYFunction([literalvalues.LiteralValue(-30, "", Role.VALUE)], role=Role.VALUE).eval(
            dummy_eval_context
        )

        dt = dummy_local_datetime.replace(
            year=dummy_local_datetime.year - 30, month=1, day=1, hour=0, minute=0, second=0, microsecond=0
        )
        dt = dt.astimezone(local_tz_info)
        assert result == dt.timestamp()

    async def test_boy_positive(self, dummy_local_datetime, dummy_timestamp, local_tz_info, dummy_eval_context):
        result = await date.BOYFunction([literalvalues.LiteralValue(100, "", Role.VALUE)], role=Role.VALUE).eval(
            dummy_eval_context
        )

        dt = dummy_local_datetime.replace(
            year=dummy_local_datetime.year + 100, month=1, day=1, hour=0, minute=0, second=0, microsecond=0
        )
        dt = dt.astimezone(local_tz_info)
        assert result == dt.timestamp()

    def test_boy_parse(self):
        e = Function.parse(None, "BOY()", Role.VALUE, 0)
        assert isinstance(e, date.BOYFunction)

    def test_boy_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "BOY(1, 2)", Role.VALUE, 0)

    @pytest.mark.parametrize("role", [Role.TRANSFORM_READ, Role.TRANSFORM_WRITE])
    def test_boy_no_transform(self, role):
        with pytest.raises(UnknownFunction):
            Function.parse(None, "BOY()", role, 0)


class TestBOM:
    async def test_bom_simple(self, dummy_local_datetime, local_tz_info, dummy_eval_context):
        result = await date.BOMFunction([], role=Role.VALUE).eval(dummy_eval_context)

        dt = dummy_local_datetime.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        dt = dt.astimezone(local_tz_info)
        assert result == dt.timestamp()

    async def test_bom_negative(self, dummy_local_datetime, dummy_timestamp, local_tz_info, dummy_eval_context):
        result = await date.BOMFunction([literalvalues.LiteralValue(-13, "", Role.VALUE)], role=Role.VALUE).eval(
            dummy_eval_context
        )

        dt = dummy_local_datetime.replace(
            year=dummy_local_datetime.year - 1,
            month=dummy_local_datetime.month - 1,
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        dt = dt.astimezone(local_tz_info)
        assert result == dt.timestamp()

    async def test_bom_positive(self, dummy_local_datetime, dummy_timestamp, local_tz_info, dummy_eval_context):
        result = await date.BOMFunction([literalvalues.LiteralValue(13, "", Role.VALUE)], role=Role.VALUE).eval(
            dummy_eval_context
        )

        dt = dummy_local_datetime.replace(
            year=dummy_local_datetime.year + 1,
            month=dummy_local_datetime.month + 1,
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        dt = dt.astimezone(local_tz_info)
        assert result == dt.timestamp()

    def test_bom_parse(self):
        e = Function.parse(None, "BOM()", Role.VALUE, 0)
        assert isinstance(e, date.BOMFunction)

    def test_bom_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "BOM(1, 2)", Role.VALUE, 0)

    @pytest.mark.parametrize("role", [Role.TRANSFORM_READ, Role.TRANSFORM_WRITE])
    def test_bom_no_transform(self, role):
        with pytest.raises(UnknownFunction):
            Function.parse(None, "BOM()", role, 0)


class TestBOW:
    async def test_bow_simple(self, dummy_local_datetime, local_tz_info, dummy_eval_context):
        result = await date.BOWFunction([], role=Role.VALUE).eval(dummy_eval_context)

        dt = dummy_local_datetime.replace(
            day=dummy_local_datetime.day - dummy_local_datetime.weekday(), hour=0, minute=0, second=0, microsecond=0
        )
        dt = dt.astimezone(local_tz_info)
        assert result == dt.timestamp()

    async def test_bow_negative(self, dummy_local_datetime, local_tz_info, dummy_eval_context):
        result = await date.BOWFunction([literalvalues.LiteralValue(-54, "", Role.VALUE)], role=Role.VALUE).eval(
            dummy_eval_context
        )

        dt = datetime(2018, 2, 26, 0, 0, 0)
        dt = dt.astimezone(local_tz_info)
        assert result == dt.timestamp()

    async def test_bow_positive(self, dummy_local_datetime, local_tz_info, dummy_eval_context):
        result = await date.BOWFunction([literalvalues.LiteralValue(54, "", Role.VALUE)], role=Role.VALUE).eval(
            dummy_eval_context
        )

        dt = datetime(2020, 3, 23, 0, 0, 0)
        dt = dt.astimezone(local_tz_info)
        assert result == dt.timestamp()

    async def test_bow_sunday(self, dummy_local_datetime, literal_zero, local_tz_info, dummy_eval_context):
        result = await date.BOWFunction(
            [literal_zero, literalvalues.LiteralValue(6, "", Role.VALUE)], role=Role.VALUE
        ).eval(dummy_eval_context)

        dt = dummy_local_datetime.replace(
            day=dummy_local_datetime.day - dummy_local_datetime.weekday() - 1, hour=0, minute=0, second=0, microsecond=0
        )
        dt = dt.astimezone(local_tz_info)
        assert result == dt.timestamp()

    async def test_bow_sunday_negative(self, dummy_local_datetime, local_tz_info, dummy_eval_context):
        result = await date.BOWFunction(
            [literalvalues.LiteralValue(-54, "", Role.VALUE), literalvalues.LiteralValue(6, "", Role.VALUE)],
            role=Role.VALUE,
        ).eval(dummy_eval_context)

        dt = datetime(2018, 2, 25, 0, 0, 0)
        dt = dt.astimezone(local_tz_info)
        assert result == dt.timestamp()

    async def test_bow_sunday_positive(self, dummy_local_datetime, local_tz_info, dummy_eval_context):
        result = await date.BOWFunction(
            [literalvalues.LiteralValue(54, "", Role.VALUE), literalvalues.LiteralValue(6, "", Role.VALUE)],
            role=Role.VALUE,
        ).eval(dummy_eval_context)

        dt = datetime(2020, 3, 22, 0, 0, 0)
        dt = dt.astimezone(local_tz_info)
        assert result == dt.timestamp()

    def test_bow_parse(self):
        e = Function.parse(None, "BOW()", Role.VALUE, 0)
        assert isinstance(e, date.BOWFunction)

    def test_bow_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "BOW(1, 2, 3)", Role.VALUE, 0)

    @pytest.mark.parametrize("role", [Role.TRANSFORM_READ, Role.TRANSFORM_WRITE])
    def test_bow_no_transform(self, role):
        with pytest.raises(UnknownFunction):
            Function.parse(None, "BOW()", role, 0)


class TestHMSInterval:
    async def test_hmsinterval_hours(self, dummy_local_datetime, dummy_eval_context):
        result = await date.HMSIntervalFunction(
            [
                literalvalues.LiteralValue(dummy_local_datetime.hour - 1, "", Role.VALUE),
                literalvalues.LiteralValue(0, "", Role.VALUE),
                literalvalues.LiteralValue(0, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.hour + 1, "", Role.VALUE),
                literalvalues.LiteralValue(0, "", Role.VALUE),
                literalvalues.LiteralValue(0, "", Role.VALUE),
            ],
            role=Role.VALUE,
        ).eval(dummy_eval_context)
        assert result == 1

        result = await date.HMSIntervalFunction(
            [
                literalvalues.LiteralValue(dummy_local_datetime.hour - 2, "", Role.VALUE),
                literalvalues.LiteralValue(0, "", Role.VALUE),
                literalvalues.LiteralValue(0, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.hour - 1, "", Role.VALUE),
                literalvalues.LiteralValue(0, "", Role.VALUE),
                literalvalues.LiteralValue(0, "", Role.VALUE),
            ],
            role=Role.VALUE,
        ).eval(dummy_eval_context)
        assert result == 0

        result = await date.HMSIntervalFunction(
            [
                literalvalues.LiteralValue(dummy_local_datetime.hour + 1, "", Role.VALUE),
                literalvalues.LiteralValue(0, "", Role.VALUE),
                literalvalues.LiteralValue(0, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.hour + 2, "", Role.VALUE),
                literalvalues.LiteralValue(0, "", Role.VALUE),
                literalvalues.LiteralValue(0, "", Role.VALUE),
            ],
            role=Role.VALUE,
        ).eval(dummy_eval_context)
        assert result == 0

    async def test_hmsinterval_minutes(self, dummy_local_datetime, dummy_eval_context):
        result = await date.HMSIntervalFunction(
            [
                literalvalues.LiteralValue(dummy_local_datetime.hour, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.minute - 1, "", Role.VALUE),
                literalvalues.LiteralValue(0, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.hour, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.minute + 1, "", Role.VALUE),
                literalvalues.LiteralValue(0, "", Role.VALUE),
            ],
            role=Role.VALUE,
        ).eval(dummy_eval_context)
        assert result == 1

        result = await date.HMSIntervalFunction(
            [
                literalvalues.LiteralValue(dummy_local_datetime.hour, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.minute - 2, "", Role.VALUE),
                literalvalues.LiteralValue(0, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.hour, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.minute - 1, "", Role.VALUE),
                literalvalues.LiteralValue(0, "", Role.VALUE),
            ],
            role=Role.VALUE,
        ).eval(dummy_eval_context)
        assert result == 0

        result = await date.HMSIntervalFunction(
            [
                literalvalues.LiteralValue(dummy_local_datetime.hour, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.minute + 1, "", Role.VALUE),
                literalvalues.LiteralValue(0, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.hour, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.minute + 2, "", Role.VALUE),
                literalvalues.LiteralValue(0, "", Role.VALUE),
            ],
            role=Role.VALUE,
        ).eval(dummy_eval_context)
        assert result == 0

    async def test_hmsinterval_seconds(self, dummy_local_datetime, dummy_eval_context):
        result = await date.HMSIntervalFunction(
            [
                literalvalues.LiteralValue(dummy_local_datetime.hour, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.minute, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.second - 1, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.hour, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.minute, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.second + 1, "", Role.VALUE),
            ],
            role=Role.VALUE,
        ).eval(dummy_eval_context)
        assert result == 1

        result = await date.HMSIntervalFunction(
            [
                literalvalues.LiteralValue(dummy_local_datetime.hour, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.minute, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.second - 2, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.hour, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.minute, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.second - 1, "", Role.VALUE),
            ],
            role=Role.VALUE,
        ).eval(dummy_eval_context)
        assert result == 0

        result = await date.HMSIntervalFunction(
            [
                literalvalues.LiteralValue(dummy_local_datetime.hour, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.minute, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.second + 1, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.hour, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.minute, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.second + 2, "", Role.VALUE),
            ],
            role=Role.VALUE,
        ).eval(dummy_eval_context)
        assert result == 0

    async def test_hmsinterval_limit(self, dummy_local_datetime, dummy_eval_context):
        result = await date.HMSIntervalFunction(
            [
                literalvalues.LiteralValue(dummy_local_datetime.hour, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.minute, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.second, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.hour, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.minute, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.second + 1, "", Role.VALUE),
            ],
            role=Role.VALUE,
        ).eval(dummy_eval_context)
        assert result == 1

        result = await date.HMSIntervalFunction(
            [
                literalvalues.LiteralValue(dummy_local_datetime.hour, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.minute, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.second - 1, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.hour, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.minute, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.second, "", Role.VALUE),
            ],
            role=Role.VALUE,
        ).eval(dummy_eval_context)
        assert result == 1

    async def test_hmsinterval_reversed(self, dummy_local_datetime, dummy_eval_context):
        result = await date.HMSIntervalFunction(
            [
                literalvalues.LiteralValue(dummy_local_datetime.hour + 1, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.minute, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.second, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.hour - 1, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.minute, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.second, "", Role.VALUE),
            ],
            role=Role.VALUE,
        ).eval(dummy_eval_context)
        assert result == 0

    def test_hmsinterval_parse(self):
        e = Function.parse(None, "HMSINTERVAL(1, 1, 1, 2, 2, 2)", Role.VALUE, 0)
        assert isinstance(e, date.HMSIntervalFunction)

    def test_hmsinterval_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "HMSINTERVAL(1, 2, 3, 4, 5)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "HMSINTERVAL(1, 2, 3, 4, 5, 6, 7)", Role.VALUE, 0)

    @pytest.mark.parametrize("role", [Role.TRANSFORM_READ, Role.TRANSFORM_WRITE])
    def test_hmsinterval_no_transform(self, role):
        with pytest.raises(UnknownFunction):
            Function.parse(None, "HMSINTERVAL(1, 1, 1, 2, 2, 2)", role, 0)


class TestMDInterval:
    async def test_mdinterval_months(self, dummy_local_datetime, dummy_eval_context):
        result = await date.MDIntervalFunction(
            [
                literalvalues.LiteralValue(dummy_local_datetime.month - 1, "", Role.VALUE),
                literalvalues.LiteralValue(1, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.month + 1, "", Role.VALUE),
                literalvalues.LiteralValue(1, "", Role.VALUE),
            ],
            role=Role.VALUE,
        ).eval(dummy_eval_context)
        assert result == 1

        result = await date.MDIntervalFunction(
            [
                literalvalues.LiteralValue(dummy_local_datetime.month - 2, "", Role.VALUE),
                literalvalues.LiteralValue(1, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.month - 1, "", Role.VALUE),
                literalvalues.LiteralValue(1, "", Role.VALUE),
            ],
            role=Role.VALUE,
        ).eval(dummy_eval_context)
        assert result == 0

        result = await date.MDIntervalFunction(
            [
                literalvalues.LiteralValue(dummy_local_datetime.month + 1, "", Role.VALUE),
                literalvalues.LiteralValue(1, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.month + 2, "", Role.VALUE),
                literalvalues.LiteralValue(1, "", Role.VALUE),
            ],
            role=Role.VALUE,
        ).eval(dummy_eval_context)
        assert result == 0

    async def test_mdinterval_days(self, dummy_local_datetime, dummy_eval_context):
        result = await date.MDIntervalFunction(
            [
                literalvalues.LiteralValue(dummy_local_datetime.month, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.day - 1, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.month, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.day + 1, "", Role.VALUE),
            ],
            role=Role.VALUE,
        ).eval(dummy_eval_context)
        assert result == 1

        result = await date.MDIntervalFunction(
            [
                literalvalues.LiteralValue(dummy_local_datetime.month, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.day - 2, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.month, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.day - 1, "", Role.VALUE),
            ],
            role=Role.VALUE,
        ).eval(dummy_eval_context)
        assert result == 0

        result = await date.MDIntervalFunction(
            [
                literalvalues.LiteralValue(dummy_local_datetime.month, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.day + 1, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.month, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.day + 2, "", Role.VALUE),
            ],
            role=Role.VALUE,
        ).eval(dummy_eval_context)
        assert result == 0

    async def test_mdinterval_limit(self, dummy_local_datetime, dummy_eval_context):
        result = await date.MDIntervalFunction(
            [
                literalvalues.LiteralValue(dummy_local_datetime.month, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.day, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.month, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.day + 1, "", Role.VALUE),
            ],
            role=Role.VALUE,
        ).eval(dummy_eval_context)
        assert result == 1

        result = await date.MDIntervalFunction(
            [
                literalvalues.LiteralValue(dummy_local_datetime.month, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.day - 1, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.month, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.day, "", Role.VALUE),
            ],
            role=Role.VALUE,
        ).eval(dummy_eval_context)
        assert result == 1

    async def test_mdinterval_reversed(self, dummy_local_datetime, dummy_eval_context):
        result = await date.MDIntervalFunction(
            [
                literalvalues.LiteralValue(dummy_local_datetime.month + 1, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.day, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.month - 1, "", Role.VALUE),
                literalvalues.LiteralValue(dummy_local_datetime.day, "", Role.VALUE),
            ],
            role=Role.VALUE,
        ).eval(dummy_eval_context)
        assert result == 0

    def test_mdinterval_parse(self):
        e = Function.parse(None, "MDINTERVAL(1, 1, 2, 2)", Role.VALUE, 0)
        assert isinstance(e, date.MDIntervalFunction)

    def test_mdinterval_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "MDINTERVAL(1, 2, 3)", Role.VALUE, 0)

        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "MDINTERVAL(1, 2, 3, 4, 5)", Role.VALUE, 0)

    @pytest.mark.parametrize("role", [Role.TRANSFORM_READ, Role.TRANSFORM_WRITE])
    def test_mdinterval_no_transform(self, role):
        with pytest.raises(UnknownFunction):
            Function.parse(None, "MDINTERVAL(1, 1, 2, 2)", role, 0)
