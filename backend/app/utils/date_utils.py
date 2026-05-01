"""Date utility functions."""

from datetime import datetime, timezone, timedelta


def now_china() -> datetime:
    """Get current time in China timezone (UTC+8)."""
    return datetime.now(timezone(timedelta(hours=8)))


def format_date(dt: datetime, fmt: str = "%Y-%m-%d") -> str:
    """Format a datetime to string."""
    return dt.strftime(fmt)


def format_datetime(dt: datetime, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format a datetime to string with time."""
    return dt.strftime(fmt)
