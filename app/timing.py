"""Dates and times in club time (Europe/London), never server UTC."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.config import settings


def tz() -> ZoneInfo:
    return ZoneInfo(settings.tz)


def today_london() -> date:
    return datetime.now(tz()).date()


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def when(value: str | None) -> str:
    """'19:02' for today, 'Sat 14 Oct, 19:02' otherwise (London time)."""
    if not value:
        return ""
    local = parse_iso(value).astimezone(tz())
    if local.date() == today_london():
        return local.strftime("%H:%M")
    return local.strftime("%a %-d %b, %H:%M")


def nice_date(value: str) -> str:
    """'2026-10-21' -> 'Wed 21 Oct 2026'."""
    return date.fromisoformat(value).strftime("%a %-d %b %Y")
