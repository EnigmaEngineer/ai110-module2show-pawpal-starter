from datetime import date, timedelta
import re


def reschedule_weekly(
    due_date: date,
    time: str,
    duration: int,
    completed_on: date,
    busy: list[tuple[date, str, int]],
    max_weeks: int = 8,
) -> tuple[date, str] | None:
    """Find the next available weekly occurrence, preserving the weekday."""

    def parse_time(value: str) -> int:
        """Validate HH:MM and return minutes since midnight."""
        if not isinstance(value, str) or not re.fullmatch(
            r"(?:[01]\d|2[0-3]):[0-5]\d", value
        ):
            raise ValueError("Time must be zero-padded HH:MM between 00:00 and 23:59.")

        hours, minutes = map(int, value.split(":"))
        return hours * 60 + minutes

    # Validate inputs.
    preferred_start = parse_time(time)

    if not isinstance(duration, int) or isinstance(duration, bool) or not 1 <= duration <= 1440:
        raise ValueError("Duration must be an integer between 1 and 1440.")

    if not isinstance(max_weeks, int) or isinstance(max_weeks, bool) or max_weeks < 1:
        raise ValueError("max_weeks must be a positive integer.")

    # Normalize and validate busy blocks without modifying the input.
    busy_by_day: dict[date, list[tuple[int, int]]] = {}

    for day, start, minutes in busy:
        block_start = parse_time(start)

        if (
            not isinstance(minutes, int)
            or isinstance(minutes, bool)
            or minutes <= 0
        ):
            raise ValueError("Busy block duration must be a positive integer.")

        # Only the portion before midnight occupies this day.
        block_end = min(block_start + minutes, 1440)
        busy_by_day.setdefault(day, []).append((block_start, block_end))

    # Start on the first matching weekday strictly after both dates.
    reference_date = max(due_date, completed_on)
    days_until_weekday = (due_date.weekday() - reference_date.weekday()) % 7

    if days_until_weekday == 0:
        days_until_weekday = 7

    candidate_day = reference_date + timedelta(days=days_until_weekday)

    # Try no more than max_weeks candidate days.
    for _ in range(max_weeks):
        blocks = sorted(busy_by_day.get(candidate_day, []))
        start = preferred_start

        for block_start, block_end in blocks:
            # A block ending at our start does not overlap.
            if start + duration <= block_start:
                break

            # A block beginning at or before our end may overlap.
            if start < block_end and start + duration > block_start:
                start = block_end

        # The task must fit entirely within the candidate day.
        if start + duration <= 1440:
            hours, minutes = divmod(start, 60)
            return candidate_day, f"{hours:02d}:{minutes:02d}"

        candidate_day += timedelta(days=7)

    return None
