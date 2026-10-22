# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## Implementation Summary

The scheduling logic lives in [`pawpal_system.py`](pawpal_system.py) as four classes (design in [`diagrams/uml.mmd`](diagrams/uml.mmd)):

- **`Task`** is one care activity: description, `HH:MM` time, duration, priority, frequency (`once`/`daily`/`weekly`), due date and completion status. It validates its own fields and can compute its next due date.
- **`Pet`** holds a pet's details and its list of tasks. Adding a task records the pet's name on it.
- **`Owner`** holds several pets and the minutes available per day. `get_all_tasks()` returns every pet's tasks as one flat list, and duplicate pet names are rejected.
- **`Scheduler`** is the brain. It takes an `Owner` and reads every task through `owner.get_all_tasks()`, never from a single pet, so it works across all pets. It can:
  - sort tasks by date and time;
  - filter them by pet or completion status;
  - warn about tasks that share a start time or overlap;
  - complete a task, creating the next occurrence of a daily or weekly one on the right pet;
  - build a daily plan and explain it.

**How the plan is built:** pending tasks due today or earlier (overdue tasks stay in until done) are ranked by priority, then oldest due date, then earliest time. They are taken in that order until the owner's available minutes run out, and a task too long for the time left is skipped so smaller ones can still fit. The chosen tasks are then listed in time order, and `explain_plan()` says what was chosen and what was left out.

**Status:** the logic layer, a terminal demo and the tests are done. `app.py` is connected to the logic layer (the Streamlit UI adds pets and tasks, shows conflict warnings and builds the plan).

```bash
python main.py       # terminal demo; sample output is below
python -m pytest     # run the test suite
```

## 🖥️ Sample Output

Output from `python main.py`, which builds an owner (Sam, 90 minutes available) with two pets and five tasks, then prints today's schedule, conflict warnings, the plan explanation, and the effect of completing a recurring task:

```
Owner: Sam, 90 minutes available

=== Today's Schedule: Thursday, October 22, 2026 ===
  Date    Time   Task          Pet    Min  Priority  Done
  ------  -----  ------------  -----  ---  --------  ----
  Oct 22  08:00  Morning walk  Buddy   30  high      no
  Oct 22  08:00  Breakfast     Mia     10  high      no
  Oct 22  12:30  Medication    Mia      5  high      no
  Oct 22  18:00  Evening walk  Buddy   30  medium    no

  4 tasks, 75 of 90 minutes used

All tasks, sorted by time:
  Date    Time   Task          Pet    Min  Priority  Done
  ------  -----  ------------  -----  ---  --------  ----
  Oct 22  08:00  Morning walk  Buddy   30  high      no
  Oct 22  08:00  Breakfast     Mia     10  high      no
  Oct 22  12:30  Medication    Mia      5  high      no
  Oct 22  16:00  Grooming      Buddy   45  low       no
  Oct 22  18:00  Evening walk  Buddy   30  medium    no

Conflicts:
  Conflict on 2026-10-22 at 08:00: Morning walk (Buddy), Breakfast (Mia)

Plan for 2026-10-22: 4 task(s), 75 of 90 available minutes used.
Tasks were chosen by priority (high first), then oldest due date (overdue first), then earliest time, until time ran out; they are listed in the order they happen.
  [ ] 08:00 Morning walk (Buddy) - 30 min, high
  [ ] 08:00 Breakfast (Mia) - 10 min, high
  [ ] 12:30 Medication (Mia) - 5 min, high
  [ ] 18:00 Evening walk (Buddy) - 30 min, medium
Left out because they did not fit in the available time:
  [ ] 16:00 Grooming (Buddy) - 45 min, low

Completed 'Morning walk'; next occurrence due 2026-10-23

Buddy's pending tasks:
  Date    Time   Task          Pet    Min  Priority  Done
  ------  -----  ------------  -----  ---  --------  ----
  Oct 22  16:00  Grooming      Buddy   45  low       no
  Oct 22  18:00  Evening walk  Buddy   30  medium    no
  Oct 23  08:00  Morning walk  Buddy   30  high      no

Completed tasks:
  Date    Time   Task          Pet    Min  Priority  Done
  ------  -----  ------------  -----  ---  --------  ----
  Oct 22  08:00  Morning walk  Buddy   30  high      yes
```

## 🧪 Testing PawPal+

The tests live in [`tests/test_pawpal.py`](tests/test_pawpal.py) and exercise the logic layer in `pawpal_system.py` directly, with no Streamlit involved. Run them from the project root:

```bash
python -m pytest        # run the full suite
python -m pytest -v     # list each test with PASSED/FAILED
```

### What the tests cover

| Behavior | Happy path | Edge cases |
|----------|------------|------------|
| **Sorting** (`sort_by_time`) | Tasks added out of order, across pets, come back chronologically | Same date and time (priority breaks the tie, then insertion order); earlier date beats earlier time; empty owner; the pets' own lists are not reordered |
| **Recurrence** (`complete_task`, `next_occurrence`) | Completing a daily task adds one pending task for the next day; weekly adds +7 days; the new task goes to the same pet | One-off tasks create nothing; completing twice creates no duplicate; an identical pending next occurrence is reused, not copied; early and late completion; month, year and leap-day rollover; unknown pet raises and leaves the task pending |
| **Conflict detection** (`detect_conflicts`) | Two pending tasks at the same date and time produce one warning naming both, within one pet or across pets | Back-to-back tasks, completed tasks and other dates are ignored; three tasks in one slot give one warning; a long task that runs into later tasks is flagged once per task; overlap is cut off at midnight; no pets or tasks returns `[]` |
| **Daily plan** (`generate_plan`, `explain_plan`) | Tasks that fit are listed in time order; the explanation reports minutes used and what was left out | Budget used exactly or zero; a too-long task is skipped but smaller ones still fit; overdue tasks are included and come first at equal priority; completed and future tasks are excluded |
| **Validation and filtering** | Valid tasks are accepted; `filter_tasks` narrows by pet and/or status | Bad times (`9:00`, `24:00`, `12:60`), non-positive durations, unknown priority or frequency; duplicate pet names ignoring case |

Tests that go through `complete_task` freeze `date.today()` (the `frozen_today` fixture), so results do not depend on the day they run.

### Sample test output

```
============================= test session starts =============================
platform win32 -- Python 3.13.14, pytest-9.1.0, pluggy-1.6.0
rootdir: C:\Users\syeds\Documents\Projects\ai110-module2show-pawpal-starter
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.14.1, locust-2.44.4, asyncio-1.4.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 138 items

tests\test_pawpal.py ................................................... [ 36%]
........................................................................ [ 89%]
...............                                                          [100%]

============================= 138 passed in 0.14s =============================
```

## 📐 Smarter Scheduling

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Task sorting | `Scheduler.sort_by_time()` | Orders every pet's tasks by due date, then time of day, then priority (high first). Reads tasks through `Owner.get_all_tasks()`. |
| Filtering | `Scheduler.filter_tasks(pet_name, status)` | Narrows tasks by pet name (whole name, ignoring case) and/or completion status; pass neither to get everything. Results keep insertion order. |
| Conflict handling | `Scheduler.detect_conflicts()` | Returns warning strings across all pets and never raises. Completed tasks are ignored. Tasks that share a start time give a `Conflict` warning; a task that starts after another begins but before it ends gives an `Overlap` warning. A task that ends exactly when the next begins is fine, and only the due date's own day is checked (a task running past midnight is cut off at 24:00). |
| Recurring tasks | `Scheduler.complete_task()`, `Task.next_occurrence()` | Completing a daily or weekly task adds the next one to the same pet, 1 or 7 days after the later of its due date and today, so a late completion never schedules into the past. One-off tasks create nothing, completing a task twice does nothing, and if the pet already has an identical pending task on that date it is returned instead of adding a copy. |

## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
