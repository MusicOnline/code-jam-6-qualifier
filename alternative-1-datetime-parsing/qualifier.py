import datetime
import re

# Proud regex code which factors in all requirements
# (except range of values and truncation consistency to raise errors for)
datetime_regex = re.compile(
    r"""(?x)

    ^
    (?# parse yyyy-mm-dd or yyyymmdd date)
    (?P<year>\d{4})(?P<hyphen>-?)(?P<month>\d{2})(?P=hyphen)(?P<day>\d{2})

    (?# parse hh, hhmm, hh:mm, hhmmss, hh:mm:ss, hhmmss.ssssss or hh:mm:ss.ssssss time)
    (?# seconds up to 6 decimal places)
    (?:
        T
        (?P<hour>\d{2})
        (?:
            (?P<colon>:?) (?# *can be substituted to validate truncation consistency)
            (?P<minute>\d{2})
            (?:
                (?P=colon)
                (?P<second>\d{2})
                (?:\.(?P<subsecond>\d{1,6}))?
            )?
        )?
    )?

    (?# parse Z, ±hh, ±hhmm or ±hh:mm timezone)
    (?P<timezone>Z|
        (?P<sign>\+|-)
        (?P<tz_hour>\d{2})
        (?::?(?P<tz_minute>\d{2}))?
    )?
    $
    """
)
# * substitution:
# (?P<colon>((?<=-\d\dT\d\d):|(?<!-\d\dT\d\d)))
# Python's regex engine does not support lookarounds in conditionals
# Therefore we use two lookarounds with an OR operator


def parse_iso8601(timestamp: str) -> datetime.datetime:
    """Parse an ISO-8601 formatted time stamp."""
    if match := re.match(datetime_regex, timestamp):
        # Check truncation consistency
        date_seperator = match.group("hyphen")  # "-" or ""
        time_seperator = match.group("colon")  # ":", "" or None
        if time_seperator is not None and (bool(date_seperator) != bool(time_seperator)):
            raise ValueError("Date and time must be both truncated or untruncated.")

        # Check year, month and time first because they're simple
        if (year := int(match.group("year"))) < 1:
            raise ValueError("The year value is out of range.")
        if not 1 <= (month := int(match.group("month"))) <= 12:
            raise ValueError("The month value is out of range.")
        if not 0 <= (hour := int(match.group("hour") or 0)) <= 23:
            raise ValueError("The hour value is out of range.")
        if not 0 <= (minute := int(match.group("minute") or 0)) <= 59:
            raise ValueError("The minute value is out of range.")
        if not 0 <= (second := int(match.group("second") or 0)) <= 59:
            # datetime.datetime does not support leap seconds
            raise ValueError("The second value is out of range.")
        
        # Check microsecond
        if (subsec_match := match.group("subsecond")) is not None:
            microsecond = int(float(f"0.{subsec_match}") * 1000000)
        else:
            microsecond = 0

        # Check timezone
        if (timezone := match.group("timezone")) is None:
            tzinfo = None
        elif timezone == "Z":
            tzinfo = datetime.timezone.utc
        else:
            if not 0 <= (tz_hour := int(match.group("tz_hour"))) <= 23:
                raise ValueError("The timezone hour offset value is out of range.")
            if not 0 <= (tz_minute := int(match.group("tz_minute") or 0)) <= 59:
                raise ValueError("The timezone minute offset value is out of range.")
            sign = 1 if match.group("sign") == "+" else -1
            tzinfo = datetime.timezone(
                datetime.timedelta(hours=tz_hour * sign, minutes=tz_minute * sign)
            )

        # Check day with respect to month and leap years
        days_in_february = 28
        if year % 4 == 0:
            days_in_february = 29
        if year % 100 == 0 and year % 400 != 0:
            days_in_february = 28
        days_in_month = {
            1: 31,
            2: days_in_february,
            3: 31,
            4: 30,
            5: 31,
            6: 30,
            7: 31,
            8: 31,
            9: 30,
            10: 31,
            11: 30,
            12: 31,
        }
        if not 1 <= (day := int(match.group("day"))) <= days_in_month[month]:
            raise ValueError("The day value is out of range for the month.")
        return datetime.datetime(
            year=year,
            month=month,
            day=day,
            hour=hour,
            minute=minute,
            second=second,
            microsecond=microsecond,
            tzinfo=tzinfo,
        )

    raise ValueError(
        "The string is not in the format as specified by ISO-8601 "
        "(limited to the requirements in README.md)."
    )
