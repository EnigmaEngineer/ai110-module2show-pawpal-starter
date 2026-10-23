from datetime import date, timedelta

_MINUTES_PER_DAY = 24 * 60
_DIGITS = "0123456789"


def _parse_hhmm(value: object) -> int:
    """Return minutes after midnight for a zero-padded 'HH:MM' string in 00:00-23:59."""
    if not isinstance(value, str) or len(value) != 5 or value[2] != ":":
        raise ValueError(f"time must be zero-padded 'HH:MM', got {value!r}")
    hh, mm = value[:2], value[3:]
    if any(c not in _DIGITS for c in hh + mm):
        raise ValueError(f"time must be zero-padded 'HH:MM', got {value!r}")
    hour, minute = int(hh), int(mm)
    if hour > 23 or minute > 59:
        raise ValueError(f"time must be between 00:00 and 23:59, got {value!r}")
    return hour * 60 + minute


def _earliest_fit(start: int, duration: int, intervals: list[tuple[int, int]]) -> int | None:
    """Earliest start >= start where [t, t+duration) avoids every [a, b) interval and ends by midnight."""
    t = start
    while t + duration <= _MINUTES_PER_DAY:
        clash = next(((a, b) for a, b in intervals if a < t + duration and t < b), None)
        if clash is None:
            return t
        # Every start in [t, clash_end) still overlaps that block, so jump past it.
        t = clash[1]
    return None


def reschedule_weekly(
    due_date: date,
    time: str,
    duration: int,
    completed_on: date,
    busy: list[tuple[date, str, int]],
    max_weeks: int = 8,
) -> tuple[date, str] | None:
    start_min = _parse_hhmm(time)
    if isinstance(duration, bool) or not isinstance(duration, int) or not 1 <= duration <= _MINUTES_PER_DAY:
        raise ValueError(f"duration must be an integer from 1 to 1440, got {duration!r}")
    if isinstance(max_weeks, bool) or not isinstance(max_weeks, int) or max_weeks < 1:
        raise ValueError(f"max_weeks must be an integer >= 1, got {max_weeks!r}")

    # Validate every busy block up front, then group the clipped intervals by day.
    # Only the part of a block on its own day counts, so clip at midnight.
    by_day: dict[date, list[tuple[int, int]]] = {}
    for day, start, minutes in busy:
        start_m = _parse_hhmm(start)
        if isinstance(minutes, bool) or not isinstance(minutes, int) or minutes <= 0:
            raise ValueError(f"busy minutes must be a positive integer, got {minutes!r}")
        end = min(start_m + minutes, _MINUTES_PER_DAY)
        by_day.setdefault(day, []).append((start_m, end))

    # First candidate: earliest date strictly after max(due, completed) on the due weekday.
    base = max(due_date, completed_on)
    delta = (due_date.weekday() - base.weekday()) % 7 or 7
    first = base + timedelta(days=delta)

    for week in range(max_weeks):
        day = first + timedelta(weeks=week)
        start = _earliest_fit(start_min, duration, by_day.get(day, []))
        if start is not None:
            return day, f"{start // 60:02d}:{start % 60:02d}"
    return None
