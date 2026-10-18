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


def day_short(value: str) -> str:
    return date.fromisoformat(value).strftime("%a")


def day_num(value: str) -> str:
    return str(date.fromisoformat(value).day)


def month_short(value: str) -> str:
    return date.fromisoformat(value).strftime("%b")


def clock(start_time: str, minutes: int) -> str:
    """'19:30' + 50 → '20:20' (wraps past midnight)."""
    h, m = (int(x) for x in start_time.split(":"))
    total = (h * 60 + m + minutes) % (24 * 60)
    return f"{total // 60:02d}:{total % 60:02d}"


def layout(durations: list[int], start_time: str) -> dict:
    """Relative and clock ranges for each block, plus the session total and end.

    Nothing time-based is stored (D9): reordering or changing a duration simply
    changes what this returns on the next render.
    """
    rows, elapsed = [], 0
    for minutes in durations:
        rows.append({
            "rel_start": elapsed, "rel_end": elapsed + minutes,
            "clock_start": clock(start_time, elapsed), "clock_end": clock(start_time, elapsed + minutes),
        })
        elapsed += minutes
    return {"blocks": rows, "total": elapsed, "end": clock(start_time, elapsed)}


def double_booked(groups: list[dict]) -> set[int]:
    """Coach ids on more than one group in the same block (D10)."""
    seen, twice = set(), set()
    for g in groups:
        for c in g["coaches"]:
            (twice if c["id"] in seen else seen).add(c["id"])
    return twice
