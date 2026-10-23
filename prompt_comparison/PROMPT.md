You are writing one pure Python function for a pet-care scheduler. Use Python 3.10+ and the standard library only. The function does no I/O and prints nothing.

```python
from datetime import date

def reschedule_weekly(
    due_date: date,
    time: str,
    duration: int,
    completed_on: date,
    busy: list[tuple[date, str, int]],
    max_weeks: int = 8,
) -> tuple[date, str] | None:
    ...
```

A weekly task was due on `due_date`, starting at `time` ("HH:MM", 24-hour, zero-padded, for example "08:00") and lasting `duration` minutes. The owner completed it on `completed_on`, which may be before, on, or after the due date. `busy` lists blocks that are already booked, each as `(day, "HH:MM" start, minutes)`. Return `(next_date, "HH:MM")`, the date and start time of the task's next occurrence, or `None` if no placement is possible.

Rules:

1. **Weekday is preserved.** The next occurrence falls on the same weekday as `due_date`.
2. **First candidate day.** It is the earliest date that is strictly after `max(due_date, completed_on)` and falls on that weekday. Completing early or on time therefore gives `due_date + 7 days`. Completing late skips forward to the next matching weekday, so the task never lands in the past or on the completion day.
3. **Start time within a day.** On a candidate day the task wants to start at `time`. If the block `[start, start + duration)` overlaps any busy block on that day, move it later: use the earliest start, in whole minutes and at or after `time`, where it fits without overlapping any busy block and ends at or before 24:00 on the same day. Blocks that only touch (one ends exactly when the next starts) do not overlap.
4. **Later weeks.** If no start works on a candidate day, try the same weekday of the following week. Try at most `max_weeks` candidate days in total; the first candidate counts as week 1. If none works, return `None`.
5. **Busy blocks.** They may be unsorted, duplicated, or overlap each other. Blocks on other days are irrelevant. A block may run past midnight (for example start "23:30", 120 minutes): only the part on its own day counts, and it does not occupy the next day.
6. **Output and input checks.** Return the start time as zero-padded "HH:MM". Do not mutate the arguments. Raise `ValueError` for: a `time` that is not zero-padded "HH:MM" between 00:00 and 23:59; a `duration` outside 1 to 1440; a `max_weeks` below 1; a busy block whose start time is malformed or whose minutes are not positive.

Worked examples (2026-03-02 is a Monday):

- Due Monday 2026-03-02 at "08:00" for 30 minutes, completed on 2026-03-02, nothing busy: `(date(2026, 3, 9), "08:00")`.
- Same task completed late on Thursday 2026-03-05: `(date(2026, 3, 9), "08:00")`, which is only 4 days after completion because the weekday is preserved.
- Same task completed on 2026-03-02 with busy `[(date(2026, 3, 9), "08:00", 45)]`: `(date(2026, 3, 9), "08:45")`.

Reply with:

1. One Python code block containing the function and any helpers.
2. A short explanation of your approach.
3. Anything in the rules you found ambiguous, and how you resolved it.
