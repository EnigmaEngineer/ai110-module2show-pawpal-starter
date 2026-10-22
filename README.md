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
  - warn about tasks sharing a start time;
  - complete a task, creating the next occurrence of a daily or weekly one on the right pet;
  - build a daily plan and explain it.

**How the plan is built:** pending tasks due today or earlier (overdue tasks stay in until done) are ranked by priority, then oldest due date, then earliest time. They are taken in that order until the owner's available minutes run out, and a task too long for the time left is skipped so smaller ones can still fit. The chosen tasks are then listed in time order, and `explain_plan()` says what was chosen and what was left out.

**Status:** the logic layer, a terminal demo and the tests are done. `app.py` is not connected to the logic layer yet.

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

```bash
# Run the full test suite:
pytest

# Run with coverage:
pytest --cov
```

Sample test output:

```
# Paste your pytest output here
```

## 📐 Smarter Scheduling

> Fill in once you've implemented scheduling logic.

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Task sorting | | e.g., by priority, duration |
| Filtering | | e.g., skip tasks if time runs out |
| Conflict handling | | e.g., overlapping time slots |
| Recurring tasks | | e.g., daily vs. weekly |

## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
