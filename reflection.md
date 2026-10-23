# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

PawPal+ is a Streamlit app that helps a busy pet owner stay consistent with pet care. The system should track daily routines (feedings, walks, medications, appointments), consider constraints such as available time and priority and produce a daily plan that explains why it chose that plan.

Core user actions
1. **Add owner and pet information:** The user enters basic owner and pet details so the app knows whose pets are being cared for and can associate care tasks with each pet.
2. **Add or edit care tasks:** The user creates and modifies tasks such as walks, feeding, medication, enrichment and grooming. Each task includes at least a duration and a priority.
3. **Generate and view a daily plan:** The user generates a daily schedule that fits tasks into available time, respects priorities and owner preferences and displays the plan clearly along with reasoning for the choices.

**Initial UML design:**

The system uses four classes:

- **Task** — Represents a single care activity. Holds a description, a scheduled time (HH:MM), a duration, a priority, a frequency (once/daily/weekly) and a completion status, plus the name of the pet it belongs to (so a flat task list can still be filtered by pet and labeled in the plan). Responsible for updating its own state, such as being marked complete and for working out its next due date when it recurs.
- **Pet** — Represents one pet. Holds pet details (name, species, age) and owns a collection of Tasks. Responsible for adding tasks to itself and tagging each with the pet's name.
- **Owner** — Represents the pet owner. Holds owner details and manages multiple Pets. Responsible for adding pets and providing a single aggregated view of every task across all pets via a `get_all_tasks()` method, so the scheduler does not depend on any individual pet.
- **Scheduler** — The "brain" of the system. Responsible for retrieving tasks from the Owner (not from a single Pet), sorting them by time, filtering by pet or completion status, detecting scheduling conflicts, generating a daily plan and explaining why it is ordered that way. This separation keeps scheduling policy in one place so it can be changed without touching the data classes.

**b. Design changes**

Yes. After drafting the UML and turning it into class skeletons, I reviewed the skeleton for missing relationships and logic bottlenecks and the design changed in these ways:

- **Added `Task.pet_name`.** `Owner.get_all_tasks()` returns a flat list, so a task no longer knew which pet it belonged to. Without that, the scheduler could not filter by pet and the plan could not label tasks by pet. `Pet.add_task` sets it. I kept it a string instead of a direct `Pet` reference because a `Pet`↔`Task` cycle makes the dataclass `repr`/`eq` recurse forever. The cost is that pet names must be unique, so `Owner.add_pet` rejects duplicates.
- **Added `Task.due_date`.** `next_occurrence()` returns a date, but a task only had an `"HH:MM"` time, so there was nothing to compute the next occurrence from and no way to tell today's tasks from future ones.
- **Added `Owner.available_minutes`.** The core requirement is a plan that fits tasks into the owner's available time, but nothing stored that time, so `generate_plan()` had no constraint to plan against.
- **Added `Scheduler.complete_task(task)`.** Completing a recurring task has to create the next occurrence and attach it to the right pet. `Task.mark_complete()` cannot do that because it only knows its pet by name, so no class owned that step. The scheduler can find the pet through the owner.
- **Removed speculative methods.** I cut `Owner.remove_pet`, `Pet.remove_task`, `Pet.task_count()`, `Task.__str__()` and the redundant `Scheduler.owner` attribute from the diagram. Nothing in the requirements needed them and each added surface area to build and test for no benefit. The `Scheduler`→`Owner` arrow already shows the owner link.

**c. Final design compared with the initial UML**

Once the app was built I redrew the diagram from the code ([`diagrams/uml_final.mmd`](diagrams/uml_final.mmd)) and kept the Phase 1 draft ([`diagrams/uml.mmd`](diagrams/uml.mmd)) for comparison. The four classes and the ownership arrows (`Owner` has `Pet`s, `Pet` has `Task`s) did not change. What changed was how the classes interact and what the `Scheduler` does:

- **`Scheduler` touches more than the `Owner`.** `complete_task` finds the right `Pet` by `pet_name` and calls `Pet.add_task` for the next occurrence, and the scheduler copies, sorts and plans `Task`s. The final diagram shows these as dashed `Scheduler ..> Pet` and `Scheduler ..> Task` dependencies. A `Task` still knows its pet only by name.
- **`Scheduler.owner` is back on the diagram.** I removed it earlier as redundant with the arrow, but the code stores it (`self.owner`), and the final diagram should match the code.
- **New method `suggest_free_time`.** Overlap detection and a free-slot suggestion were added after the first draft, once I saw that two tasks starting at different times can still collide.
- **Small corrections.** `complete_task` returns `Task?` (a one-off task returns nothing) and `next_occurrence` takes a `from_date`, so a late completion never schedules into the past.
- **Private helpers.** `_build_plan` and `_overlapping_pairs` are shown as private members.
- **Methods that came back or were made explicit.** `Task.__str__`, which I had cut as speculative, is used by `explain_plan` and the terminal demo, so it is back. `Task.__post_init__` (validation), `Pet.__post_init__` (stamping each task with the pet's name) and `Scheduler.__init__` are shown because they carry real behavior.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

The scheduler weighs five things, from most to least important:

1. **Time budget (a hard limit).** `Owner.available_minutes` is the most the plan may use. A task that does not fit is skipped and listed as "left out", never squeezed in.
2. **Priority** (high, medium, low). It decides which tasks get the limited minutes first.
3. **Due date.** Only pending tasks due today or earlier are planned. Overdue tasks stay in the plan and come before today's tasks at the same priority; future tasks are left out.
4. **Time of day.** The earliest time breaks ties when choosing tasks, and it sets the order the chosen tasks are shown in.
5. **Completion status (a filter, not a ranking).** Completed tasks are removed before anything is ranked, so they are never planned and never count as conflicts.

Clashes (tasks that start together or overlap) are reported as warnings, not enforced. I did not model owner preferences: the scenario mentions them, but no class stores them and nothing in the required behavior needed them.

I ranked these by what each one costs when it goes wrong. A plan that does not fit the day is not a plan, so the time budget is a hard limit. Priority comes next because a skipped medication matters more than skipped grooming (in the sample data, the 45-minute low-priority grooming task is the one that gets left out). Due date matters once recurring tasks exist, because without it an overdue task would silently vanish from the plan. Time of day comes last among the ranking factors because it only breaks ties.

**b. Tradeoffs**

**The plan picks tasks greedily by priority instead of packing the most minutes.** It takes tasks in order (priority, then due date, then time) until the time runs out, skipping any task too long for what is left. For example, with 90 minutes, a 60-minute high-priority task, and two 45-minute medium tasks, the plan contains only the high-priority task and uses 60 minutes. Dropping it would fit both medium tasks and use all 90, but that plan would skip the most important task.

This is reasonable here because in pet care, priority reflects consequences (medication, feeding), not just volume, so the important task should never be displaced by two smaller ones. It also keeps the explanation simple: the "Why this plan?" panel says tasks were "chosen by priority (high first), then oldest due date (overdue first), then earliest time, until time ran out", which is the whole algorithm in one sentence. A better packing would need a rule for trading priority against minutes, and I would have had to invent that rule.

I did not leave that tradeoff untouched. Strict priority can starve a low-priority task, because a medium task due today always beats it, however long it has been waiting. So I added an optional **priority with aging** mode: a task's score is its priority points (high 10, medium 5, low 2) plus one point per day overdue, and tasks are taken highest score first. A low task that is 5 days late (score 7) now beats a medium task due today (5), but a high task (10) still beats a low task that is a week late (9). I kept strict priority as the default because it is the simpler promise ("high first, always") and the weights are my own judgment, not something the requirements specify.

A second tradeoff in the same spirit: **conflicts are warned about, not resolved.** The plan can contain two tasks at 08:00 (visible in my screenshots). The owner knows things the scheduler cannot, such as a family member who can feed one pet while the other is walked, so the app warns, suggests the next free slot, and leaves the decision to the owner.

---

## 3. AI Collaboration

**a. How you used AI**

I used the AI at every stage: brainstorming the four classes and their methods, drawing the Mermaid UML, generating the class skeletons, implementing the logic, writing a terminal demo (`main.py`), writing tests and drafting docs. What it suggested, in order:

- A class brainstorm (Owner, Pet, Task, Scheduler) with attributes, methods and relationships, which it turned into a Mermaid diagram and then dataclass skeletons.
- Implementations for sorting, filtering, conflict detection, recurring tasks and a daily plan that fits tasks into the owner's available minutes by priority and explains its choices.
- A test suite and then a set of AI-written "bugs" to see whether that suite would notice them.

The most helpful prompts asked the AI to critique its own work instead of producing more: "make sure the relationships make sense and you haven't included unnecessary complexity" and "do you notice any missing relationships or potential logic bottlenecks?". Those two prompts changed the design more than any request to build something.

**b. Judgment and verification**

**What I accepted and rejected.** The first diagram was accepted as a starting point but not as final. When I asked for a complexity check, the AI cut methods nothing in the requirements needed (`remove_pet`, `remove_task`, `task_count`, `__str__`) and a redundant `Scheduler.owner` attribute. The skeleton review then found real gaps: `get_all_tasks()` returns a flat list, so tasks had lost track of their pet (fixed with `Task.pet_name`); there was no `due_date` for recurrence to work from; there was no time budget for the plan; and nothing owned the "create the next occurrence" step (fixed with `Scheduler.complete_task`). I approved those fixes. I deferred one suggestion, keeping the `Owner` in Streamlit's `st.session_state`, until `app.py` is wired up. I also stopped a `git push` the AI tried to run, because I wanted to decide when work goes to GitHub.

**How I verified.** I did not take "it works" on trust:

- **Running it:** I ran `main.py` in the terminal and checked the output by hand: the 08:00 clash across two pets, the 45-minute grooming task left out of a 90-minute plan and the daily walk recreated for the next day.
- **Adversarial review:** four independent AI reviewers hunted for bugs and a separate verifier ran each claimed bug's repro script before it counted. Only 3 of the 16 findings were real (a Unicode-digit hole in time validation, tasks passed to `Pet(tasks=[...])` missing their pet name and an explanation that did not match the plan's actual ordering). I fixed those and recorded the rest, such as exact-start-time conflicts only, as deliberate tradeoffs.
- **Testing the tests:** all my first 53 tests passed, which proved little. A mutation test (the AI injected bugs into scratch copies of the code) caught only 79 of 122 injected bugs. The survivors showed real weaknesses, for example that my fixed test date happened to equal the real date, so bugs that quietly used `date.today()` went unnoticed. A second round caught 88 of 136 subtler bugs. I added tests for the survivors, moved the fixed test date and re-checked 12 of the surviving bugs against the final suite. All 12 were caught. At that point the suite had 120 passing tests; it has since grown to 260 with leap-day, overlap, duplicate-follow-up, free-slot, sorting tie-break and weighted-planning tests.

**Limits.** The AI's first design had a real flaw (tasks lost their pet) and its first test suite looked stronger than it was. Both were found by asking the AI to look for faults, not by trusting its first answer. The mutation check is also only as good as the bugs the AI thought of and the Streamlit UI is covered by clicking through it, headless runs, and (for saving and reloading only) the committed test suite.

**c. AI strategy**

*Which AI coding assistant features were most effective for building the scheduler?*

- **Asking the AI to critique its own work.** The two prompts quoted above ("make sure the relationships make sense and you haven't included unnecessary complexity" and "do you notice any missing relationships or potential logic bottlenecks?") shaped the design more than any request to build something.
- **Running things instead of describing them.** The assistant ran `main.py`, `python -m pytest` and a headless run of the Streamlit app, so claims like "it works" came with output. That caught real problems, such as the diagram renderer showing `__init__` as bold "init" (Mermaid reads double underscores as markdown), which I only noticed because the diagram was rendered and looked at.
- **Editing several files consistently.** One change often touched the engine, the tests, the app and the README at the same time, for example when overlap detection changed `detect_conflicts` and then the UI warnings, the test table and the docs.
- **Adversarial review and mutation testing.** Reviewers hunting for bugs and a verifier that had to reproduce each claim found three real defects that my first passing suite had missed.

*An AI suggestion I rejected or modified to keep the design clean.*

The assistant's first brainstorm, before I committed any diagram, was fuller than the requirements needed: it included `remove_pet`, `remove_task`, `task_count()` and a `Scheduler.owner` attribute that the `Scheduler`-to-`Owner` arrow already implied. I did not accept it as final. I asked for a complexity check and those items were removed from the committed diagram, because each one added code to build and test with no requirement behind it. One of them, `Task.__str__`, later earned its place back once the plan explanation needed it (see 1c). I handled the Streamlit suggestion the same way. Keeping the `Owner` in `st.session_state` was right for the app, but I deferred it until the logic layer was finished, so the UI could not shape the engine. I also stopped a `git push` the assistant tried to run, because I wanted to decide when work goes to GitHub, and I had the `Co-Authored-By` line removed from my latest commit (the earlier commits still carry it).

*How separate chat sessions for different phases helped.*

The work moved in phases, and the commit history roughly follows them: skeletons, implementation, tests, UI, then a second round of engine changes and tests. My last phase (more tests, UI polish, redrawing the UML and rewriting the README) started in a fresh session with none of the earlier chat history. The assistant had to re-read `pawpal_system.py` and the diagram rather than trust what it remembered, and that is how it found that the diagram had drifted from the code: a missing method, a missing `owner` attribute, a wrong return type. A fresh session also kept each conversation short enough that the assistant was not working from stale decisions.

*What I learned about being the lead architect.*

- **The AI generates quickly and I decide what is correct.** It was easy to get code, tests, diagrams and docs; deciding what the system should be (a logic layer that does not depend on the UI, a scheduler that reads every task through the owner, a greedy plan I could explain) was my job.
- **Different pieces of the same project drift apart.** The diagram, README, tests and code each said something slightly different at points, for instance a README claiming the UI was not connected after it was. Someone has to check that they agree, and that someone is the architect.
- **A passing result is not a verified result.** My first 53 tests all passed and proved little. Asking "what would break this?" was more useful than asking for more output.
- **Limits belong in the record.** When I found that overlapping tasks were not flagged and that completing a task could create a duplicate, I first documented them as known limits, then decided to fix them and flipped the tests. Writing them down made the decision deliberate instead of accidental.

---

## 4. Testing and Verification

**a. What you tested**

The suite (260 tests in `tests/`) mostly tests the engine directly, plus the app's save-and-reload flow, and covers eight behaviors, each with a happy path and edge cases:

- **Sorting.** Tasks added out of order come back chronologically. Edge cases: same date and time (priority breaks the tie, then insertion order), an earlier date beating an earlier time, and an empty owner.
- **Recurrence.** Completing a daily task adds one pending task due the next day, and a weekly task adds one a week later, on the same pet. Edge cases: one-off tasks create nothing, completing twice creates no duplicate, an identical pending next task is reused, early and late completion, month, year and leap-day rollover, and an unknown pet.
- **Conflict detection.** Two pending tasks at the same date and time give one warning naming both. Edge cases: overlapping durations, back-to-back tasks (not a conflict), completed tasks, other dates, three tasks in one slot, and overlap being cut off at midnight.
- **The daily plan.** Tasks that fit are chosen by priority and listed in time order. Edge cases: a budget used exactly or set to zero, a too-long task skipped while smaller ones still fit, overdue tasks included, and completed or future tasks excluded.
- **Weighted prioritization.** A task's score is its priority points plus one per day overdue, and a long-overdue low task can outrank a medium one due today. Edge cases: a high task still beating a low one that is 7 days late, a score tie going to the older due date, a future task getting no bonus, the same plan as strict priority when nothing is overdue, the time budget never being exceeded, and scores shown only in the weighted explanation.
- **Data persistence.** Saving and then loading gives back an equal owner with every field, each task's pet name and the original order, and the scheduler answers identically after a reload. Edge cases: a missing file, an empty or non-JSON or wrong-version file, every kind of bad field (time, duration, priority, frequency, date, wrong types, missing keys, duplicate pet names, minutes out of range), a failed save keeping the old file, accents and emoji, and the app (driven with Streamlit's test harness) showing the same data after a restart and keeping an unreadable file instead of overwriting it.
- **Free-slot suggestion.** The first time a task fits, a gap that fits exactly, back-to-back tasks, and `None` when nothing fits before midnight.
- **Validation.** Bad times (`9:00`, `24:00`, `12:60`), non-positive durations, unknown priority or frequency, and duplicate pet names.

These mattered because each one changes what the owner sees or what is stored. A sorting bug misorders the schedule, a recurrence bug quietly creates duplicate or missing tasks, and a plan bug can put more work in the day than the owner has time for. Several tests freeze `date.today()`, because early on a bug that quietly used the real date went unnoticed.

**b. Confidence**

About **4 out of 5**. All 260 tests pass, the eight behaviors above have both happy-path and edge-case coverage, and I also checked the app by hand and in a headless run. I hold back the last point for three reasons: the tests were written by the same side that wrote the code, so they encode my understanding of the requirements; only the save-and-reload flow of the Streamlit UI is part of the automated suite, and the rest of the interface is checked by hand and in headless runs; and the engine knows only a time of day and a due date, so it has not been tested against time zones or clock changes, and tasks that run past midnight are tested only for being cut off at 24:00, not for carrying into the next day.

With more time I would test:

- A property-style check that no generated plan ever exceeds the time budget, over many random task sets.
- Tasks that carry over into the next day, which the engine does not support and currently cuts off at 24:00.
- More of the Streamlit app with the framework's test harness in the committed suite (today only the save-and-reload flow is).
- Editing and deleting tasks, once those features exist.
- A larger number of pets and tasks, to see whether the plan and conflict checks stay fast.

---

## 5. Reflection

**a. What went well**

I am most satisfied with keeping the engine independent of the interface. `pawpal_system.py` knows nothing about Streamlit, so the same code serves the terminal demo, the 260 tests and the web app, and the app is thin enough to read in a few minutes. I am also pleased that I treated verification as part of the work: asking for critiques, running adversarial reviews and mutation checks, and fixing the limits I had written down (overlapping tasks and duplicate follow-ups) instead of leaving them as excuses.

**b. What you would improve**

- **A real time model.** Tasks have only an `HH:MM` time and a due date, which is why overlap detection stops at midnight and why there are no time zones. A start and end datetime would remove those limits.
- **A plan that avoids clashes.** Today it chooses tasks by priority and lets two of them share 08:00. It should assign start times so that nothing overlaps, or at least offer to.
- **Link tasks to pets by an id, not a name.** Names have to be unique only because tasks refer to pets by name.
- **Editing, and storage that scales.** A task cannot be edited or removed in the app. Data is saved to one local JSON file, which is fine for one owner on one machine; two browser tabs would overwrite each other, and several users would need a database.

**c. Key takeaway**

An AI assistant makes it cheap to produce an answer, which makes it more important to know what a right answer looks like before asking. The design decisions that held up were ones I could state in a sentence and test: a scheduler that reads every task through the owner, tasks linked to pets by a unique name, a greedy plan I could explain. The things that went wrong were places where I had accepted output I had not yet checked, such as a test suite that passed but missed bugs, or a diagram and README that no longer matched the code.
