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
    if max_weeks < 1:
        raise ValueError("max_weeks must be at least 1")
    if not (1 <= duration <= 1440):
        raise ValueError("duration must be between 1 and 1440")

    def parse_time(t_str: str) -> int:
        if not isinstance(t_str, str) or not re.match(r"^\d{2}:\d{2}$", t_str):
            raise ValueError(f"Invalid time format: {t_str}")
        h, m = int(t_str[:2]), int(t_str[3:])
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError(f"Time out of range: {t_str}")
        return h * 60 + m

    req_start = parse_time(time)

    # Validate busy blocks
    validated_busy = []
    for item in busy:
        if not isinstance(item, (list, tuple)) or len(item) != 3:
            raise ValueError("Busy block must be a tuple/list of (date, time, minutes)")
        b_day, b_time, b_mins = item
        b_start = parse_time(b_time)
        if not isinstance(b_mins, int) or b_mins <= 0:
            raise ValueError(f"Busy minutes must be a positive integer: {b_mins}")
        validated_busy.append((b_day, b_start, b_mins))

    # Determine first candidate day
    target_weekday = due_date.weekday()
    start_search = max(due_date, completed_on) + timedelta(days=1)
    days_ahead = (target_weekday - start_search.weekday()) % 7
    first_candidate = start_search + timedelta(days=days_ahead)

    for week in range(max_weeks):
        current_date = first_candidate + timedelta(weeks=week)

        # Gather busy intervals for the current date, capping past-midnight spillage
        busy_intervals = []
        for b_day, b_start, b_mins in validated_busy:
            if b_day == current_date:
                b_end = min(b_start + b_mins, 1440)
                if b_start < 1440:
                    busy_intervals.append((b_start, b_end))

        # Find earliest valid start time on current_date
        s = req_start
        found = False
        while s + duration <= 1440:
            overlapping_end = None
            for b_s, b_e in busy_intervals:
                if max(s, b_s) < min(s + duration, b_e):
                    if overlapping_end is None or b_e > overlapping_end:
                        overlapping_end = b_e
            if overlapping_end is None:
                found = True
                break
            else:
                s = overlapping_end

        if found:
            h = s // 60
            m = s % 60
            return (current_date, f"{h:02d}:{m:02d}")

    return None
