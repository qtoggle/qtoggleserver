import datetime

import pytest

from qtoggleserver.core.expressions import ROLE_VALUE, Function, InvalidNumberOfArguments, date, literalvalues


async def test_year_simple(dummy_local_datetime, dummy_eval_context):
    result = await date.YearFunction([], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == dummy_local_datetime.year


async def test_year_argument(dummy_local_datetime, literal_dummy_timestamp, dummy_eval_context):
    result = await date.YearFunction([literal_dummy_timestamp], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == dummy_local_datetime.year


def test_year_parse():
    e = Function.parse(None, 'YEAR()', ROLE_VALUE, 0)
    assert isinstance(e, date.YearFunction)


def test_year_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'YEAR(1, 2)', ROLE_VALUE, 0)


async def test_month_simple(dummy_local_datetime, dummy_eval_context):
    result = await date.MonthFunction([], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == dummy_local_datetime.month


async def test_month_argument(dummy_local_datetime, literal_dummy_timestamp, dummy_eval_context):
    result = await date.MonthFunction([literal_dummy_timestamp], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == dummy_local_datetime.month


def test_month_parse():
    e = Function.parse(None, 'MONTH()', ROLE_VALUE, 0)
    assert isinstance(e, date.MonthFunction)


def test_month_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'MONTH(1, 2)', ROLE_VALUE, 0)


async def test_day_simple(dummy_local_datetime, dummy_eval_context):
    result = await date.DayFunction([], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == dummy_local_datetime.day


async def test_day_argument(dummy_local_datetime, literal_dummy_timestamp, dummy_eval_context):
    result = await date.DayFunction([literal_dummy_timestamp], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == dummy_local_datetime.day


def test_day_parse():
    e = Function.parse(None, 'DAY()', ROLE_VALUE, 0)
    assert isinstance(e, date.DayFunction)


def test_day_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'DAY(1, 2)', ROLE_VALUE, 0)


async def test_dow_simple(dummy_local_datetime, dummy_eval_context):
    result = await date.DOWFunction([], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == dummy_local_datetime.weekday()


async def test_dow_argument(dummy_local_datetime, literal_dummy_timestamp, dummy_eval_context):
    result = await date.DOWFunction([literal_dummy_timestamp], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == dummy_local_datetime.weekday()


def test_dow_parse():
    e = Function.parse(None, 'DOW()', ROLE_VALUE, 0)
    assert isinstance(e, date.DOWFunction)


def test_dow_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'DOW(1, 2)', ROLE_VALUE, 0)


async def test_ldom_simple(dummy_local_datetime, dummy_eval_context):
    result = await date.LDOMFunction([], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 31


async def test_ldom_argument(dummy_local_datetime, literal_dummy_timestamp, dummy_eval_context):
    result = await date.LDOMFunction([literal_dummy_timestamp], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 31


def test_ldom_parse():
    e = Function.parse(None, 'LDOM()', ROLE_VALUE, 0)
    assert isinstance(e, date.LDOMFunction)


def test_ldom_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'LDOM(1, 2)', ROLE_VALUE, 0)


async def test_hour_simple(dummy_local_datetime, dummy_eval_context):
    result = await date.HourFunction([], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == dummy_local_datetime.hour


async def test_hour_argument(dummy_local_datetime, literal_dummy_timestamp, dummy_eval_context):
    result = await date.HourFunction([literal_dummy_timestamp], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == dummy_local_datetime.hour


def test_hour_parse():
    e = Function.parse(None, 'HOUR()', ROLE_VALUE, 0)
    assert isinstance(e, date.HourFunction)


def test_hour_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'HOUR(1, 2)', ROLE_VALUE, 0)


async def test_minute_simple(dummy_local_datetime, dummy_eval_context):
    result = await date.MinuteFunction([], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == dummy_local_datetime.minute


async def test_minute_argument(dummy_local_datetime, literal_dummy_timestamp, dummy_eval_context):
    result = await date.MinuteFunction([literal_dummy_timestamp], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == dummy_local_datetime.minute


def test_minute_parse():
    e = Function.parse(None, 'MINUTE()', ROLE_VALUE, 0)
    assert isinstance(e, date.MinuteFunction)


def test_minute_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'MINUTE(1, 2)', ROLE_VALUE, 0)


async def test_second_simple(dummy_local_datetime, dummy_eval_context):
    result = await date.SecondFunction([], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == dummy_local_datetime.second


async def test_second_argument(dummy_local_datetime, literal_dummy_timestamp, dummy_eval_context):
    result = await date.SecondFunction([literal_dummy_timestamp], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == dummy_local_datetime.second


def test_second_parse():
    e = Function.parse(None, 'SECOND()', ROLE_VALUE, 0)
    assert isinstance(e, date.SecondFunction)


def test_second_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'SECOND(1, 2)', ROLE_VALUE, 0)


async def test_millisecond(dummy_local_datetime, dummy_eval_context):
    result = await date.MillisecondFunction([], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == dummy_local_datetime.microsecond // 1000


def test_millisecond_parse():
    e = Function.parse(None, 'MILLISECOND()', ROLE_VALUE, 0)
    assert isinstance(e, date.MillisecondFunction)


def test_millisecond_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'MILLISECOND(1)', ROLE_VALUE, 0)


async def test_minuteday_simple(dummy_local_datetime, dummy_eval_context):
    result = await date.MinuteDayFunction([], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == dummy_local_datetime.hour * 60 + dummy_local_datetime.minute


async def test_minuteday_argument(dummy_local_datetime, literal_dummy_timestamp, dummy_eval_context):
    result = await date.MinuteDayFunction([literal_dummy_timestamp], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == dummy_local_datetime.hour * 60 + dummy_local_datetime.minute


def test_minuteday_parse():
    e = Function.parse(None, 'MINUTEDAY()', ROLE_VALUE, 0)
    assert isinstance(e, date.MinuteDayFunction)


def test_minuteday_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'MINUTEDAY(1, 2)', ROLE_VALUE, 0)


async def test_secondday_simple(dummy_local_datetime, dummy_eval_context):
    result = await date.SecondDayFunction([], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == dummy_local_datetime.hour * 3600 + dummy_local_datetime.minute * 60 + dummy_local_datetime.second


async def test_secondday_argument(dummy_local_datetime, literal_dummy_timestamp, dummy_eval_context):
    result = await date.SecondDayFunction([literal_dummy_timestamp], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == dummy_local_datetime.hour * 3600 + dummy_local_datetime.minute * 60 + dummy_local_datetime.second


def test_secondday_parse():
    e = Function.parse(None, 'SECONDDAY()', ROLE_VALUE, 0)
    assert isinstance(e, date.SecondDayFunction)


def test_secondday_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'SECONDDAY(1, 2)', ROLE_VALUE, 0)


async def test_date(dummy_local_datetime, dummy_timestamp, dummy_eval_context):
    result = await date.DateFunction([
        literalvalues.LiteralValue(dummy_local_datetime.year, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.month, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.day, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.hour, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.minute, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.second, '', ROLE_VALUE)
    ], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == int(dummy_timestamp)


def test_date_parse():
    e = Function.parse(None, 'DATE(2019, 3, 14, 1, 2, 3)', ROLE_VALUE, 0)
    assert isinstance(e, date.DateFunction)


def test_date_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'DATE(2019, 3, 14, 1, 2)', ROLE_VALUE, 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'DATE(2019, 3, 14, 1, 2, 3, 4)', ROLE_VALUE, 0)


async def test_boy_simple(dummy_local_datetime, local_tz_info, dummy_eval_context):
    result = await date.BOYFunction([], role=ROLE_VALUE).eval(dummy_eval_context)

    dt = dummy_local_datetime.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    dt = dt.astimezone(local_tz_info)
    assert result == dt.timestamp()


async def test_boy_negative(dummy_local_datetime, dummy_timestamp, local_tz_info, dummy_eval_context):
    result = await date.BOYFunction(
        [literalvalues.LiteralValue(-30, '', ROLE_VALUE)], role=ROLE_VALUE
    ).eval(dummy_eval_context)

    dt = dummy_local_datetime.replace(
        year=dummy_local_datetime.year - 30,
        month=1,
        day=1,
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )
    dt = dt.astimezone(local_tz_info)
    assert result == dt.timestamp()


async def test_boy_positive(dummy_local_datetime, dummy_timestamp, local_tz_info, dummy_eval_context):
    result = await date.BOYFunction(
        [literalvalues.LiteralValue(100, '', ROLE_VALUE)], role=ROLE_VALUE
    ).eval(dummy_eval_context)

    dt = dummy_local_datetime.replace(
        year=dummy_local_datetime.year + 100,
        month=1,
        day=1,
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )
    dt = dt.astimezone(local_tz_info)
    assert result == dt.timestamp()


def test_boy_parse():
    e = Function.parse(None, 'BOY()', ROLE_VALUE, 0)
    assert isinstance(e, date.BOYFunction)


def test_boy_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'BOY(1, 2)', ROLE_VALUE, 0)


async def test_bom_simple(dummy_local_datetime, local_tz_info, dummy_eval_context):
    result = await date.BOMFunction([], role=ROLE_VALUE).eval(dummy_eval_context)

    dt = dummy_local_datetime.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    dt = dt.astimezone(local_tz_info)
    assert result == dt.timestamp()


async def test_bom_negative(dummy_local_datetime, dummy_timestamp, local_tz_info, dummy_eval_context):
    result = await date.BOMFunction(
        [literalvalues.LiteralValue(-13, '', ROLE_VALUE)], role=ROLE_VALUE
    ).eval(dummy_eval_context)

    dt = dummy_local_datetime.replace(
        year=dummy_local_datetime.year - 1,
        month=dummy_local_datetime.month - 1,
        day=1,
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )
    dt = dt.astimezone(local_tz_info)
    assert result == dt.timestamp()


async def test_bom_positive(dummy_local_datetime, dummy_timestamp, local_tz_info, dummy_eval_context):
    result = await date.BOMFunction(
        [literalvalues.LiteralValue(13, '', ROLE_VALUE)], role=ROLE_VALUE
    ).eval(dummy_eval_context)

    dt = dummy_local_datetime.replace(
        year=dummy_local_datetime.year + 1,
        month=dummy_local_datetime.month + 1,
        day=1,
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )
    dt = dt.astimezone(local_tz_info)
    assert result == dt.timestamp()


def test_bom_parse():
    e = Function.parse(None, 'BOM()', ROLE_VALUE, 0)
    assert isinstance(e, date.BOMFunction)


def test_bom_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'BOM(1, 2)', ROLE_VALUE, 0)


async def test_bow_simple(dummy_local_datetime, local_tz_info, dummy_eval_context):
    result = await date.BOWFunction([], role=ROLE_VALUE).eval(dummy_eval_context)

    dt = dummy_local_datetime.replace(
        day=dummy_local_datetime.day - dummy_local_datetime.weekday(),
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )
    dt = dt.astimezone(local_tz_info)
    assert result == dt.timestamp()


async def test_bow_negative(dummy_local_datetime, local_tz_info, dummy_eval_context):
    result = await date.BOWFunction(
        [literalvalues.LiteralValue(-54, '', ROLE_VALUE)], role=ROLE_VALUE
    ).eval(dummy_eval_context)

    dt = datetime.datetime(2018, 2, 26, 0, 0, 0)
    dt = dt.astimezone(local_tz_info)
    assert result == dt.timestamp()


async def test_bow_positive(dummy_local_datetime, local_tz_info, dummy_eval_context):
    result = await date.BOWFunction(
        [literalvalues.LiteralValue(54, '', ROLE_VALUE)], role=ROLE_VALUE
    ).eval(dummy_eval_context)

    dt = datetime.datetime(2020, 3, 23, 0, 0, 0)
    dt = dt.astimezone(local_tz_info)
    assert result == dt.timestamp()


async def test_bow_sunday(dummy_local_datetime, literal_zero, local_tz_info, dummy_eval_context):
    result = await date.BOWFunction([
        literal_zero,
        literalvalues.LiteralValue(6, '', ROLE_VALUE)
    ], role=ROLE_VALUE).eval(dummy_eval_context)

    dt = dummy_local_datetime.replace(
        day=dummy_local_datetime.day - dummy_local_datetime.weekday() - 1,
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )
    dt = dt.astimezone(local_tz_info)
    assert result == dt.timestamp()


async def test_bow_sunday_negative(dummy_local_datetime, local_tz_info, dummy_eval_context):
    result = await date.BOWFunction([
        literalvalues.LiteralValue(-54, '', ROLE_VALUE),
        literalvalues.LiteralValue(6, '', ROLE_VALUE)
    ], role=ROLE_VALUE).eval(dummy_eval_context)

    dt = datetime.datetime(2018, 2, 25, 0, 0, 0)
    dt = dt.astimezone(local_tz_info)
    assert result == dt.timestamp()


async def test_bow_sunday_positive(dummy_local_datetime, local_tz_info, dummy_eval_context):
    result = await date.BOWFunction([
        literalvalues.LiteralValue(54, '', ROLE_VALUE),
        literalvalues.LiteralValue(6, '', ROLE_VALUE)
    ], role=ROLE_VALUE).eval(dummy_eval_context)

    dt = datetime.datetime(2020, 3, 22, 0, 0, 0)
    dt = dt.astimezone(local_tz_info)
    assert result == dt.timestamp()


def test_bow_parse():
    e = Function.parse(None, 'BOW()', ROLE_VALUE, 0)
    assert isinstance(e, date.BOWFunction)


def test_bow_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'BOW(1, 2, 3)', ROLE_VALUE, 0)


async def test_hmsinterval_hours(dummy_local_datetime, dummy_eval_context):
    result = await date.HMSIntervalFunction([
        literalvalues.LiteralValue(dummy_local_datetime.hour - 1, '', ROLE_VALUE),
        literalvalues.LiteralValue(0, '', ROLE_VALUE),
        literalvalues.LiteralValue(0, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.hour + 1, '', ROLE_VALUE),
        literalvalues.LiteralValue(0, '', ROLE_VALUE),
        literalvalues.LiteralValue(0, '', ROLE_VALUE)
    ], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 1

    result = await date.HMSIntervalFunction([
        literalvalues.LiteralValue(dummy_local_datetime.hour - 2, '', ROLE_VALUE),
        literalvalues.LiteralValue(0, '', ROLE_VALUE),
        literalvalues.LiteralValue(0, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.hour - 1, '', ROLE_VALUE),
        literalvalues.LiteralValue(0, '', ROLE_VALUE),
        literalvalues.LiteralValue(0, '', ROLE_VALUE)
    ], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 0

    result = await date.HMSIntervalFunction([
        literalvalues.LiteralValue(dummy_local_datetime.hour + 1, '', ROLE_VALUE),
        literalvalues.LiteralValue(0, '', ROLE_VALUE),
        literalvalues.LiteralValue(0, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.hour + 2, '', ROLE_VALUE),
        literalvalues.LiteralValue(0, '', ROLE_VALUE),
        literalvalues.LiteralValue(0, '', ROLE_VALUE)
    ], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 0


async def test_hmsinterval_minutes(dummy_local_datetime, dummy_eval_context):
    result = await date.HMSIntervalFunction([
        literalvalues.LiteralValue(dummy_local_datetime.hour, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.minute - 1, '', ROLE_VALUE),
        literalvalues.LiteralValue(0, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.hour, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.minute + 1, '', ROLE_VALUE),
        literalvalues.LiteralValue(0, '', ROLE_VALUE)
    ], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 1

    result = await date.HMSIntervalFunction([
        literalvalues.LiteralValue(dummy_local_datetime.hour, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.minute - 2, '', ROLE_VALUE),
        literalvalues.LiteralValue(0, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.hour, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.minute - 1, '', ROLE_VALUE),
        literalvalues.LiteralValue(0, '', ROLE_VALUE)
    ], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 0

    result = await date.HMSIntervalFunction([
        literalvalues.LiteralValue(dummy_local_datetime.hour, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.minute + 1, '', ROLE_VALUE),
        literalvalues.LiteralValue(0, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.hour, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.minute + 2, '', ROLE_VALUE),
        literalvalues.LiteralValue(0, '', ROLE_VALUE)
    ], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 0


async def test_hmsinterval_seconds(dummy_local_datetime, dummy_eval_context):
    result = await date.HMSIntervalFunction([
        literalvalues.LiteralValue(dummy_local_datetime.hour, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.minute, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.second - 1, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.hour, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.minute, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.second + 1, '', ROLE_VALUE)
    ], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 1

    result = await date.HMSIntervalFunction([
        literalvalues.LiteralValue(dummy_local_datetime.hour, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.minute, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.second - 2, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.hour, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.minute, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.second - 1, '', ROLE_VALUE)
    ], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 0

    result = await date.HMSIntervalFunction([
        literalvalues.LiteralValue(dummy_local_datetime.hour, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.minute, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.second + 1, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.hour, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.minute, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.second + 2, '', ROLE_VALUE)
    ], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 0


async def test_hmsinterval_limit(dummy_local_datetime, dummy_eval_context):
    result = await date.HMSIntervalFunction([
        literalvalues.LiteralValue(dummy_local_datetime.hour, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.minute, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.second, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.hour, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.minute, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.second + 1, '', ROLE_VALUE)
    ], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 1

    result = await date.HMSIntervalFunction([
        literalvalues.LiteralValue(dummy_local_datetime.hour, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.minute, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.second - 1, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.hour, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.minute, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.second, '', ROLE_VALUE)
    ], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 1


async def test_hmsinterval_reversed(dummy_local_datetime, dummy_eval_context):
    result = await date.HMSIntervalFunction([
        literalvalues.LiteralValue(dummy_local_datetime.hour + 1, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.minute, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.second, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.hour - 1, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.minute, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.second, '', ROLE_VALUE)
    ], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 0


def test_hmsinterval_parse():
    e = Function.parse(None, 'HMSINTERVAL(1, 1, 1, 2, 2, 2)', ROLE_VALUE, 0)
    assert isinstance(e, date.HMSIntervalFunction)


def test_hmsinterval_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'HMSINTERVAL(1, 2, 3, 4, 5)', ROLE_VALUE, 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'HMSINTERVAL(1, 2, 3, 4, 5, 6, 7)', ROLE_VALUE, 0)


async def test_mdinterval_months(dummy_local_datetime, dummy_eval_context):
    result = await date.MDIntervalFunction([
        literalvalues.LiteralValue(dummy_local_datetime.month - 1, '', ROLE_VALUE),
        literalvalues.LiteralValue(1, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.month + 1, '', ROLE_VALUE),
        literalvalues.LiteralValue(1, '', ROLE_VALUE)
    ], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 1

    result = await date.MDIntervalFunction([
        literalvalues.LiteralValue(dummy_local_datetime.month - 2, '', ROLE_VALUE),
        literalvalues.LiteralValue(1, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.month - 1, '', ROLE_VALUE),
        literalvalues.LiteralValue(1, '', ROLE_VALUE)
    ], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 0

    result = await date.MDIntervalFunction([
        literalvalues.LiteralValue(dummy_local_datetime.month + 1, '', ROLE_VALUE),
        literalvalues.LiteralValue(1, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.month + 2, '', ROLE_VALUE),
        literalvalues.LiteralValue(1, '', ROLE_VALUE)
    ], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 0


async def test_mdinterval_days(dummy_local_datetime, dummy_eval_context):
    result = await date.MDIntervalFunction([
        literalvalues.LiteralValue(dummy_local_datetime.month, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.day - 1, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.month, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.day + 1, '', ROLE_VALUE)
    ], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 1

    result = await date.MDIntervalFunction([
        literalvalues.LiteralValue(dummy_local_datetime.month, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.day - 2, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.month, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.day - 1, '', ROLE_VALUE)
    ], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 0

    result = await date.MDIntervalFunction([
        literalvalues.LiteralValue(dummy_local_datetime.month, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.day + 1, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.month, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.day + 2, '', ROLE_VALUE)
    ], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 0


async def test_mdinterval_limit(dummy_local_datetime, dummy_eval_context):
    result = await date.MDIntervalFunction([
        literalvalues.LiteralValue(dummy_local_datetime.month, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.day, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.month, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.day + 1, '', ROLE_VALUE)
    ], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 1

    result = await date.MDIntervalFunction([
        literalvalues.LiteralValue(dummy_local_datetime.month, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.day - 1, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.month, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.day, '', ROLE_VALUE)
    ], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 1


async def test_mdinterval_reversed(dummy_local_datetime, dummy_eval_context):
    result = await date.MDIntervalFunction([
        literalvalues.LiteralValue(dummy_local_datetime.month + 1, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.day, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.month - 1, '', ROLE_VALUE),
        literalvalues.LiteralValue(dummy_local_datetime.day, '', ROLE_VALUE)
    ], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 0


def test_mdinterval_parse():
    e = Function.parse(None, 'MDINTERVAL(1, 1, 2, 2)', ROLE_VALUE, 0)
    assert isinstance(e, date.MDIntervalFunction)


def test_mdinterval_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'MDINTERVAL(1, 2, 3)', ROLE_VALUE, 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'MDINTERVAL(1, 2, 3, 4, 5)', ROLE_VALUE, 0)
