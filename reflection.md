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

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

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
- **Testing the tests:** all my first 53 tests passed, which proved little. A mutation test (the AI injected bugs into scratch copies of the code) caught only 79 of 122 injected bugs. The survivors showed real weaknesses, for example that my fixed test date happened to equal the real date, so bugs that quietly used `date.today()` went unnoticed. A second round caught 88 of 136 subtler bugs. I added tests for the survivors, moved the fixed test date and re-checked 12 of the surviving bugs against the final suite. All 12 were caught. The suite now has 120 passing tests.

**Limits.** The AI's first design had a real flaw (tasks lost their pet) and its first test suite looked stronger than it was. Both were found by asking the AI to look for faults, not by trusting its first answer. The mutation check is also only as good as the bugs the AI thought of and I have not yet tested the Streamlit UI.

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
