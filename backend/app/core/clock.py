"""The business date, independent of the server's time zone."""

from datetime import date, datetime, timedelta, timezone

# Colombia is UTC-5 all year (no daylight saving). A fixed offset also avoids
# needing the tzdata package on Windows, which zoneinfo would require.
COLOMBIA = timezone(timedelta(hours=-5))


def today() -> date:
    """Today in Colombia. On a UTC server, date.today() is tomorrow after 7 p.m."""
    return datetime.now(COLOMBIA).date()
