
import datetime
import pytest

from qtoggleserver.core.expressions import date, literalvalues, Function
from qtoggleserver.core.expressions import InvalidNumberOfArguments


async def test_year_simple(freezer, dummy_local_datetime):
    freezer.move_to(dummy_local_datetime)

    result = await date.YearFunction([]).eval(context={})
    assert result == dummy_local_datetime.year


async def test_year_argument(dummy_local_datetime, literal_dummy_timestamp):
    result = await date.YearFunction([literal_dummy_timestamp]).eval(context={})
    assert result == dummy_local_datetime.year


def test_year_parse():
    e = Function.parse(None, 'YEAR()', 0)
    assert isinstance(e, date.YearFunction)


def test_year_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'YEAR(1, 2)', 0)


async def test_month_simple(freezer, dummy_local_datetime):
    freezer.move_to(dummy_local_datetime)

    result = await date.MonthFunction([]).eval(context={})
    assert result == dummy_local_datetime.month


async def test_month_argument(dummy_local_datetime, literal_dummy_timestamp):
    result = await date.MonthFunction([literal_dummy_timestamp]).eval(context={})
    assert result == dummy_local_datetime.month


def test_month_parse():
    e = Function.parse(None, 'MONTH()', 0)
    assert isinstance(e, date.MonthFunction)


def test_month_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'MONTH(1, 2)', 0)


async def test_day_simple(freezer, dummy_local_datetime):
    freezer.move_to(dummy_local_datetime)

    result = await date.DayFunction([]).eval(context={})
    assert result == dummy_local_datetime.day


async def test_day_argument(dummy_local_datetime, literal_dummy_timestamp):
    result = await date.DayFunction([literal_dummy_timestamp]).eval(context={})
    assert result == dummy_local_datetime.day


def test_day_parse():
    e = Function.parse(None, 'DAY()', 0)
    assert isinstance(e, date.DayFunction)


def test_day_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'DAY(1, 2)', 0)


async def test_dow_simple(freezer, dummy_local_datetime):
    freezer.move_to(dummy_local_datetime)

    result = await date.DOWFunction([]).eval(context={})
    assert result == dummy_local_datetime.weekday()


async def test_dow_argument(dummy_local_datetime, literal_dummy_timestamp):
    result = await date.DOWFunction([literal_dummy_timestamp]).eval(context={})
    assert result == dummy_local_datetime.weekday()


def test_dow_parse():
    e = Function.parse(None, 'DOW()', 0)
    assert isinstance(e, date.DOWFunction)


def test_dow_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'DOW(1, 2)', 0)


async def test_ldom_simple(freezer, dummy_local_datetime):
    freezer.move_to(dummy_local_datetime)

    result = await date.LDOMFunction([]).eval(context={})
    assert result == 31


async def test_ldom_argument(dummy_local_datetime, literal_dummy_timestamp):
    result = await date.LDOMFunction([literal_dummy_timestamp]).eval(context={})
    assert result == 31


def test_ldom_parse():
    e = Function.parse(None, 'LDOM()', 0)
    assert isinstance(e, date.LDOMFunction)


def test_ldom_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'LDOM(1, 2)', 0)


async def test_hour_simple(freezer, dummy_local_datetime):
    freezer.move_to(dummy_local_datetime)

    result = await date.HourFunction([]).eval(context={})
    assert result == dummy_local_datetime.hour


async def test_hour_argument(dummy_local_datetime, literal_dummy_timestamp):
    result = await date.HourFunction([literal_dummy_timestamp]).eval(context={})
    assert result == dummy_local_datetime.hour


def test_hour_parse():
    e = Function.parse(None, 'HOUR()', 0)
    assert isinstance(e, date.HourFunction)


def test_hour_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'HOUR(1, 2)', 0)


async def test_minute_simple(freezer, dummy_local_datetime):
    freezer.move_to(dummy_local_datetime)

    result = await date.MinuteFunction([]).eval(context={})
    assert result == dummy_local_datetime.minute


async def test_minute_argument(dummy_local_datetime, literal_dummy_timestamp):
    result = await date.MinuteFunction([literal_dummy_timestamp]).eval(context={})
    assert result == dummy_local_datetime.minute


def test_minute_parse():
    e = Function.parse(None, 'MINUTE()', 0)
    assert isinstance(e, date.MinuteFunction)


def test_minute_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'MINUTE(1, 2)', 0)


async def test_second_simple(freezer, dummy_local_datetime):
    freezer.move_to(dummy_local_datetime)

    result = await date.SecondFunction([]).eval(context={})
    assert result == dummy_local_datetime.second


async def test_second_argument(dummy_local_datetime, literal_dummy_timestamp):
    result = await date.SecondFunction([literal_dummy_timestamp]).eval(context={})
    assert result == dummy_local_datetime.second


def test_second_parse():
    e = Function.parse(None, 'SECOND()', 0)
    assert isinstance(e, date.SecondFunction)


def test_second_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'SECOND(1, 2)', 0)


async def test_millisecond(freezer, dummy_local_datetime):
    freezer.move_to(dummy_local_datetime)

    result = await date.MillisecondFunction([]).eval(context={})
    assert result == dummy_local_datetime.microsecond // 1000


def test_millisecond_parse():
    e = Function.parse(None, 'MILLISECOND()', 0)
    assert isinstance(e, date.MillisecondFunction)


def test_millisecond_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'MILLISECOND(1)', 0)


async def test_date(dummy_local_datetime, dummy_timestamp):
    result = await date.DateFunction([
        literalvalues.LiteralValue(dummy_local_datetime.year, ''),
        literalvalues.LiteralValue(dummy_local_datetime.month, ''),
        literalvalues.LiteralValue(dummy_local_datetime.day, ''),
        literalvalues.LiteralValue(dummy_local_datetime.hour, ''),
        literalvalues.LiteralValue(dummy_local_datetime.minute, ''),
        literalvalues.LiteralValue(dummy_local_datetime.second, '')
    ]).eval(context={})
    assert result == int(dummy_timestamp)


def test_date_parse():
    e = Function.parse(None, 'DATE(2019, 3, 14, 1, 2, 3)', 0)
    assert isinstance(e, date.DateFunction)


def test_date_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'DATE(2019, 3, 14, 1, 2)', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'DATE(2019, 3, 14, 1, 2, 3, 4)', 0)


async def test_boy_simple(freezer, dummy_local_datetime, local_tz_info):
    freezer.move_to(dummy_local_datetime)
    result = await date.BOYFunction([]).eval(context={})

    dt = dummy_local_datetime.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    dt = dt.astimezone(local_tz_info)
    assert result == dt.timestamp()


async def test_boy_negative(freezer, dummy_local_datetime, dummy_timestamp, local_tz_info):
    freezer.move_to(dummy_local_datetime)
    result = await date.BOYFunction([literalvalues.LiteralValue(-30, '')]).eval(context={})

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


async def test_boy_positive(freezer, dummy_local_datetime, dummy_timestamp, local_tz_info):
    freezer.move_to(dummy_local_datetime)
    result = await date.BOYFunction([literalvalues.LiteralValue(100, '')]).eval(context={})

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
    e = Function.parse(None, 'BOY()', 0)
    assert isinstance(e, date.BOYFunction)


def test_boy_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'BOY(1, 2)', 0)


async def test_bom_simple(freezer, dummy_local_datetime, local_tz_info):
    freezer.move_to(dummy_local_datetime)
    result = await date.BOMFunction([]).eval(context={})

    dt = dummy_local_datetime.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    dt = dt.astimezone(local_tz_info)
    assert result == dt.timestamp()


async def test_bom_negative(freezer, dummy_local_datetime, dummy_timestamp, local_tz_info):
    freezer.move_to(dummy_local_datetime)
    result = await date.BOMFunction([literalvalues.LiteralValue(-13, '')]).eval(context={})

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


async def test_bom_positive(freezer, dummy_local_datetime, dummy_timestamp, local_tz_info):
    freezer.move_to(dummy_local_datetime)
    result = await date.BOMFunction([literalvalues.LiteralValue(13, '')]).eval(context={})

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
    e = Function.parse(None, 'BOM()', 0)
    assert isinstance(e, date.BOMFunction)


def test_bom_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'BOM(1, 2)', 0)


async def test_bow_simple(freezer, dummy_local_datetime, local_tz_info):
    freezer.move_to(dummy_local_datetime)
    result = await date.BOWFunction([]).eval(context={})

    dt = dummy_local_datetime.replace(
        day=dummy_local_datetime.day - dummy_local_datetime.weekday(),
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )
    dt = dt.astimezone(local_tz_info)
    assert result == dt.timestamp()


async def test_bow_negative(freezer, dummy_local_datetime, local_tz_info):
    freezer.move_to(dummy_local_datetime)
    result = await date.BOWFunction([literalvalues.LiteralValue(-54, '')]).eval(context={})

    dt = datetime.datetime(2018, 2, 26, 0, 0, 0)
    dt = dt.astimezone(local_tz_info)
    assert result == dt.timestamp()


async def test_bow_positive(freezer, dummy_local_datetime, local_tz_info):
    freezer.move_to(dummy_local_datetime)
    result = await date.BOWFunction([literalvalues.LiteralValue(54, '')]).eval(context={})

    dt = datetime.datetime(2020, 3, 23, 0, 0, 0)
    dt = dt.astimezone(local_tz_info)
    assert result == dt.timestamp()


async def test_bow_sunday(freezer, dummy_local_datetime, literal_zero, local_tz_info):
    freezer.move_to(dummy_local_datetime)
    result = await date.BOWFunction([
        literal_zero,
        literalvalues.LiteralValue(6, '')
    ]).eval(context={})

    dt = dummy_local_datetime.replace(
        day=dummy_local_datetime.day - dummy_local_datetime.weekday() - 1,
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )
    dt = dt.astimezone(local_tz_info)
    assert result == dt.timestamp()


async def test_bow_sunday_negative(freezer, dummy_local_datetime, local_tz_info):
    freezer.move_to(dummy_local_datetime)
    result = await date.BOWFunction([
        literalvalues.LiteralValue(-54, ''),
        literalvalues.LiteralValue(6, '')
    ]).eval(context={})

    dt = datetime.datetime(2018, 2, 25, 0, 0, 0)
    dt = dt.astimezone(local_tz_info)
    assert result == dt.timestamp()


async def test_bow_sunday_positive(freezer, dummy_local_datetime, local_tz_info):
    freezer.move_to(dummy_local_datetime)
    result = await date.BOWFunction([
        literalvalues.LiteralValue(54, ''),
        literalvalues.LiteralValue(6, '')
    ]).eval(context={})

    dt = datetime.datetime(2020, 3, 22, 0, 0, 0)
    dt = dt.astimezone(local_tz_info)
    assert result == dt.timestamp()


def test_bow_parse():
    e = Function.parse(None, 'BOW()', 0)
    assert isinstance(e, date.BOWFunction)


def test_bow_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'BOW(1, 2, 3)', 0)


async def test_hmsinterval_hours(freezer, dummy_local_datetime):
    freezer.move_to(dummy_local_datetime)
    result = await date.HMSIntervalFunction([
        literalvalues.LiteralValue(dummy_local_datetime.hour - 1, ''),
        literalvalues.LiteralValue(0, ''),
        literalvalues.LiteralValue(0, ''),
        literalvalues.LiteralValue(dummy_local_datetime.hour + 1, ''),
        literalvalues.LiteralValue(0, ''),
        literalvalues.LiteralValue(0, '')
    ]).eval(context={})
    assert result == 1

    result = await date.HMSIntervalFunction([
        literalvalues.LiteralValue(dummy_local_datetime.hour - 2, ''),
        literalvalues.LiteralValue(0, ''),
        literalvalues.LiteralValue(0, ''),
        literalvalues.LiteralValue(dummy_local_datetime.hour - 1, ''),
        literalvalues.LiteralValue(0, ''),
        literalvalues.LiteralValue(0, '')
    ]).eval(context={})
    assert result == 0

    result = await date.HMSIntervalFunction([
        literalvalues.LiteralValue(dummy_local_datetime.hour + 1, ''),
        literalvalues.LiteralValue(0, ''),
        literalvalues.LiteralValue(0, ''),
        literalvalues.LiteralValue(dummy_local_datetime.hour + 2, ''),
        literalvalues.LiteralValue(0, ''),
        literalvalues.LiteralValue(0, '')
    ]).eval(context={})
    assert result == 0


async def test_hmsinterval_minutes(freezer, dummy_local_datetime):
    freezer.move_to(dummy_local_datetime)
    result = await date.HMSIntervalFunction([
        literalvalues.LiteralValue(dummy_local_datetime.hour, ''),
        literalvalues.LiteralValue(dummy_local_datetime.minute - 1, ''),
        literalvalues.LiteralValue(0, ''),
        literalvalues.LiteralValue(dummy_local_datetime.hour, ''),
        literalvalues.LiteralValue(dummy_local_datetime.minute + 1, ''),
        literalvalues.LiteralValue(0, '')
    ]).eval(context={})
    assert result == 1

    result = await date.HMSIntervalFunction([
        literalvalues.LiteralValue(dummy_local_datetime.hour, ''),
        literalvalues.LiteralValue(dummy_local_datetime.minute - 2, ''),
        literalvalues.LiteralValue(0, ''),
        literalvalues.LiteralValue(dummy_local_datetime.hour, ''),
        literalvalues.LiteralValue(dummy_local_datetime.minute - 1, ''),
        literalvalues.LiteralValue(0, '')
    ]).eval(context={})
    assert result == 0

    result = await date.HMSIntervalFunction([
        literalvalues.LiteralValue(dummy_local_datetime.hour, ''),
        literalvalues.LiteralValue(dummy_local_datetime.minute + 1, ''),
        literalvalues.LiteralValue(0, ''),
        literalvalues.LiteralValue(dummy_local_datetime.hour, ''),
        literalvalues.LiteralValue(dummy_local_datetime.minute + 2, ''),
        literalvalues.LiteralValue(0, '')
    ]).eval(context={})
    assert result == 0


async def test_hmsinterval_seconds(freezer, dummy_local_datetime):
    freezer.move_to(dummy_local_datetime)
    result = await date.HMSIntervalFunction([
        literalvalues.LiteralValue(dummy_local_datetime.hour, ''),
        literalvalues.LiteralValue(dummy_local_datetime.minute, ''),
        literalvalues.LiteralValue(dummy_local_datetime.second - 1, ''),
        literalvalues.LiteralValue(dummy_local_datetime.hour, ''),
        literalvalues.LiteralValue(dummy_local_datetime.minute, ''),
        literalvalues.LiteralValue(dummy_local_datetime.second + 1, '')
    ]).eval(context={})
    assert result == 1

    result = await date.HMSIntervalFunction([
        literalvalues.LiteralValue(dummy_local_datetime.hour, ''),
        literalvalues.LiteralValue(dummy_local_datetime.minute, ''),
        literalvalues.LiteralValue(dummy_local_datetime.second - 2, ''),
        literalvalues.LiteralValue(dummy_local_datetime.hour, ''),
        literalvalues.LiteralValue(dummy_local_datetime.minute, ''),
        literalvalues.LiteralValue(dummy_local_datetime.second - 1, '')
    ]).eval(context={})
    assert result == 0

    result = await date.HMSIntervalFunction([
        literalvalues.LiteralValue(dummy_local_datetime.hour, ''),
        literalvalues.LiteralValue(dummy_local_datetime.minute, ''),
        literalvalues.LiteralValue(dummy_local_datetime.second + 1, ''),
        literalvalues.LiteralValue(dummy_local_datetime.hour, ''),
        literalvalues.LiteralValue(dummy_local_datetime.minute, ''),
        literalvalues.LiteralValue(dummy_local_datetime.second + 2, '')
    ]).eval(context={})
    assert result == 0


async def test_hmsinterval_limit(freezer, dummy_local_datetime):
    freezer.move_to(dummy_local_datetime)
    result = await date.HMSIntervalFunction([
        literalvalues.LiteralValue(dummy_local_datetime.hour, ''),
        literalvalues.LiteralValue(dummy_local_datetime.minute, ''),
        literalvalues.LiteralValue(dummy_local_datetime.second, ''),
        literalvalues.LiteralValue(dummy_local_datetime.hour, ''),
        literalvalues.LiteralValue(dummy_local_datetime.minute, ''),
        literalvalues.LiteralValue(dummy_local_datetime.second + 1, '')
    ]).eval(context={})
    assert result == 1

    result = await date.HMSIntervalFunction([
        literalvalues.LiteralValue(dummy_local_datetime.hour, ''),
        literalvalues.LiteralValue(dummy_local_datetime.minute, ''),
        literalvalues.LiteralValue(dummy_local_datetime.second - 1, ''),
        literalvalues.LiteralValue(dummy_local_datetime.hour, ''),
        literalvalues.LiteralValue(dummy_local_datetime.minute, ''),
        literalvalues.LiteralValue(dummy_local_datetime.second, '')
    ]).eval(context={})
    assert result == 1


async def test_hmsinterval_reversed(freezer, dummy_local_datetime):
    freezer.move_to(dummy_local_datetime)
    result = await date.HMSIntervalFunction([
        literalvalues.LiteralValue(dummy_local_datetime.hour + 1, ''),
        literalvalues.LiteralValue(dummy_local_datetime.minute, ''),
        literalvalues.LiteralValue(dummy_local_datetime.second, ''),
        literalvalues.LiteralValue(dummy_local_datetime.hour - 1, ''),
        literalvalues.LiteralValue(dummy_local_datetime.minute, ''),
        literalvalues.LiteralValue(dummy_local_datetime.second, '')
    ]).eval(context={})
    assert result == 0


def test_hmsinterval_parse():
    e = Function.parse(None, 'HMSINTERVAL(1, 1, 1, 2, 2, 2)', 0)
    assert isinstance(e, date.HMSIntervalFunction)


def test_hmsinterval_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'HMSINTERVAL(1, 2, 3, 4, 5)', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'HMSINTERVAL(1, 2, 3, 4, 5, 6, 7)', 0)


async def test_mdinterval_months(freezer, dummy_local_datetime):
    freezer.move_to(dummy_local_datetime)
    result = await date.MDIntervalFunction([
        literalvalues.LiteralValue(dummy_local_datetime.month - 1, ''),
        literalvalues.LiteralValue(1, ''),
        literalvalues.LiteralValue(dummy_local_datetime.month + 1, ''),
        literalvalues.LiteralValue(1, '')
    ]).eval(context={})
    assert result == 1

    result = await date.MDIntervalFunction([
        literalvalues.LiteralValue(dummy_local_datetime.month - 2, ''),
        literalvalues.LiteralValue(1, ''),
        literalvalues.LiteralValue(dummy_local_datetime.month - 1, ''),
        literalvalues.LiteralValue(1, '')
    ]).eval(context={})
    assert result == 0

    result = await date.MDIntervalFunction([
        literalvalues.LiteralValue(dummy_local_datetime.month + 1, ''),
        literalvalues.LiteralValue(1, ''),
        literalvalues.LiteralValue(dummy_local_datetime.month + 2, ''),
        literalvalues.LiteralValue(1, '')
    ]).eval(context={})
    assert result == 0


async def test_mdinterval_days(freezer, dummy_local_datetime):
    freezer.move_to(dummy_local_datetime)
    result = await date.MDIntervalFunction([
        literalvalues.LiteralValue(dummy_local_datetime.month, ''),
        literalvalues.LiteralValue(dummy_local_datetime.day - 1, ''),
        literalvalues.LiteralValue(dummy_local_datetime.month, ''),
        literalvalues.LiteralValue(dummy_local_datetime.day + 1, '')
    ]).eval(context={})
    assert result == 1

    result = await date.MDIntervalFunction([
        literalvalues.LiteralValue(dummy_local_datetime.month, ''),
        literalvalues.LiteralValue(dummy_local_datetime.day - 2, ''),
        literalvalues.LiteralValue(dummy_local_datetime.month, ''),
        literalvalues.LiteralValue(dummy_local_datetime.day - 1, '')
    ]).eval(context={})
    assert result == 0

    result = await date.MDIntervalFunction([
        literalvalues.LiteralValue(dummy_local_datetime.month, ''),
        literalvalues.LiteralValue(dummy_local_datetime.day + 1, ''),
        literalvalues.LiteralValue(dummy_local_datetime.month, ''),
        literalvalues.LiteralValue(dummy_local_datetime.day + 2, '')
    ]).eval(context={})
    assert result == 0


async def test_mdinterval_limit(freezer, dummy_local_datetime):
    freezer.move_to(dummy_local_datetime)
    result = await date.MDIntervalFunction([
        literalvalues.LiteralValue(dummy_local_datetime.month, ''),
        literalvalues.LiteralValue(dummy_local_datetime.day, ''),
        literalvalues.LiteralValue(dummy_local_datetime.month, ''),
        literalvalues.LiteralValue(dummy_local_datetime.day + 1, '')
    ]).eval(context={})
    assert result == 1

    result = await date.MDIntervalFunction([
        literalvalues.LiteralValue(dummy_local_datetime.month, ''),
        literalvalues.LiteralValue(dummy_local_datetime.day - 1, ''),
        literalvalues.LiteralValue(dummy_local_datetime.month, ''),
        literalvalues.LiteralValue(dummy_local_datetime.day, '')
    ]).eval(context={})
    assert result == 1


async def test_mdinterval_reversed(freezer, dummy_local_datetime):
    freezer.move_to(dummy_local_datetime)
    result = await date.MDIntervalFunction([
        literalvalues.LiteralValue(dummy_local_datetime.month + 1, ''),
        literalvalues.LiteralValue(dummy_local_datetime.day, ''),
        literalvalues.LiteralValue(dummy_local_datetime.month - 1, ''),
        literalvalues.LiteralValue(dummy_local_datetime.day, '')
    ]).eval(context={})
    assert result == 0


def test_mdinterval_parse():
    e = Function.parse(None, 'MDINTERVAL(1, 1, 2, 2)', 0)
    assert isinstance(e, date.MDIntervalFunction)


def test_mdinterval_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'MDINTERVAL(1, 2, 3)', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'MDINTERVAL(1, 2, 3, 4, 5)', 0)
