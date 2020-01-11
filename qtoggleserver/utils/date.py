
import datetime

from typing import Union

import pytz


def from_utc(moment: datetime.datetime, timezone: Union[str, pytz.tzinfo]) -> datetime.datetime:
    if isinstance(timezone, str):
        timezone = pytz.timezone(timezone)

    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=pytz.UTC)

    return moment.astimezone(timezone)


def to_utc(moment: datetime.datetime, timezone: Union[str, pytz.tzinfo] = pytz.UTC) -> datetime.datetime:
    if moment.tzinfo is None:
        if isinstance(timezone, str):
            moment = pytz.timezone(timezone).localize(moment)

        else:
            moment = moment.replace(tzinfo=timezone)

    return moment.astimezone(pytz.UTC)
