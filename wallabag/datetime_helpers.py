import datetime
import json
from typing import Union, Optional


# in PTB-Raw we don't have pytz, so we make a little workaround here
DTM_UTC = datetime.timezone.utc
try:
    import pytz

    UTC = pytz.utc
except ImportError:
    UTC = DTM_UTC  # type: ignore[assignment]


def _datetime_to_float_timestamp(dt_obj: datetime.datetime) -> float:
    """
    Converts a datetime object to a float timestamp (with sub-second precision).
    If the datetime object is timezone-naive, it is assumed to be in UTC.
    """
    if dt_obj.tzinfo is None:
        dt_obj = dt_obj.replace(tzinfo=datetime.timezone.utc)
    return dt_obj.timestamp()


def _localize(datetime: datetime.datetime, tzinfo: datetime.tzinfo) -> datetime.datetime:
    """Localize the datetime, where UTC is handled depending on whether pytz is available or not"""
    if tzinfo is DTM_UTC:
        return datetime.replace(tzinfo=DTM_UTC)
    return tzinfo.localize(datetime)  # type: ignore[attr-defined]


def to_float_timestamp(
    time_object: Union[int, float, datetime.timedelta, datetime.datetime, datetime.time],
    reference_timestamp: float = None,
    tzinfo: datetime.tzinfo = None,
) -> float:
    """
    Converts a given time object to a float POSIX timestamp.
    Used to convert different time specifications to a common format. The time object
    can be relative (i.e. indicate a time increment, or a time of day) or absolute.
    object objects from the :class:`datetime` module that are timezone-naive will be assumed
    to be in UTC, if ``bot`` is not passed or ``bot.defaults`` is :obj:`None`.
    Args:
        time_object (:obj:`int` | :obj:`float` | :obj:`datetime.timedelta` | \
            :obj:`datetime.datetime` | :obj:`datetime.time`):
            Time value to convert. The semantics of this parameter will depend on its type:
            * :obj:`int` or :obj:`float` will be interpreted as "seconds from ``reference_t``"
            * :obj:`datetime.timedelta` will be interpreted as
              "time increment from ``reference_t``"
            * :obj:`datetime.datetime` will be interpreted as an absolute date/time value
            * :obj:`datetime.time` will be interpreted as a specific time of day
        reference_timestamp (:obj:`float`, optional): POSIX timestamp that indicates the absolute
            time from which relative calculations are to be performed (e.g. when ``t`` is given as
            an :obj:`int`, indicating "seconds from ``reference_t``"). Defaults to now (the time at
            which this function is called).
            If ``t`` is given as an absolute representation of date & time (i.e. a
            :obj:`datetime.datetime` object), ``reference_timestamp`` is not relevant and so its
            value should be :obj:`None`. If this is not the case, a ``ValueError`` will be raised.
        tzinfo (:obj:`pytz.BaseTzInfo`, optional): If ``t`` is a naive object from the
            :class:`datetime` module, it will be interpreted as this timezone. Defaults to
            ``pytz.utc``.
            Note:
                Only to be used by ``telegram.ext``.
    Returns:
        :obj:`float` | :obj:`None`:
            The return value depends on the type of argument ``t``.
            If ``t`` is given as a time increment (i.e. as a :obj:`int`, :obj:`float` or
            :obj:`datetime.timedelta`), then the return value will be ``reference_t`` + ``t``.
            Else if it is given as an absolute date/time value (i.e. a :obj:`datetime.datetime`
            object), the equivalent value as a POSIX timestamp will be returned.
            Finally, if it is a time of the day without date (i.e. a :obj:`datetime.time`
            object), the return value is the nearest future occurrence of that time of day.
    Raises:
        TypeError: If ``t``'s type is not one of those described above.
        ValueError: If ``t`` is a :obj:`datetime.datetime` and :obj:`reference_timestamp` is not
            :obj:`None`.
    """
    if reference_timestamp is None:
        import time
        reference_timestamp = time.time()
    elif isinstance(time_object, datetime.datetime):
        raise ValueError('t is an (absolute) datetime while reference_timestamp is not None')

    if isinstance(time_object, datetime.timedelta):
        return reference_timestamp + time_object.total_seconds()
    if isinstance(time_object, (int, float)):
        return reference_timestamp + time_object

    if tzinfo is None:
        tzinfo = UTC

    if isinstance(time_object, datetime.time):
        reference_dt = datetime.datetime.fromtimestamp(
            reference_timestamp, tz=time_object.tzinfo or tzinfo
        )
        reference_date = reference_dt.date()
        reference_time = reference_dt.timetz()

        aware_datetime = datetime.datetime.combine(reference_date, time_object)
        if aware_datetime.tzinfo is None:
            aware_datetime = _localize(aware_datetime, tzinfo)

        # if the time of day has passed today, use tomorrow
        if reference_time > aware_datetime.timetz():
            aware_datetime += datetime.timedelta(days=1)
        return _datetime_to_float_timestamp(aware_datetime)
    if isinstance(time_object, datetime.datetime):
        if time_object.tzinfo is None:
            time_object = _localize(time_object, tzinfo)
        return _datetime_to_float_timestamp(time_object)

    raise TypeError(f'Unable to convert {type(time_object).__name__} object to timestamp')


def to_timestamp(
    dt_obj: Union[int, float, datetime.timedelta, datetime.datetime, datetime.time, None],
    reference_timestamp: float = None,
    tzinfo: datetime.tzinfo = None,
) -> Optional[int]:
    """
    Wrapper over :func:`to_float_timestamp` which returns an integer (the float value truncated
    down to the nearest integer).
    See the documentation for :func:`to_float_timestamp` for more details.
    """
    return (
        int(to_float_timestamp(dt_obj, reference_timestamp, tzinfo))
        if dt_obj is not None
        else None
    )
