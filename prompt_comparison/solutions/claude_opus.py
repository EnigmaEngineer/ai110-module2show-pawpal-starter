import re
from datetime import date, timedelta

_TIME_RE = re.compile(r"[0-9]{2}:[0-9]{2}")
_DAY_MINUTES = 1440


def _parse_hhmm(value: object, what: str) -> int:
    """Return minutes since midnight for a zero-padded "HH:MM" string."""
    if not isinstance(value, str) or not _TIME_RE.fullmatch(value):
        raise ValueError(f"{what} must be zero-padded 'HH:MM', got {value!r}")
    hours, minutes = int(value[:2]), int(value[3:])
    if hours > 23 or minutes > 59:
        raise ValueError(f"{what} out of range: {value!r}")
    return hours * 60 + minutes


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _earliest_start(want: int, duration: int, blocks: list[tuple[int, int]]) -> int | None:
    """Earliest start >= want so [start, start+duration) avoids all blocks
    (half-open, sorted by start) and ends by 24:00; None if impossible."""
    start = want
    for b_start, b_end in blocks:
        if b_start >= start + duration:
            break  # this and every later block start after the slot
        if b_end > start:  # overlap: jump past this block
            start = b_end
    return start if start + duration <= _DAY_MINUTES else None


def reschedule_weekly(
    due_date: date,
    time: str,
    duration: int,
    completed_on: date,
    busy: list[tuple[date, str, int]],
    max_weeks: int = 8,
) -> tuple[date, str] | None:
    want = _parse_hhmm(time, "time")
    if not _is_int(duration) or not 1 <= duration <= _DAY_MINUTES:
        raise ValueError(f"duration must be 1..1440 minutes, got {duration!r}")
    if not _is_int(max_weeks) or max_weeks < 1:
        raise ValueError(f"max_weeks must be at least 1, got {max_weeks!r}")

    # Validate every busy block and index the in-day part by date.
    by_day: dict[date, list[tuple[int, int]]] = {}
    for day, start_str, minutes in busy:
        b_start = _parse_hhmm(start_str, "busy block start")
        if not _is_int(minutes) or minutes <= 0:
            raise ValueError(f"busy block minutes must be positive, got {minutes!r}")
        b_end = min(b_start + minutes, _DAY_MINUTES)  # clip at midnight
        by_day.setdefault(day, []).append((b_start, b_end))

    base = max(due_date, completed_on)
    ahead = (due_date.weekday() - base.weekday()) % 7 or 7
    candidate = base + timedelta(days=ahead)

    for _ in range(max_weeks):
        blocks = sorted(by_day.get(candidate, ()))
        start = _earliest_start(want, duration, blocks)
        if start is not None:
            return candidate, f"{start // 60:02d}:{start % 60:02d}"
        candidate += timedelta(weeks=1)
    return None
