"""Reference solution for the prompt comparison. The scoring cases and random checks are measured against this."""

import re
from datetime import date, timedelta

_TIME = re.compile(r"([01]\d|2[0-3]):[0-5]\d", re.ASCII)
MINUTES_PER_DAY = 24 * 60


def _minutes(text: str) -> int:
    hours, minutes = text.split(":")
    return int(hours) * 60 + int(minutes)


def reschedule_weekly(
    due_date: date,
    time: str,
    duration: int,
    completed_on: date,
    busy: list[tuple[date, str, int]],
    max_weeks: int = 8,
) -> tuple[date, str] | None:
    if not isinstance(time, str) or not _TIME.fullmatch(time):
        raise ValueError(f"time must be zero-padded HH:MM, got {time!r}")
    if isinstance(duration, bool) or not isinstance(duration, int) or not 1 <= duration <= MINUTES_PER_DAY:
        raise ValueError(f"duration must be 1 to {MINUTES_PER_DAY}, got {duration!r}")
    if isinstance(max_weeks, bool) or not isinstance(max_weeks, int) or max_weeks < 1:
        raise ValueError(f"max_weeks must be at least 1, got {max_weeks!r}")

    blocks: dict[date, list[tuple[int, int]]] = {}
    for day, start_text, minutes in busy:
        if not isinstance(start_text, str) or not _TIME.fullmatch(start_text):
            raise ValueError(f"busy start must be zero-padded HH:MM, got {start_text!r}")
        if isinstance(minutes, bool) or not isinstance(minutes, int) or minutes <= 0:
            raise ValueError(f"busy minutes must be positive, got {minutes!r}")
        start = _minutes(start_text)
        blocks.setdefault(day, []).append((start, min(start + minutes, MINUTES_PER_DAY)))

    wanted = _minutes(time)
    anchor = max(due_date, completed_on)
    ahead = (due_date.weekday() - anchor.weekday()) % 7 or 7
    first = anchor + timedelta(days=ahead)

    for week in range(max_weeks):
        day = first + timedelta(days=7 * week)  # worked out per attempt, so the last attempt never steps past date.max
        start = wanted
        for block_start, block_end in sorted(blocks.get(day, [])):
            if start + duration <= block_start:
                break  # fits in the gap before this block
            start = max(start, block_end)
        if start + duration <= MINUTES_PER_DAY:
            return day, f"{start // 60:02d}:{start % 60:02d}"
    return None
