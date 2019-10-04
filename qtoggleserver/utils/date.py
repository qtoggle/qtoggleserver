
import pytz


def from_utc(moment, timezone):
    # noinspection PyTypeChecker
    if isinstance(timezone, str):
        timezone = pytz.timezone(timezone)
    
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=pytz.UTC)
    
    return moment.astimezone(timezone)


def to_utc(moment, timezone=pytz.UTC):
    if moment.tzinfo is None:
        # noinspection PyTypeChecker
        if isinstance(timezone, str):
            moment = pytz.timezone(timezone).localize(moment)

        else:
            moment = moment.replace(tzinfo=timezone)

    return moment.astimezone(pytz.UTC)
