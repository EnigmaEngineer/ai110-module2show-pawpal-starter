# 🐾 PawPal+

PawPal+ is a pet-care planner for busy owners. Enter your pets and their care tasks (walks, feeding, medication, grooming), and PawPal+ builds a daily plan that fits your available time, puts the most important tasks first, warns you about clashes, and explains every choice it made.

It has two parts: a scheduling engine in plain Python ([`pawpal_system.py`](pawpal_system.py)) and a [Streamlit](https://streamlit.io) web app ([`app.py`](app.py)) on top of it.

## Contents

- [Features](#features)
- [Requirements and installation](#requirements-and-installation)
- [Demo walkthrough](#-demo-walkthrough)
- [How the scheduler decides](#how-the-scheduler-decides)
- [Data persistence](#data-persistence)
- [Architecture](#architecture)
- [Testing](#testing)
- [Project structure](#project-structure)
- [Limitations](#limitations)

## Features

Each feature below names the algorithm behind it, so you know exactly what the app does.

- **Sorting by time.** Tasks from every pet are merged into one list and ordered by due date, then time of day, then priority (high first). Times are stored as zero-padded `HH:MM`, so they sort correctly as text. Ties keep the order the tasks were added.
- **Priority-first sorting.** A second ordering for the task list: high-priority tasks first, then medium, then low. Within a priority, an older due date comes first (overdue tasks surface), then the earlier time of day, and tasks that tie on all three keep the order they were added. Priority always outranks time, so a 21:00 high-priority task is listed before a 07:00 low-priority one. Choose it with **Order by** in the app or call `sort_by_priority()` in code.
- **Filtering.** Narrow the list to one pet (whole name, ignoring case) and/or to completed or pending tasks. The engine returns matches in the order tasks were added, and the app then lists them in time order.
- **Conflict warnings.** Two checks run over pending tasks only (completed tasks are ignored):
  - *Same start:* tasks are grouped by date and start time, and any group of two or more gives a `Conflict` warning, even across different pets.
  - *Overlap:* on each day, tasks are ordered by start and each one is compared with the tasks that start after it. If a later task starts before the earlier one ends, you get an `Overlap` warning such as "Long walk 09:00-10:00 runs into Feed at 09:30". A task that ends exactly when the next begins is not a conflict, and a task running past midnight is cut off at 24:00.
- **Free-slot suggestion.** When a task you add clashes, the app walks through that day's pending tasks in start order and returns the first time at or after the task's start where its full duration fits. If nothing fits before midnight, it says so.
- **Daily recurrence.** Completing a daily or weekly task adds the next one to the same pet, dated one or seven days after the *later* of its due date and today, so completing late never schedules into the past. Month ends, year ends and leap days are handled by date arithmetic. One-off tasks create nothing, completing a task twice does nothing, and an identical pending next task is reused instead of duplicated.
- **Daily plan.** Pending tasks due today or earlier (overdue ones stay in) are ranked by priority, then oldest due date, then earliest time, and taken in that order until your available minutes run out. A task that is too long for the time left is skipped so shorter ones can still fit. This is a greedy choice: it favors priority and is not guaranteed to pack the most minutes. The chosen tasks are then shown in the order they happen.
- **Weighted prioritization with aging.** An optional second way to choose the plan. Each task gets a score: priority points (high 10, medium 5, low 2) plus 1 point for every day it is overdue. Tasks are taken highest score first until the minutes run out, so a low-priority task that keeps getting skipped slowly gains points and eventually wins a slot (a low task 5 days overdue scores 7 and beats a medium task due today at 5), while a high-priority task still beats a low one that is only a week late. Ties go to the older due date. Without overdue tasks it gives the same plan as strict priority. Pick it with **Planning style** in the app or `weighted=True` in code.
- **Plan explanation.** The plan states how many of your minutes it uses, which tasks are overdue, and which tasks were left out for lack of time.
- **Saved data.** Pets, tasks, your name and your time budget are saved to `data.json` automatically and loaded the next time you start the app, so nothing is lost between runs. The file is written safely (a crash cannot leave a half-written file) and a damaged or invalid file is never silently overwritten. See [Data persistence](#data-persistence).
- **Readable output.** Both the web app and the terminal demo mark each task with an icon for the kind of care (walk, meal, medicine, grooming and so on), a colour-coded priority (🔴 🟡 🟢) and a status (✅ done, ⏳ pending, 🚨 overdue), with a task tally and a time-budget gauge. Terminal tables are boxed with `tabulate`. See [Friendly output](#friendly-output-icons-colours-and-tables).
- **Input validation.** Tasks reject a time that isn't `HH:MM`, a duration of zero or less, and an unknown priority or repeat setting. An owner rejects a second pet with the same name, ignoring case.

## Requirements and installation

- Python 3.10 or newer
- The packages in [`requirements.txt`](requirements.txt): `streamlit` (the web app), `pytest` (the tests), and `tabulate` and `wcwidth` (the terminal tables; both optional, see below)

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Start the app from the project root:

```bash
streamlit run app.py
```

Streamlit prints a local address (usually http://localhost:8501) and opens it in your browser.

## 📸 Demo Walkthrough

This walkthrough shows what PawPal+ does, first through the web app and then through the terminal demo. Everything below was run against the code in this repository.

### What you can do in the app

Start it with `streamlit run app.py`. The page is one scrolling screen, top to bottom:

| Area | What you can do |
|------|-----------------|
| **Owner** | Enter your name and the **minutes available today**, which caps the daily plan. |
| **Pets** | Add pets with a name, species (dog, cat, other) and age. A table lists each pet and its task count. Duplicate names are rejected. |
| **Tasks** | Add a task for a pet: description, time, duration (1 to 240 minutes), priority (low, medium, high) and repeat (once, daily, weekly). Invalid input shows an error instead of being saved. |
| **Conflict banner** | Warns about tasks that start together or overlap, and says "No scheduling conflicts." when the day is clear. When a task you just added clashes, it also suggests the next free slot. |
| **Task list** | Shows every pet's tasks sorted by date and time, or high priority first (**Order by**), under a count of pending, overdue and done tasks. Each task has an icon for the kind of care and a colour-coded priority and status. Filter with **Show pet** and **Show tasks** (All, Pending, Completed). |
| **Mark a task done** | Complete a task. If it repeats, the next one is added automatically. |
| **Saved data** | Everything is saved automatically as you work. An expander at the bottom explains where, and lets you delete all saved data (after ticking a confirmation box). |
| **Build Schedule** | Choose a **Planning style** (strict priority, or priority with aging), then **Generate schedule** to see the tasks that fit in your minutes, in the order they happen, with a **Why this plan?** explanation. |

### Example workflow

Sam has 90 minutes today and two pets.

1. **Set up the owner.** Enter the name `Sam` and set **Minutes available today** to `90`.
2. **Add the pets.** Add `Buddy` (dog) and `Mia` (cat). The pets table shows both with 0 tasks.
3. **Schedule the first task.** For Buddy, add "Morning walk" at 08:00, 30 minutes, high priority, repeating daily. The page confirms it, and no conflict is reported.
4. **Cause a conflict on purpose.** For Mia, add "Breakfast" at 08:00, 10 minutes, high priority. A warning appears right away: `Conflict on 2026-10-22 at 08:00: Morning walk (Buddy), Breakfast (Mia)`, together with `Next free slot for 10 min after 08:00: 08:30.`
5. **Add the rest of the day.** Mia: "Medication" at 12:30, 5 minutes, high. Buddy: "Grooming" at 16:00, 45 minutes, low. Buddy: "Evening walk" at 18:00, 30 minutes, medium. The task list stays in time order however you add them.
6. **Filter the list.** Set **Show pet** to `Mia` to see only Breakfast and Medication, then set it back to **All pets**.
7. **View today's schedule.** Press **Generate schedule**. The result is `4 task(s), 75 of 90 minutes used.`: Morning walk, Breakfast, Medication and Evening walk. Grooming (45 minutes) is left out because only 15 minutes remain, and the **Why this plan?** panel says so.
8. **Complete a recurring task.** Under **Mark a task done**, choose "Morning walk" and press **Mark complete**. The page says the next daily one is due tomorrow, and a new "Morning walk" appears in the list.
9. **Close it and come back.** Stop the app (`Ctrl+C`) and start it again with `streamlit run app.py`. Your pets, tasks, completion status, name and available minutes are all back, because they were saved to `data.json` as you worked.

### Scheduler behaviors on display

| Behavior | Where you see it |
|----------|------------------|
| **Sorting by time** | Step 5: tasks added in any order are listed by date, then time, then priority. |
| **Conflict warnings** | Step 4: two tasks starting at 08:00 trigger a warning, even though they belong to different pets. Overlapping tasks with different start times are flagged too. |
| **Free-slot suggestion** | Step 4: 08:30 is the first time a 10-minute task fits after the 30-minute walk. |
| **Priority-first sorting** | Step 5: switch **Order by** to *Priority first* and the high-priority tasks (Morning walk, Breakfast, Medication) move to the top, with the low-priority Grooming last. |
| **Filtering** | Step 6: narrow the list by pet and by completion status. |
| **Priority-based planning** | Step 7: high-priority tasks are chosen first, and the 45-minute low-priority task is the one dropped. |
| **Plan explanation** | Step 7: the panel reports minutes used and lists what was left out. |
| **Weighted prioritization** | Switch **Planning style** to *Priority with aging* in step 7. With no overdue tasks the plan is the same; the terminal demo below shows a case where an overdue low-priority task wins. |
| **Data persistence** | Step 9: pets, tasks, completion status and settings survive a restart. |
| **Daily recurrence** | Step 8: completing a daily task creates the next occurrence on the same pet. Completing it again does nothing. |

### Terminal demo output

[`main.py`](main.py) runs the same engine without the web app. It builds Sam's day from the workflow above, then checks sorting, priority-first sorting, daily recurrence, late completion, conflict warnings, overlap detection with free-slot search, weighted planning and saving and loading. The next section picks out the sections that show the enhanced scheduling logic. Run it with:

```bash
python main.py
```

Output:

```
Owner: Sam, 90 minutes available
Priority: 🔴 high  🟡 medium  🟢 low    Status: ✅ done  ⏳ pending  🚨 overdue


=== Today's Schedule: Friday, October 23, 2026 ===
  ╭────────┬────────┬────────┬──────────────┬───────┬───────┬────────────┬────────────╮
  │ Date   │ Time   │ Type   │ Task         │ Pet   │   Min │ Priority   │ Status     │
  ├────────┼────────┼────────┼──────────────┼───────┼───────┼────────────┼────────────┤
  │ Oct 23 │ 08:00  │ 🦮     │ Morning walk │ Buddy │    30 │ 🔴 High    │ ⏳ Pending │
  │ Oct 23 │ 08:00  │ 🍖     │ Breakfast    │ Mia   │    10 │ 🔴 High    │ ⏳ Pending │
  │ Oct 23 │ 12:30  │ 💊     │ Medication   │ Mia   │     5 │ 🔴 High    │ ⏳ Pending │
  │ Oct 23 │ 18:00  │ 🦮     │ Evening walk │ Buddy │    30 │ 🟡 Medium  │ ⏳ Pending │
  ╰────────┴────────┴────────┴──────────────┴───────┴───────┴────────────┴────────────╯

  📋 4 tasks   ⏳ 4 pending   ✅ 0 done   🚨 0 overdue
  Time budget  [█████████████████░░░] 75 of 90 min (83%)

All tasks, sorted by time:
  ╭────────┬────────┬────────┬──────────────┬───────┬───────┬────────────┬────────────╮
  │ Date   │ Time   │ Type   │ Task         │ Pet   │   Min │ Priority   │ Status     │
  ├────────┼────────┼────────┼──────────────┼───────┼───────┼────────────┼────────────┤
  │ Oct 23 │ 08:00  │ 🦮     │ Morning walk │ Buddy │    30 │ 🔴 High    │ ⏳ Pending │
  │ Oct 23 │ 08:00  │ 🍖     │ Breakfast    │ Mia   │    10 │ 🔴 High    │ ⏳ Pending │
  │ Oct 23 │ 12:30  │ 💊     │ Medication   │ Mia   │     5 │ 🔴 High    │ ⏳ Pending │
  │ Oct 23 │ 16:00  │ 🛁     │ Grooming     │ Buddy │    45 │ 🟢 Low     │ ⏳ Pending │
  │ Oct 23 │ 18:00  │ 🦮     │ Evening walk │ Buddy │    30 │ 🟡 Medium  │ ⏳ Pending │
  ╰────────┴────────┴────────┴──────────────┴───────┴───────┴────────────┴────────────╯

Conflicts:
  Conflict on 2026-10-23 at 08:00: Morning walk (Buddy), Breakfast (Mia)

Plan for 2026-10-23: 4 task(s), 75 of 90 available minutes used.
Tasks were chosen by priority (high first), then oldest due date (overdue first), then earliest time, until time ran out; they are listed in the order they happen.
  [ ] 08:00 Morning walk (Buddy) - 30 min, high
  [ ] 08:00 Breakfast (Mia) - 10 min, high
  [ ] 12:30 Medication (Mia) - 5 min, high
  [ ] 18:00 Evening walk (Buddy) - 30 min, medium
Left out because they did not fit in the available time:
  [ ] 16:00 Grooming (Buddy) - 45 min, low

Completed 'Morning walk'; next occurrence due 2026-10-24

Buddy's pending tasks:
  ╭────────┬────────┬────────┬──────────────┬───────┬───────┬────────────┬────────────╮
  │ Date   │ Time   │ Type   │ Task         │ Pet   │   Min │ Priority   │ Status     │
  ├────────┼────────┼────────┼──────────────┼───────┼───────┼────────────┼────────────┤
  │ Oct 23 │ 16:00  │ 🛁     │ Grooming     │ Buddy │    45 │ 🟢 Low     │ ⏳ Pending │
  │ Oct 23 │ 18:00  │ 🦮     │ Evening walk │ Buddy │    30 │ 🟡 Medium  │ ⏳ Pending │
  │ Oct 24 │ 08:00  │ 🦮     │ Morning walk │ Buddy │    30 │ 🔴 High    │ ⏳ Pending │
  ╰────────┴────────┴────────┴──────────────┴───────┴───────┴────────────┴────────────╯

Completed tasks:
  ╭────────┬────────┬────────┬──────────────┬───────┬───────┬────────────┬──────────╮
  │ Date   │ Time   │ Type   │ Task         │ Pet   │   Min │ Priority   │ Status   │
  ├────────┼────────┼────────┼──────────────┼───────┼───────┼────────────┼──────────┤
  │ Oct 23 │ 08:00  │ 🦮     │ Morning walk │ Buddy │    30 │ 🔴 High    │ ✅ Done  │
  ╰────────┴────────┴────────┴──────────────┴───────┴───────┴────────────┴──────────╯

=== Sorting check ===

Insertion order:
  ╭────────┬────────┬────────┬──────────────┬───────┬───────┬────────────┬────────────╮
  │ Date   │ Time   │ Type   │ Task         │ Pet   │   Min │ Priority   │ Status     │
  ├────────┼────────┼────────┼──────────────┼───────┼───────┼────────────┼────────────┤
  │ Oct 23 │ 18:00  │ 🍖     │ Dinner       │ Buddy │    15 │ 🟡 Medium  │ ⏳ Pending │
  │ Oct 23 │ 08:00  │ 🍖     │ Breakfast    │ Buddy │    15 │ 🟡 Medium  │ ⏳ Pending │
  │ Oct 23 │ 12:30  │ 🦮     │ Lunch walk   │ Buddy │    15 │ 🟡 Medium  │ ⏳ Pending │
  │ Oct 23 │ 09:00  │ 🐾     │ Coffee break │ Buddy │    15 │ 🟡 Medium  │ ⏳ Pending │
  ╰────────┴────────┴────────┴──────────────┴───────┴───────┴────────────┴────────────╯

Via scheduler.sort_by_time():
  ╭────────┬────────┬────────┬──────────────┬───────┬───────┬────────────┬────────────╮
  │ Date   │ Time   │ Type   │ Task         │ Pet   │   Min │ Priority   │ Status     │
  ├────────┼────────┼────────┼──────────────┼───────┼───────┼────────────┼────────────┤
  │ Oct 23 │ 08:00  │ 🍖     │ Breakfast    │ Buddy │    15 │ 🟡 Medium  │ ⏳ Pending │
  │ Oct 23 │ 09:00  │ 🐾     │ Coffee break │ Buddy │    15 │ 🟡 Medium  │ ⏳ Pending │
  │ Oct 23 │ 12:30  │ 🦮     │ Lunch walk   │ Buddy │    15 │ 🟡 Medium  │ ⏳ Pending │
  │ Oct 23 │ 18:00  │ 🍖     │ Dinner       │ Buddy │    15 │ 🟡 Medium  │ ⏳ Pending │
  ╰────────┴────────┴────────┴──────────────┴───────┴───────┴────────────┴────────────╯

  Times ascend: True ['08:00', '09:00', '12:30', '18:00']

=== Priority-first sorting ===

By time:
  ╭────────┬────────┬────────┬──────────────┬───────┬───────┬────────────┬────────────╮
  │ Date   │ Time   │ Type   │ Task         │ Pet   │   Min │ Priority   │ Status     │
  ├────────┼────────┼────────┼──────────────┼───────┼───────┼────────────┼────────────┤
  │ Oct 23 │ 06:30  │ 🍖     │ Breakfast    │ Buddy │    10 │ 🔴 High    │ ⏳ Pending │
  │ Oct 23 │ 07:00  │ 🎾     │ Play fetch   │ Buddy │    20 │ 🟢 Low     │ ⏳ Pending │
  │ Oct 23 │ 12:00  │ 🦮     │ Lunch walk   │ Buddy │    30 │ 🟡 Medium  │ ⏳ Pending │
  │ Oct 23 │ 20:00  │ 💊     │ Evening meds │ Buddy │     5 │ 🔴 High    │ ⏳ Pending │
  ╰────────┴────────┴────────┴──────────────┴───────┴───────┴────────────┴────────────╯

By priority (high first, then time):
  ╭────────┬────────┬────────┬──────────────┬───────┬───────┬────────────┬────────────╮
  │ Date   │ Time   │ Type   │ Task         │ Pet   │   Min │ Priority   │ Status     │
  ├────────┼────────┼────────┼──────────────┼───────┼───────┼────────────┼────────────┤
  │ Oct 23 │ 06:30  │ 🍖     │ Breakfast    │ Buddy │    10 │ 🔴 High    │ ⏳ Pending │
  │ Oct 23 │ 20:00  │ 💊     │ Evening meds │ Buddy │     5 │ 🔴 High    │ ⏳ Pending │
  │ Oct 23 │ 12:00  │ 🦮     │ Lunch walk   │ Buddy │    30 │ 🟡 Medium  │ ⏳ Pending │
  │ Oct 23 │ 07:00  │ 🎾     │ Play fetch   │ Buddy │    20 │ 🟢 Low     │ ⏳ Pending │
  ╰────────┴────────┴────────┴──────────────┴───────┴───────┴────────────┴────────────╯

=== Daily recurrence (happy path) ===
  Original due 2026-10-23, completed on 2026-10-23

New task:
  ╭────────┬────────┬────────┬──────────────┬───────┬───────┬────────────┬────────────╮
  │ Date   │ Time   │ Type   │ Task         │ Pet   │   Min │ Priority   │ Status     │
  ├────────┼────────┼────────┼──────────────┼───────┼───────┼────────────┼────────────┤
  │ Oct 24 │ 18:00  │ 🦮     │ Evening walk │ Buddy │    30 │ 🟡 Medium  │ ⏳ Pending │
  ╰────────┴────────┴────────┴──────────────┴───────┴───────┴────────────┴────────────╯

  new due_date == today + 1: True (2026-10-24)

=== Late completion ===
  Original due 2026-10-20, completed on 2026-10-23

New task:
  ╭────────┬────────┬────────┬──────────────┬───────┬───────┬────────────┬────────────╮
  │ Date   │ Time   │ Type   │ Task         │ Pet   │   Min │ Priority   │ Status     │
  ├────────┼────────┼────────┼──────────────┼───────┼───────┼────────────┼────────────┤
  │ Oct 24 │ 18:00  │ 🦮     │ Evening walk │ Buddy │    30 │ 🟡 Medium  │ ⏳ Pending │
  ╰────────┴────────┴────────┴──────────────┴───────┴───────┴────────────┴────────────╯

  new due_date == today + 1: True (2026-10-24)
  new due_date == original due_date + 1: False

=== Conflict warnings ===
Both pending:
  Conflict on 2026-10-23 at 08:00: Walk (Buddy), Breakfast (Mia)
After marking 'Walk' complete:
  (none)

=== Overlap detection and next free slot ===

Tasks:
  ╭────────┬────────┬────────┬───────────┬───────┬───────┬────────────┬────────────╮
  │ Date   │ Time   │ Type   │ Task      │ Pet   │   Min │ Priority   │ Status     │
  ├────────┼────────┼────────┼───────────┼───────┼───────┼────────────┼────────────┤
  │ Oct 23 │ 09:00  │ 🦮     │ Long walk │ Buddy │    60 │ 🟡 Medium  │ ⏳ Pending │
  │ Oct 23 │ 09:00  │ 🛁     │ Brush     │ Buddy │    15 │ 🟢 Low     │ ⏳ Pending │
  │ Oct 23 │ 09:30  │ 🍖     │ Feed      │ Mia   │    10 │ 🔴 High    │ ⏳ Pending │
  │ Oct 23 │ 10:00  │ 💊     │ Meds      │ Mia   │     5 │ 🔴 High    │ ⏳ Pending │
  ╰────────┴────────┴────────┴───────────┴───────┴───────┴────────────┴────────────╯

Warnings:
  Conflict on 2026-10-23 at 09:00: Long walk (Buddy), Brush (Buddy)
  Overlap on 2026-10-23: Long walk (Buddy) 09:00-10:00 runs into Feed (Mia) at 09:30

Next free slot (first time the whole task fits between the others):
  30 min, not before 08:00: 08:00
  15 min, not before 09:00: 10:05
  60 min, not before 09:00: 10:05

=== Weighted prioritization (aging) ===
  score  7  [ ] 09:00 Brush teeth (Buddy) - 30 min, low
  score  5  [ ] 18:00 Evening walk (Buddy) - 30 min, medium

Strict priority:
Plan for 2026-10-23: 1 task(s), 30 of 30 available minutes used.
Tasks were chosen by priority (high first), then oldest due date (overdue first), then earliest time, until time ran out; they are listed in the order they happen.
  [ ] 18:00 Evening walk (Buddy) - 30 min, medium
Left out because they did not fit in the available time:
  [ ] 09:00 Brush teeth (Buddy) - 30 min, low (overdue since 2026-10-18)

Priority with aging:
Plan for 2026-10-23: 1 task(s), 30 of 30 available minutes used.
Tasks were chosen by score (priority points: high 10, medium 5, low 2; plus 1 per day overdue), highest first, until time ran out; they are listed in the order they happen.
  [ ] 09:00 Brush teeth (Buddy) - 30 min, low (overdue since 2026-10-18) [score 7]
Left out because they did not fit in the available time:
  [ ] 18:00 Evening walk (Buddy) - 30 min, medium [score 5]

=== Data persistence ===
  Saved 2 pets and 3 tasks to data.json (1149 bytes)
  Reloaded: Sam, 90 minutes, pets Buddy (2 tasks), Mia (1 task)
  Reloaded owner equals the original: True

Reloaded tasks, sorted by time:
  ╭────────┬────────┬────────┬──────────────┬───────┬───────┬────────────┬────────────╮
  │ Date   │ Time   │ Type   │ Task         │ Pet   │   Min │ Priority   │ Status     │
  ├────────┼────────┼────────┼──────────────┼───────┼───────┼────────────┼────────────┤
  │ Oct 20 │ 16:00  │ 🛁     │ Grooming     │ Buddy │    45 │ 🟢 Low     │ 🚨 Overdue │
  │ Oct 23 │ 08:00  │ 🦮     │ Morning walk │ Buddy │    30 │ 🔴 High    │ ⏳ Pending │
  │ Oct 23 │ 12:30  │ 💊     │ Medication   │ Mia   │     5 │ 🔴 High    │ ✅ Done    │
  ╰────────┴────────┴────────┴──────────────┴───────┴───────┴────────────┴────────────╯

  A task with a bad time in the file is rejected: time must be zero-padded HH:MM, got '8am'
```

### Friendly output: icons, colours and tables

The terminal demo and the web app share one set of display helpers, [`formatting.py`](formatting.py), so a task looks the same in both. The scheduling engine itself prints nothing.

| Element | What it shows |
|---------|---------------|
| **Priority colour** | 🔴 high, 🟡 medium, 🟢 low, in every table |
| **Status** | ✅ done, ⏳ pending, 🚨 overdue (pending and due before today) |
| **Kind of care** | 🦮 walk or run, 🍖 meal or treat, 💊 medicine, 🏥 vet, 🛁 grooming or bath, 🎾 play or training, 🚽 litter or cleaning, 💧 water, 🐾 anything else |
| **Summary** | A tally of tasks, pending, done and overdue (metrics in the app, one line in the terminal) |
| **Time budget** | A progress bar in the app, a text gauge in the terminal: `[█████████████████░░░] 75 of 90 min (83%)` |
| **Tables** | Boxed tables built with [`tabulate`](https://pypi.org/project/tabulate/) in the terminal, `st.dataframe` in the app |

Tasks have no "type" field, so the kind of care is **guessed from the description** by matching whole words ("Morning walk" is a walk, "Medium priority" is not medicine). A description that matches nothing gets the paw print. The colours come from emoji rather than terminal escape codes, so they work in any terminal, in redirected output and in the browser. Every icon is a double-width character, which keeps the table columns lined up.

Task and pet names are shown **exactly as typed**. Streamlit renders the text of tables and messages as Markdown, so the web app uses dataframes for its tables and escapes Markdown characters in its messages with `escape_markdown`. A task called `[click](http://x)` or `**bold**` is therefore plain text, never a link, an image request or bold type.

#### Functions in `formatting.py`

| Function or constant | What it does |
|----------------------|--------------|
| `task_icon(description)` | Returns the emoji for the kind of care. It tests the description against an ordered list of whole-word regular expressions (`_TYPE_PATTERNS`); the first match wins, and anything else gets `DEFAULT_ICON` (🐾). |
| `priority_label(priority)` | Returns the colour-coded priority, such as `"🔴 High"`, from the `PRIORITY_ICON` table. |
| `status_label(task, today)` | Returns `"✅ Done"`, `"🚨 Overdue"` (pending and due before `today`) or `"⏳ Pending"`. A completed task is always Done, even if it was overdue. |
| `task_rows(tasks, today)` | Turns tasks into display rows: one dict per task with the columns Date, Time, Type, Task, Pet, Min, Priority, Repeats and Status. Both the table builder and the web app start from this. |
| `summary_counts(tasks, today)` | Counts tasks: total, pending, done and overdue (an overdue task is counted once, not also as pending). |
| `summary_line(tasks, today)` | One-line tally for the terminal, e.g. `📋 4 tasks   ⏳ 3 pending   ✅ 1 done   🚨 0 overdue`. |
| `budget_bar(used, available, width=20)` | Text gauge of minutes used, e.g. `[█████████████████░░░] 75 of 90 min (83%)`. It never draws past a full bar and copes with a budget of zero. |
| `tasks_table(tasks, today, tablefmt, repeats)` | Returns a boxed text table (default style `rounded_outline`) with the minutes right-aligned, or a plain aligned table if `tabulate` is not installed. `repeats=True` adds the Repeats column; an empty list returns `(no tasks)`. |
| `escape_markdown(text)` | Puts a backslash before every character Markdown treats as special (backslash, backtick, asterisk, underscore, square brackets, parentheses, hash, tilde, dollar sign, angle brackets, vertical bar, curly braces and ampersand) and turns line breaks into spaces, so Streamlit shows the text literally. Used on every message and warning that contains a task or pet name. |
| `PRIORITY_ICON`, `STATUS_DONE`, `STATUS_PENDING`, `STATUS_OVERDUE`, `DEFAULT_ICON`, `LEGEND` | The shared icons and labels, and the one-line legend printed under the terminal header and under the app's task table. |

#### Where they are used

- **Terminal demo ([`main.py`](main.py)).** `print_tasks` builds every table with `tasks_table` and indents it; `print_todays_schedule` adds `summary_line` and `budget_bar`; the `LEGEND` is printed under the owner line. `main()` starts by calling `use_utf8_output()` (`sys.stdout.reconfigure(encoding="utf-8")`), because a Windows console on a legacy code page cannot print emoji or box lines; this also covers a program that imports `main` and calls `main.main()`.
- **Web app ([`app.py`](app.py)).** `task_rows` feeds the task table and the plan table (`st.dataframe`); `summary_counts` feeds four `st.metric` tiles above the task table; `LEGEND` goes under the table with `st.caption`; `task_icon` labels the "Mark a task done" list; and `st.progress` draws the time-budget bar for a generated plan.

#### Libraries used

| Library | Used for | Where |
|---------|----------|-------|
| [`tabulate`](https://pypi.org/project/tabulate/) (third party, 0.9 or newer) | Draws the boxed terminal tables: `tabulate(body, headers=..., tablefmt="rounded_outline", colalign=..., disable_numparse=True)`. `disable_numparse` keeps values such as `08:00` and `Mar 02` as plain text. | `formatting.tasks_table` |
| [`wcwidth`](https://pypi.org/project/wcwidth/) (third party, 0.2 or newer) | `tabulate` uses it automatically when it is installed, so emoji count as two columns wide and the box borders line up. The tests also call `wcswidth` to check that every table line has the same display width. | `tabulate` (indirectly), `tests/test_formatting.py` |
| [`streamlit`](https://streamlit.io) | `st.dataframe`, `st.metric`, `st.progress` and `st.caption` for the web version of the same output. | `app.py` |
| `re` (standard library) | The whole-word patterns that pick a task's icon. | `formatting.task_icon` |
| `datetime` (standard library) | Comparing a due date with today to decide Overdue. | `formatting.status_label` |
| `sys` (standard library) | Switching terminal output to UTF-8. | `main.py` |

`tabulate` and `wcwidth` are listed in [`requirements.txt`](requirements.txt), so `pip install -r requirements.txt` installs them. They are optional at run time: if `tabulate` is missing, the terminal tables fall back to simple aligned plain text and the web app is not affected.

Today's schedule exactly as `python main.py` prints it:

```
Owner: Sam, 90 minutes available
Priority: 🔴 high  🟡 medium  🟢 low    Status: ✅ done  ⏳ pending  🚨 overdue


=== Today's Schedule: Friday, October 23, 2026 ===
  ╭────────┬────────┬────────┬──────────────┬───────┬───────┬────────────┬────────────╮
  │ Date   │ Time   │ Type   │ Task         │ Pet   │   Min │ Priority   │ Status     │
  ├────────┼────────┼────────┼──────────────┼───────┼───────┼────────────┼────────────┤
  │ Oct 23 │ 08:00  │ 🦮     │ Morning walk │ Buddy │    30 │ 🔴 High    │ ⏳ Pending │
  │ Oct 23 │ 08:00  │ 🍖     │ Breakfast    │ Mia   │    10 │ 🔴 High    │ ⏳ Pending │
  │ Oct 23 │ 12:30  │ 💊     │ Medication   │ Mia   │     5 │ 🔴 High    │ ⏳ Pending │
  │ Oct 23 │ 18:00  │ 🦮     │ Evening walk │ Buddy │    30 │ 🟡 Medium  │ ⏳ Pending │
  ╰────────┴────────┴────────┴──────────────┴───────┴───────┴────────────┴────────────╯

  📋 4 tasks   ⏳ 4 pending   ✅ 0 done   🚨 0 overdue
  Time budget  [█████████████████░░░] 75 of 90 min (83%)
```

### Enhanced scheduling logic in action

Each excerpt below is real output from `python main.py`, one section per feature (the complete run is above). The dates are the day you run it.

**1. Priority-first sorting.** The same four tasks listed by time, then with high priority first. "Evening meds" (20:00, high) jumps ahead of "Lunch walk" and "Play fetch", and the two high-priority tasks are ordered by time.

```
=== Priority-first sorting ===

By time:
  ╭────────┬────────┬────────┬──────────────┬───────┬───────┬────────────┬────────────╮
  │ Date   │ Time   │ Type   │ Task         │ Pet   │   Min │ Priority   │ Status     │
  ├────────┼────────┼────────┼──────────────┼───────┼───────┼────────────┼────────────┤
  │ Oct 23 │ 06:30  │ 🍖     │ Breakfast    │ Buddy │    10 │ 🔴 High    │ ⏳ Pending │
  │ Oct 23 │ 07:00  │ 🎾     │ Play fetch   │ Buddy │    20 │ 🟢 Low     │ ⏳ Pending │
  │ Oct 23 │ 12:00  │ 🦮     │ Lunch walk   │ Buddy │    30 │ 🟡 Medium  │ ⏳ Pending │
  │ Oct 23 │ 20:00  │ 💊     │ Evening meds │ Buddy │     5 │ 🔴 High    │ ⏳ Pending │
  ╰────────┴────────┴────────┴──────────────┴───────┴───────┴────────────┴────────────╯

By priority (high first, then time):
  ╭────────┬────────┬────────┬──────────────┬───────┬───────┬────────────┬────────────╮
  │ Date   │ Time   │ Type   │ Task         │ Pet   │   Min │ Priority   │ Status     │
  ├────────┼────────┼────────┼──────────────┼───────┼───────┼────────────┼────────────┤
  │ Oct 23 │ 06:30  │ 🍖     │ Breakfast    │ Buddy │    10 │ 🔴 High    │ ⏳ Pending │
  │ Oct 23 │ 20:00  │ 💊     │ Evening meds │ Buddy │     5 │ 🔴 High    │ ⏳ Pending │
  │ Oct 23 │ 12:00  │ 🦮     │ Lunch walk   │ Buddy │    30 │ 🟡 Medium  │ ⏳ Pending │
  │ Oct 23 │ 07:00  │ 🎾     │ Play fetch   │ Buddy │    20 │ 🟢 Low     │ ⏳ Pending │
  ╰────────┴────────┴────────┴──────────────┴───────┴───────┴────────────┴────────────╯
```

**2. Conflict and overlap warnings, and the next free slot.** "Brush" starts at the same time as "Long walk" (a conflict), "Feed" starts while the walk is still going (an overlap), and "Meds" starts the minute the walk ends (no warning). The free-slot search then finds the first gap where a task fits.

```
=== Overlap detection and next free slot ===

Tasks:
  ╭────────┬────────┬────────┬───────────┬───────┬───────┬────────────┬────────────╮
  │ Date   │ Time   │ Type   │ Task      │ Pet   │   Min │ Priority   │ Status     │
  ├────────┼────────┼────────┼───────────┼───────┼───────┼────────────┼────────────┤
  │ Oct 23 │ 09:00  │ 🦮     │ Long walk │ Buddy │    60 │ 🟡 Medium  │ ⏳ Pending │
  │ Oct 23 │ 09:00  │ 🛁     │ Brush     │ Buddy │    15 │ 🟢 Low     │ ⏳ Pending │
  │ Oct 23 │ 09:30  │ 🍖     │ Feed      │ Mia   │    10 │ 🔴 High    │ ⏳ Pending │
  │ Oct 23 │ 10:00  │ 💊     │ Meds      │ Mia   │     5 │ 🔴 High    │ ⏳ Pending │
  ╰────────┴────────┴────────┴───────────┴───────┴───────┴────────────┴────────────╯

Warnings:
  Conflict on 2026-10-23 at 09:00: Long walk (Buddy), Brush (Buddy)
  Overlap on 2026-10-23: Long walk (Buddy) 09:00-10:00 runs into Feed (Mia) at 09:30

Next free slot (first time the whole task fits between the others):
  30 min, not before 08:00: 08:00
  15 min, not before 09:00: 10:05
  60 min, not before 09:00: 10:05
```

**3. Weighted prioritization with aging.** With room for only one 30-minute task, strict priority keeps the medium task due today. Aging scores the low-priority task 7 (2 points plus 5 days overdue) against 5, so the task that kept getting skipped now wins.

```
=== Weighted prioritization (aging) ===
  score  7  [ ] 09:00 Brush teeth (Buddy) - 30 min, low
  score  5  [ ] 18:00 Evening walk (Buddy) - 30 min, medium

Strict priority:
Plan for 2026-10-23: 1 task(s), 30 of 30 available minutes used.
Tasks were chosen by priority (high first), then oldest due date (overdue first), then earliest time, until time ran out; they are listed in the order they happen.
  [ ] 18:00 Evening walk (Buddy) - 30 min, medium
Left out because they did not fit in the available time:
  [ ] 09:00 Brush teeth (Buddy) - 30 min, low (overdue since 2026-10-18)

Priority with aging:
Plan for 2026-10-23: 1 task(s), 30 of 30 available minutes used.
Tasks were chosen by score (priority points: high 10, medium 5, low 2; plus 1 per day overdue), highest first, until time ran out; they are listed in the order they happen.
  [ ] 09:00 Brush teeth (Buddy) - 30 min, low (overdue since 2026-10-18) [score 7]
Left out because they did not fit in the available time:
  [ ] 18:00 Evening walk (Buddy) - 30 min, medium [score 5]
```

**4. Daily recurrence.** Completing a daily task adds the next one for tomorrow. Completing it three days late still schedules the next one from today, never into the past.

```
=== Daily recurrence (happy path) ===
  Original due 2026-10-23, completed on 2026-10-23

New task:
  ╭────────┬────────┬────────┬──────────────┬───────┬───────┬────────────┬────────────╮
  │ Date   │ Time   │ Type   │ Task         │ Pet   │   Min │ Priority   │ Status     │
  ├────────┼────────┼────────┼──────────────┼───────┼───────┼────────────┼────────────┤
  │ Oct 24 │ 18:00  │ 🦮     │ Evening walk │ Buddy │    30 │ 🟡 Medium  │ ⏳ Pending │
  ╰────────┴────────┴────────┴──────────────┴───────┴───────┴────────────┴────────────╯

  new due_date == today + 1: True (2026-10-24)

=== Late completion ===
  Original due 2026-10-20, completed on 2026-10-23

New task:
  ╭────────┬────────┬────────┬──────────────┬───────┬───────┬────────────┬────────────╮
  │ Date   │ Time   │ Type   │ Task         │ Pet   │   Min │ Priority   │ Status     │
  ├────────┼────────┼────────┼──────────────┼───────┼───────┼────────────┼────────────┤
  │ Oct 24 │ 18:00  │ 🦮     │ Evening walk │ Buddy │    30 │ 🟡 Medium  │ ⏳ Pending │
  ╰────────┴────────┴────────┴──────────────┴───────┴───────┴────────────┴────────────╯

  new due_date == today + 1: True (2026-10-24)
  new due_date == original due_date + 1: False
```

**5. Saving and reloading.** An owner with pets and tasks is saved to JSON and loaded back equal; a file with an invalid value is rejected.

```
=== Data persistence ===
  Saved 2 pets and 3 tasks to data.json (1149 bytes)
  Reloaded: Sam, 90 minutes, pets Buddy (2 tasks), Mia (1 task)
  Reloaded owner equals the original: True

Reloaded tasks, sorted by time:
  ╭────────┬────────┬────────┬──────────────┬───────┬───────┬────────────┬────────────╮
  │ Date   │ Time   │ Type   │ Task         │ Pet   │   Min │ Priority   │ Status     │
  ├────────┼────────┼────────┼──────────────┼───────┼───────┼────────────┼────────────┤
  │ Oct 20 │ 16:00  │ 🛁     │ Grooming     │ Buddy │    45 │ 🟢 Low     │ 🚨 Overdue │
  │ Oct 23 │ 08:00  │ 🦮     │ Morning walk │ Buddy │    30 │ 🔴 High    │ ⏳ Pending │
  │ Oct 23 │ 12:30  │ 💊     │ Medication   │ Mia   │     5 │ 🔴 High    │ ✅ Done    │
  ╰────────┴────────┴────────┴──────────────┴───────┴───────┴────────────┴────────────╯

  A task with a bad time in the file is rejected: time must be zero-padded HH:MM, got '8am'
```

### Screenshots

*The screenshots were taken before the icons, colour-coded labels and summary tallies were added, so the live app now looks richer than these images. The terminal output above is current.*

**Adding a task that clashes.** The page confirms the task, warns about the conflict, and suggests the next free slot (here, 08:30 for a 10-minute task).

![Adding a task that clashes: conflict warning and next free slot](docs/screenshot-conflict.png)

**Task list.** The conflict summary sits above the sorted table, with the pet and status filters and the "Mark a task done" control below it.

![Sorted task list with conflict warning and filters](docs/screenshot-tasks.png)

**Generated schedule.** The tasks that fit in the available minutes, in the order they happen, with the "Why this plan?" explanation. This screenshot predates the **Planning style** option, so it shows the default strict-priority plan.

![Generated schedule with explanation](docs/screenshot-plan.png)

> **Note:** the app saves to `data.json` in the project folder (see [Data persistence](#data-persistence)), so reloading the page or restarting the server keeps your pets and tasks.

## How the scheduler decides

**Daily plan.** Pending tasks due today or earlier (overdue tasks stay in until they are done) are ranked by priority, then oldest due date, then earliest time. They are taken in that order until your available minutes run out. A task that is too long for the time left is skipped so shorter ones can still fit. The chosen tasks are then shown in the order they happen, and `explain_plan()` reports what was chosen and what was left out.

| Method | Behavior |
|--------|----------|
| `Scheduler.sort_by_time()` | Orders every pet's tasks by due date, then time of day, then priority (high first). |
| `Scheduler.sort_by_priority()` | Orders every pet's tasks most important first: priority (high, medium, low), then due date, then time of day. Ties keep the order they were added. |
| `Scheduler.filter_tasks(pet_name, status)` | Narrows tasks by pet name (whole name, ignoring case) and/or completion status; with no arguments it returns everything. |
| `Scheduler.detect_conflicts()` | Returns warning strings and never raises. Completed tasks are ignored. Tasks that share a start time give a `Conflict` warning; a task that starts after another begins but before it ends gives an `Overlap` warning. A task that ends exactly when the next begins is fine. Only the due date's own day is checked, so a task running past midnight is cut off at 24:00. |
| `Scheduler.suggest_free_time(duration, day, earliest, ignore)` | Returns the first `HH:MM` at or after `earliest` where the task fits between pending tasks on that day, or `None` if nothing fits before midnight. `ignore` leaves out the task being moved. |
| `Scheduler.complete_task(task)` | Marks the task done. For a daily or weekly task it adds the next one to the same pet, 1 or 7 days after the later of its due date and today, so a late completion never schedules into the past. One-off tasks create nothing, completing a task twice does nothing, and if the pet already has an identical pending task on that date it is reused instead of copied. |
| `Scheduler.generate_plan(day, weighted)` / `explain_plan(day, weighted)` | Build the plan described above and explain it in plain text. With `weighted=True`, tasks are chosen by `task_score` and the explanation lists each task's score. |
| `Scheduler.task_score(task, day)` | Priority points (high 10, medium 5, low 2) plus 1 per day the task is overdue on `day`. A task that is not yet due gets no bonus. |

## Data persistence

PawPal+ remembers your pets and tasks between runs by saving them to a JSON file.

- **Where.** `data.json` in the project folder, next to `app.py`. It is created the first time you change something (a fresh start with nothing entered does not create it) and is listed in `.gitignore`, so your personal data is never committed. Set the environment variable `PAWPAL_DATA_FILE` to use a different path.
- **When.** Automatically, after every change in the app: adding a pet or task, marking a task done, or editing your name or time budget. There is no save button.
- **What.** The owner (name and available minutes), each pet (name, species, age) and every task (description, time, duration, priority, repeat, done or not, due date). A task's pet is recorded by where it sits in the file, not repeated on each task.
- **Delete it.** Open **Saved data** at the bottom of the page, tick the confirmation box and press **Delete all saved data**, or just delete `data.json`.

```json
{
  "version": 1,
  "owner": {
    "name": "Sam",
    "available_minutes": 90,
    "pets": [
      {
        "name": "Buddy",
        "species": "dog",
        "age": 3,
        "tasks": [
          {
            "description": "Morning walk",
            "time": "08:00",
            "duration": 30,
            "priority": "high",
            "frequency": "daily",
            "completed": false,
            "due_date": "2026-10-22"
          }
        ]
      }
    ]
  }
}
```

**Safety.**
- **Atomic writes.** `save_to_json` writes to a temporary file and swaps it into place in one step, so a crash or full disk cannot leave a half-written `data.json`. If the swap fails, the previous file is kept and the temporary file is removed.
- **Validation on load.** Every field is checked, with the same rules as creating a task by hand (a time must be `HH:MM`, a duration positive, and so on), and a pet name may not repeat. One bad value rejects the whole file with a clear `ValueError`, so you never get a half-loaded owner.
- **Nothing is lost on a bad file.** If `data.json` cannot be loaded, the app shows a warning, moves the file to `data.json.corrupt` (or `data.json.corrupt2`, `corrupt3` and so on, so an earlier backup is never replaced) and starts empty. If the file cannot be moved aside, the app still runs but saves nothing, so a file it could not read is never overwritten.
- **Two windows.** If another window or program changed `data.json` after your page loaded or last saved, the app does not write over it. It shows a warning with two buttons: overwrite the file with this window's data, or reload the saved file and discard this window's changes. There is no automatic merge.
- **Odd files.** A file saved with a UTF-8 byte-order mark (Notepad can add one) loads normally. A folder where the file should be, bad UTF-8, or absurdly nested JSON give the same clean error and warning instead of a crash.
- **Versioned.** The file records `"version": 1`; a file from a different version is rejected instead of being misread. Unknown extra keys are ignored.

| Method | Behavior |
|--------|----------|
| `Owner.save_to_json(path)` | Writes the owner, pets and tasks to `path` as indented UTF-8 JSON (accents and emoji stay readable). |
| `Owner.load_from_json(path)` | Returns the saved `Owner`, `None` if the file does not exist, or raises `ValueError` if it is unreadable or invalid. Never modifies the file. |
| `to_dict()` / `from_dict(data)` on `Task`, `Pet` and `Owner` | Convert to and from plain JSON-ready data; `from_dict` validates and raises `ValueError`. |

### The persistence workflow

What happens from the moment you open the app to the next time you open it:

1. **Start.** On the first run of a browser session, `app.py` calls `Owner.load_from_json(DATA_FILE)`.
   - *No file yet:* it returns `None`, and the app starts with a new, empty owner. Nothing is written until you change something.
   - *Valid file:* `Owner.from_dict` rebuilds the owner, then each `Pet.from_dict` and `Task.from_dict`, validating every field. Each pet stamps its name back onto its tasks.
   - *Unreadable or invalid file:* a `ValueError` is raised. The app shows a warning, renames the file to `data.json.corrupt` (a numbered name if that one is taken) so it is not lost, and starts empty.
2. **Remember what is on disk.** The app keeps a text snapshot of the loaded owner (`owner.to_dict()` as JSON) in the session, and fills the owner-name and available-minutes boxes from the loaded values instead of their defaults.
3. **Use the app.** Every click re-runs the script. Adding a pet or task, marking a task done, or editing the name or time budget changes the in-memory `Owner`.
4. **Autosave.** At the end of every run, the app compares a fresh snapshot of the owner with the remembered one. If they differ, it calls `owner.save_to_json(DATA_FILE)`, which writes a temporary file and swaps it into place, then updates the remembered snapshot. Before writing, it checks that no other window or program changed the file since this page loaded or last saved; if one did, nothing is written and you choose which version to keep. If the disk write fails, you get a warning and the app keeps working. (**Mark complete** re-runs the page straight away, so that change is saved by the run that follows.)
5. **Come back later.** Stop and start the app, or reload the page, and step 1 loads everything you saved.
6. **Start over (optional).** **Saved data**, then **Delete all saved data** (after ticking the confirmation box) deletes `data.json` and resets the session to an empty owner.

The terminal demo (`python main.py`) exercises the same save and load calls on a temporary folder, so running it never touches your `data.json`.

### Files modified for persistence

| File | Change |
|------|--------|
| [`pawpal_system.py`](pawpal_system.py) | Added `to_dict()` and `from_dict()` to `Task`, `Pet` and `Owner` (validating on load), `Owner.save_to_json` and `Owner.load_from_json`, and the `DATA_VERSION` constant. |
| [`app.py`](app.py) | Loads the saved owner at startup, handles an unreadable file, starts the name and minutes boxes from saved values, autosaves after every change (after checking that no other window changed the file), and adds the **Saved data** panel with a confirmed delete. `PAWPAL_DATA_FILE` can override the file location. |
| [`main.py`](main.py) | New save-and-reload section in the terminal demo, using a temporary folder. |
| [`.gitignore`](.gitignore) | Ignores `data.json`, `data.json.tmp` and `data.json.corrupt`, so personal data is never committed. |
| [`tests/test_persistence.py`](tests/test_persistence.py) | **New.** 91 tests for the engine: round trips (including names with spaces and unsorted order), file format, missing, damaged, BOM and nested files, every kind of invalid field, plain string paths, failed saves, and the scheduler behaving the same after a reload. |
| [`tests/test_app_persistence.py`](tests/test_app_persistence.py) | **New.** 24 tests that run the real `app.py` with Streamlit's test harness: data survives a restart, an unreadable file is kept (with numbered backups) and the app starts empty, delete works with and without a file, a failed save or unmovable bad file never crashes or overwrites, and two windows cannot silently overwrite each other. They use a temporary file, never your `data.json`. |
| [`diagrams/uml_final.mmd`](diagrams/uml_final.mmd) and `.png` | Added the new methods to `Task`, `Pet` and `Owner`. |
| `README.md`, [`reflection.md`](reflection.md), [`ai_interactions.md`](ai_interactions.md) | Documentation of the feature, updated test counts, and corrections to statements that were no longer true. |
| `data.json` | **Created while you use the app, not part of the source.** It is git-ignored. |

## Architecture

The engine in [`pawpal_system.py`](pawpal_system.py) is four classes. The web app and the demo only call into it.

![PawPal+ class diagram](diagrams/uml_final.png)

- **`Task`** is one care activity: description, `HH:MM` time, duration, priority, frequency, due date and completion status. It validates its own fields and can compute its next due date.
- **`Pet`** holds a pet's details and its tasks. Adding a task records the pet's name on it; a task knows its pet only by that name.
- **`Owner`** holds the pets and the minutes available per day. `get_all_tasks()` returns every pet's tasks as one flat list, and duplicate pet names are rejected.
- **`Scheduler`** takes an `Owner` and reads every task through `owner.get_all_tasks()`, never from a single pet, so it works across all pets.

The diagram source is [`diagrams/uml_final.mmd`](diagrams/uml_final.mmd) (Mermaid). The original Phase 1 draft is kept in [`diagrams/uml.mmd`](diagrams/uml.mmd), and the reasoning behind the changes is in [`reflection.md`](reflection.md).

## Testing

The engine tests are in [`tests/test_pawpal.py`](tests/test_pawpal.py) and [`tests/test_persistence.py`](tests/test_persistence.py) and run with no Streamlit involved. [`tests/test_app_persistence.py`](tests/test_app_persistence.py) drives the real `app.py` with Streamlit's test harness to check that data survives a restart. [`tests/test_formatting.py`](tests/test_formatting.py) covers the display helpers, [`tests/test_demo.py`](tests/test_demo.py) runs `main.py`, and [`tests/test_app_ordering.py`](tests/test_app_ordering.py) and [`tests/test_app_display.py`](tests/test_app_display.py) check what the app shows. Run them from the project root:

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
| **Priority-first sorting** (`sort_by_priority`, and the app's **Order by** choice) | High, medium, low whatever order tasks were added; earlier time first within a priority | Priority outranks time (a late high beats an early low); at equal priority an older due date comes first, but priority still beats age; full ties keep listing order; empty owner; completed tasks are listed; the pets' own lists are not reordered; the list switches between time and priority order in the real app, still honoring the filters |
| **Weighted prioritization** (`task_score`, `generate_plan(weighted=True)`) | Score is priority points plus 1 per day overdue; a long-overdue low task outranks a medium task due today when time is short, and strict priority (the default) is unchanged | A high task still beats a low task 7 days late (9 < 10); a score tie goes to the older due date; with nothing overdue it matches strict priority; the budget is never exceeded; completed and future tasks are excluded; scores appear in the explanation only when weighted; a future task gets no bonus |
| **Free-slot suggestion** (`suggest_free_time`) | Empty day returns the earliest time; a busy task pushes the suggestion to when it ends; the suggestion clears the conflict it was made for | A gap that fits exactly is used and one a minute short is not; back-to-back tasks chain; completed tasks, other dates and the task being moved are ignored; `None` when nothing fits before midnight; bad duration or time raises |
| **Data persistence** (`Owner.save_to_json` / `Owner.load_from_json`, and the app) | Save then load gives an equal owner with every field, pet name and order intact; the scheduler gives identical answers after a reload; the app shows the same pets, tasks, name and minutes after a restart | Missing file returns `None`; empty, non-JSON, non-UTF-8, wrong-shaped or wrong-version files raise `ValueError` and are never modified; every bad field (time, duration, priority, frequency, date, types, missing keys, duplicate pet names, out-of-range minutes) is rejected; a failed save keeps the old file and leaves no temporary file; accents and emoji survive; the app keeps an unreadable file as `data.json.corrupt` (numbered if taken) and starts empty; a file with a BOM loads; a folder in place of the file and absurdly nested JSON are handled; saving never crashes the app and never overwrites a file the app could not read; a second window cannot silently overwrite a newer save (it can overwrite or reload on request) |
| **Friendly output** (`formatting.py`) | Every kind of care gets its icon; priority and status are colour-coded; the summary tally and time gauge read correctly; tables are boxed with the expected columns | Whole-word matching ("Medium" is not medicine, "Washington" is not washing), first match wins, unknown text gets the paw print, a completed overdue task shows as done, a gauge never draws past full or divides by zero, minutes are right-aligned, and every table line has the same display width even with emoji; the plain-text fallback when `tabulate` is missing; Markdown characters escaped so names show literally; the demo run as a program and as an import on a legacy console encoding; and, in the real app, the tally, legend, task picker, schedule section, progress bar and Score column |
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
collected 526 items

tests\test_app_display.py ............                                   [  2%]
tests\test_app_ordering.py ....                                          [  3%]
tests\test_app_persistence.py ........................                   [  7%]
tests\test_demo.py ...........                                           [  9%]
tests\test_formatting.py ............................................... [ 18%]
........................................................................ [ 32%]
........................................................................ [ 46%]
...                                                                      [ 46%]
tests\test_pawpal.py ................................................... [ 56%]
........................................................................ [ 69%]
...................................................................      [ 82%]
tests\test_persistence.py .............................................. [ 91%]
.............................................                            [100%]

============================ 526 passed in 26.84s =============================
```

## Project structure

```
app.py                  Streamlit web app
main.py                 Terminal demo of the engine
pawpal_system.py        Task, Pet, Owner and Scheduler classes
formatting.py           Icons, colour-coded labels, summaries and tables shared by the app and the demo
tests/test_pawpal.py    Engine tests: sorting, recurrence, conflicts, plans, validation
tests/test_persistence.py       Saving and loading tests
tests/test_app_ordering.py      Streamlit app tests: the Order by choice
tests/test_app_display.py       Streamlit app tests: tally, legend, task picker, schedule section, literal text
tests/test_demo.py              Checks that main.py runs and prints each feature the README quotes
tests/test_formatting.py        Icons, labels, summaries, the gauge and table alignment
tests/test_app_persistence.py   Streamlit app tests: data survives a restart
docs/                   App screenshots used in this README
diagrams/               Class diagram: uml_final.mmd/.png (final), uml.mmd (Phase 1 draft)
data.json               Your saved pets and tasks (created on first change; not committed)
reflection.md           Design decisions and project reflection
requirements.txt        Python dependencies
pytest.ini              Test configuration
```

## Limitations

- **One local file.** Data lives in a single `data.json` next to the app: one owner, no accounts, no database. If you open the app in two browser tabs, each keeps its own copy in memory; the app notices when the file changed under it and asks whether to keep this window's data or reload the saved file, but it cannot merge the two.
- **No editing or deleting.** In the app you can add pets and tasks and mark tasks done, but you can't change or remove them afterwards.
- **Tasks are due today.** Tasks added in the app are dated today; only recurring follow-ups land on later days. The engine itself accepts any due date.
- **Conflicts are checked per day.** A task running past midnight is treated as ending at 24:00.
- **The plan does not resolve conflicts.** It chooses tasks by priority and time budget, so tasks that clash can both appear in the plan (as in the screenshot above). The conflict warnings are how you spot and fix them.
- **Fixed weights.** The aging weights (10, 5, 2 and 1 point per overdue day) are constants in `pawpal_system.py`, not settings in the app.
- **Time of day only.** There are no time zones, and tasks have no end time other than start plus duration.
