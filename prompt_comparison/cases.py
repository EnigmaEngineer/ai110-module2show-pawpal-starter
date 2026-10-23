"""Hand-computed scoring cases for reschedule_weekly. Expected values come from the rules in PROMPT.md, not from reference.py."""

from datetime import date, timedelta

M = date(2026, 3, 2)  # a Monday


def d(n: int) -> date:
    """The date n days after Monday 2026-03-02."""
    return M + timedelta(days=n)


def base(**overrides):
    """Arguments for a task due Monday 08:00 for 30 minutes, completed on its due date, with nothing busy."""
    args = dict(due_date=M, time="08:00", duration=30, completed_on=M, busy=[])
    args.update(overrides)
    return args


FULL_DAY = lambda day: (day, "00:00", 1440)

# (category, name, keyword arguments, expected). Expected is (date, "HH:MM"), None, or ValueError.
CASES = [
    # --- which day: weekday preserved, strictly after the later of due and completion ---------------------------
    ("dates", "completed early", base(completed_on=d(-1)), (d(7), "08:00")),
    ("dates", "completed on the due date", base(), (d(7), "08:00")),
    ("dates", "one day late", base(completed_on=d(1)), (d(7), "08:00")),
    ("dates", "three days late", base(completed_on=d(3)), (d(7), "08:00")),
    ("dates", "six days late", base(completed_on=d(6)), (d(7), "08:00")),
    ("dates", "exactly a week late lands on the next Monday after", base(completed_on=d(7)), (d(14), "08:00")),
    ("dates", "eight days late", base(completed_on=d(8)), (d(14), "08:00")),
    ("dates", "twenty days late", base(completed_on=d(20)), (d(21), "08:00")),
    ("dates", "three weeks late on a Monday", base(completed_on=d(21)), (d(28), "08:00")),
    ("dates", "a thousand days late", base(completed_on=d(1000)), (d(1001), "08:00")),
    ("dates", "a year early", base(completed_on=d(-400)), (d(7), "08:00")),
    ("dates", "Thursday task completed on its day", base(due_date=d(3), completed_on=d(3)), (d(10), "08:00")),
    ("dates", "Thursday task completed Friday", base(due_date=d(3), completed_on=d(4)), (d(10), "08:00")),
    ("dates", "Thursday task completed early on Wednesday", base(due_date=d(3), completed_on=d(2)), (d(10), "08:00")),
    ("dates", "Thursday task completed the next Thursday", base(due_date=d(3), completed_on=d(10)), (d(17), "08:00")),
    ("dates", "year boundary", base(due_date=date(2026, 12, 30), completed_on=date(2026, 12, 31)), (date(2027, 1, 6), "08:00")),
    ("dates", "leap day is skipped over", base(due_date=date(2028, 2, 28), completed_on=date(2028, 2, 28)), (date(2028, 3, 6), "08:00")),
    ("dates", "task due on the leap day", base(due_date=date(2028, 2, 29), completed_on=date(2028, 2, 29)), (date(2028, 3, 7), "08:00")),
    ("dates", "no leap day in a normal year", base(due_date=date(2027, 2, 22), completed_on=date(2027, 2, 22)), (date(2027, 3, 1), "08:00")),

    # --- where in the day: pushed past busy blocks ----------------------------------------------------------------
    ("busy", "block at the same start", base(busy=[(d(7), "08:00", 30)]), (d(7), "08:30")),
    ("busy", "block ending exactly at the start is not an overlap", base(busy=[(d(7), "07:30", 30)]), (d(7), "08:00")),
    ("busy", "block starting exactly at the end is not an overlap", base(busy=[(d(7), "08:30", 30)]), (d(7), "08:00")),
    ("busy", "block overlapping the start", base(busy=[(d(7), "07:45", 30)]), (d(7), "08:15")),
    ("busy", "block overlapping the end", base(busy=[(d(7), "08:15", 30)]), (d(7), "08:45")),
    ("busy", "short block inside the task", base(busy=[(d(7), "08:10", 5)]), (d(7), "08:15")),
    ("busy", "block entirely later does not matter", base(busy=[(d(7), "09:00", 30)]), (d(7), "08:00")),
    ("busy", "long block that began earlier", base(busy=[(d(7), "06:00", 300)]), (d(7), "11:00")),
    ("busy", "chain of back-to-back blocks", base(busy=[(d(7), "08:00", 30), (d(7), "08:30", 30), (d(7), "09:00", 15)]), (d(7), "09:15")),
    ("busy", "a gap that fits exactly is used", base(busy=[(d(7), "08:00", 30), (d(7), "09:00", 30)]), (d(7), "08:30")),
    ("busy", "a gap one minute too small is skipped", base(busy=[(d(7), "08:00", 30), (d(7), "08:59", 30)]), (d(7), "09:29")),
    ("busy", "unsorted, duplicated and overlapping blocks",
     base(busy=[(d(7), "09:00", 30), (d(7), "08:00", 30), (d(7), "08:00", 30), (d(7), "08:20", 40), (d(7), "09:10", 10)]), (d(7), "09:30")),
    ("busy", "blocks on other days are ignored",
     base(busy=[(d(6), "08:00", 30), (d(8), "08:00", 30), (d(0), "08:00", 30), (d(14), "08:00", 30)]), (d(7), "08:00")),
    ("busy", "output is zero-padded", base(busy=[(d(7), "08:00", 65)]), (d(7), "09:05")),
    ("busy", "a block on the due date itself is not the target day", base(busy=[(M, "08:00", 30)]), (d(7), "08:00")),
    ("busy", "a busy block for the day before is ignored for the late case", base(completed_on=d(3), busy=[(d(3), "08:00", 30)]), (d(7), "08:00")),

    # --- days that are full, and how many weeks to try ------------------------------------------------------------
    ("weeks", "full first day moves a week", base(busy=[FULL_DAY(d(7))]), (d(14), "08:00")),
    ("weeks", "three full weeks with max_weeks=3 gives up", base(busy=[FULL_DAY(d(7)), FULL_DAY(d(14)), FULL_DAY(d(21))], max_weeks=3), None),
    ("weeks", "three full weeks with max_weeks=4 finds the fourth", base(busy=[FULL_DAY(d(7)), FULL_DAY(d(14)), FULL_DAY(d(21))], max_weeks=4), (d(28), "08:00")),
    ("weeks", "max_weeks=1 and a free day", base(max_weeks=1), (d(7), "08:00")),
    ("weeks", "max_weeks=1 and a full day", base(busy=[FULL_DAY(d(7))], max_weeks=1), None),
    ("weeks", "default tries eight weeks, seventh full, eighth free", base(busy=[FULL_DAY(d(7 * k)) for k in range(1, 8)]), (d(56), "08:00")),
    ("weeks", "default gives up after eight full weeks", base(busy=[FULL_DAY(d(7 * k)) for k in range(1, 9)]), None),
    # Added after the comparison, when a reviewer spotted that one answer steps a week past its last attempt: 9999-12-31 is the
    # last date Python can represent, so that step raises OverflowError where the rules say to return None.
    ("weeks", "full last representable day with max_weeks=1 returns None, not an error",
     base(due_date=date(9999, 12, 24), completed_on=date(9999, 12, 24), busy=[FULL_DAY(date(9999, 12, 31))], max_weeks=1), None),
    ("weeks", "late completion counts weeks from the first candidate", base(completed_on=d(10), busy=[FULL_DAY(d(14))], max_weeks=2), (d(21), "08:00")),

    # --- the end of the day ---------------------------------------------------------------------------------------
    ("night", "last slot of the day", base(time="23:00", busy=[(d(7), "23:00", 30)]), (d(7), "23:30")),
    ("night", "ends exactly at midnight", base(time="23:00", duration=60), (d(7), "23:00")),
    ("night", "would run past midnight so moves a week", base(time="23:00", duration=60, busy=[(d(7), "23:00", 15)]), (d(14), "23:00")),
    ("night", "can never fit before midnight", base(time="23:30", duration=31), None),
    ("night", "one minute at 23:59", base(time="23:59", duration=1), (d(7), "23:59")),
    ("night", "one minute at 23:59 with that minute busy", base(time="23:59", duration=1, busy=[(d(7), "23:59", 1)]), (d(14), "23:59")),
    ("night", "yesterday's late block does not spill into today", base(time="00:00", busy=[(d(6), "23:30", 120)]), (d(7), "00:00")),
    ("night", "a block running past its own day only counts until midnight", base(time="23:00", busy=[(d(7), "23:30", 120)]), (d(7), "23:00")),
    ("night", "a block past midnight still blocks its own evening", base(time="23:15", busy=[(d(7), "23:30", 120)]), (d(14), "23:15")),
    ("night", "a whole-day task at midnight", base(time="00:00", duration=1440), (d(7), "00:00")),
    ("night", "a whole-day task that starts later can never fit", base(time="08:00", duration=1440), None),
    ("night", "a whole-day task blocked by one minute", base(time="00:00", duration=1440, busy=[(d(7), "23:59", 1)]), (d(14), "00:00")),
    ("night", "midnight start with a block at midnight", base(time="00:00", duration=30, busy=[(d(7), "00:00", 15)]), (d(7), "00:15")),

    # --- bad input ------------------------------------------------------------------------------------------------
    *[("validation", f"time {t!r}", base(time=t), ValueError) for t in ("8:00", "24:00", "12:60", "08:00 ", "", "0800", "08:0", "ab:cd", 800, None)],
    *[("validation", f"duration {n!r}", base(duration=n), ValueError) for n in (0, -5, 1441, 100000)],
    *[("validation", f"max_weeks {n!r}", base(max_weeks=n), ValueError) for n in (0, -1)],
    *[("validation", f"busy start {t!r}", base(busy=[(d(7), t, 30)]), ValueError) for t in ("9:00", "25:00", "08:60", "", None)],
    *[("validation", f"busy minutes {n!r}", base(busy=[(d(7), "09:00", n)]), ValueError) for n in (0, -10)],
    ("validation", "a malformed block on an irrelevant day still raises", base(busy=[(d(100), "9:00", 30)]), ValueError),
    # Added after reading the Gemini answer, which accepts a time followed by a newline. Rule 6 already says a time that is not
    # exactly zero-padded "HH:MM" must raise, so these two were a gap in my first list of bad inputs, not a new rule.
    ("validation", "time followed by a newline", base(time="08:00\n"), ValueError),
    ("validation", "busy start followed by a newline", base(busy=[(d(7), "09:00\n", 30)]), ValueError),
    ("validation", "valid boundary values are accepted", base(time="00:00", duration=1, max_weeks=1), (d(7), "00:00")),
]
