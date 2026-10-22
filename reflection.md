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

- **Task** — Represents a single care activity. Holds a description, a scheduled time (HH:MM), a duration, a priority, a frequency (once/daily/weekly) and a completion status, plus the name of the pet it belongs to (so a flat task list can still be filtered by pet and labeled in the plan). Responsible for updating its own state, such as being marked complete, and for working out its next due date when it recurs.
- **Pet** — Represents one pet. Holds pet details (name, species, age) and owns a collection of Tasks. Responsible for adding tasks to itself and tagging each with the pet's name.
- **Owner** — Represents the pet owner. Holds owner details and manages multiple Pets. Responsible for adding pets and providing a single aggregated view of every task across all pets via a `get_all_tasks()` method, so the scheduler does not depend on any individual pet.
- **Scheduler** — The "brain" of the system. Responsible for retrieving tasks from the Owner (not from a single Pet), sorting them by time, filtering by pet or completion status, detecting scheduling conflicts, generating a daily plan and explaining why it is ordered that way. This separation keeps scheduling policy in one place so it can be changed without touching the data classes.

**b. Design changes**

Yes. After drafting the UML and turning it into class skeletons, I reviewed the skeleton for missing relationships and logic bottlenecks, and the design changed in these ways:

- **Added `Task.pet_name`.** `Owner.get_all_tasks()` returns a flat list, so a task no longer knew which pet it belonged to. Without that, the scheduler could not filter by pet and the plan could not label tasks by pet. `Pet.add_task` sets it. I kept it a string instead of a direct `Pet` reference because a `Pet`↔`Task` cycle makes the dataclass `repr`/`eq` recurse forever. The cost is that pet names must be unique, so `Owner.add_pet` rejects duplicates.
- **Added `Task.due_date`.** `next_occurrence()` returns a date, but a task only had an `"HH:MM"` time, so there was nothing to compute the next occurrence from, and no way to tell today's tasks from future ones.
- **Added `Owner.available_minutes`.** The core requirement is a plan that fits tasks into the owner's available time, but nothing stored that time, so `generate_plan()` had no constraint to plan against.
- **Added `Scheduler.complete_task(task)`.** Completing a recurring task has to create the next occurrence and attach it to the right pet. `Task.mark_complete()` cannot do that because it only knows its pet by name, so no class owned that step. The scheduler can find the pet through the owner.
- **Removed speculative methods.** I cut `Owner.remove_pet`, `Pet.remove_task`, `Pet.task_count()`, `Task.__str__()` and the redundant `Scheduler.owner` attribute from the diagram. Nothing in the requirements needed them, and each added surface area to build and test for no benefit. The `Scheduler`→`Owner` arrow already shows the owner link.

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

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

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
