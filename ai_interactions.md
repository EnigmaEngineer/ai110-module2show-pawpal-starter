# AI Interactions Log

> **Stretch features only.** Only fill in the sections that apply to stretch features you attempted. If you did not attempt a stretch feature, leave its section blank or delete it. This file is not required for the core project.

---

## Agent Workflow (SF7)

> Document your experience using an AI agent (e.g., Cursor Agent, Claude, Copilot) to make multi-step changes autonomously.

The agent was Claude Code, running in VS Code with permission to read and edit files, run the shell, and start sub-agents. This log covers the final stretch of the project: hardening the scheduler, polishing the UI, redrawing the UML and writing the docs. Earlier phases (class skeletons, first implementation) are in the git history, not here.

### Files modified

| File | What changed | Committed? |
|------|--------------|------------|
| `pawpal_system.py` | Overlap detection in `detect_conflicts`; `complete_task` reuses an identical pending follow-up instead of adding a copy; new `suggest_free_time`; new weighted prioritization (`task_score`, `weighted=` on `generate_plan` / `explain_plan`) | Partly (`4f9f9ee`); free-slot and weighted planning are not yet |
| `tests/test_pawpal.py` | Grew from 126 to 175 tests: leap days, overlap, duplicate follow-up, free slots, sorting tie-breaks, weighted planning | Partly (`4f9f9ee`) |
| `app.py` | Conflict banner above a sorted table, pet and status filters, "Mark a task done", next-free-slot message when a new task clashes, "Planning style" choice | No |
| `main.py` | Added a weighted-planning section to the terminal demo | No |
| `README.md` | Rewritten as a manual: features, demo walkthrough with real CLI output, scheduler behavior, testing, limitations | Partly (`4f9f9ee`) |
| `reflection.md` | Filled in sections 1c, 2, 3c, 4 and 5; corrected two stale facts in 3b | Partly (`4f9f9ee`) |
| `diagrams/uml_final.mmd`, `uml_final.png` | New: the final class diagram, redrawn from the code | No |
| `diagrams/uml.mmd` | Edited, then restored with `git checkout` so it stays as the Phase 1 draft | n/a |
| `docs/screenshot-*.png` | Three screenshots I took of the running app | No |
| `ai_interactions.md` | This section | No |

### What I asked the agent to do

In order, each as a separate request:

1. Review `pawpal_system.py` and list the core behaviors and edge cases to test for sorting and recurring tasks (including a pet with no tasks and two tasks at the same time).
2. Make sure the suite covers sorting, daily recurrence and duplicate-time conflict detection, then add tests for the three gaps it had listed (leap day, overlapping durations, an identical follow-up already existing).
3. Run `python -m pytest` and keep going until everything passes.
4. Write a "Testing PawPal+" section in the README with the run command, what the tests cover and the real output.
5. Show the algorithms in the UI (sorting, filtering, conflict warnings) and say how a conflict warning should look to a pet owner; then add a suggested free slot and a warning at the moment a task is added.
6. Check the Mermaid UML against the final code, update it, and save it as `diagrams/uml_final.mmd` with a PNG.
7. Rewrite the README as a professional manual and add a Demo Walkthrough with an example workflow and the real `main.py` output.
8. Write the reflection, including the four AI-strategy questions.
9. Add a third algorithmic capability beyond the basics.
10. Commit and push the test suite.

### What the agent completed

- **Tests and engine.** Fixed the two limits the tests had documented: overlapping tasks are now flagged (shared start time still gives a `Conflict`, a task starting before another ends gives an `Overlap`), and completing a recurring task no longer creates a duplicate. Flipped the matching tests to assert the new behavior. Ran the suite after every change; it ends at 175 passing.
- **UI.** Wired `sort_by_time`, `filter_tasks`, `detect_conflicts`, `complete_task` and `suggest_free_time` into `app.py`. I checked it by driving the app with Streamlit's headless test harness: add pets and tasks, trigger a conflict, filter, mark a task done, generate a schedule. No exceptions.
- **Diagram.** Compared the Phase 1 draft with the code, listed the drift (a missing method, a missing `owner` attribute, a wrong return type, missing `Scheduler` to `Pet` and `Task` dependencies), redrew it, and exported a PNG.
- **Third capability.** Weighted prioritization with aging: a task's score is its priority points (high 10, medium 5, low 2) plus 1 per day overdue, so a task that keeps getting skipped eventually wins a slot. Strict priority stays the default. It added a "Planning style" choice in the app and a demo in `main.py`. Free-slot suggestion (`suggest_free_time`) was the other capability added beyond the basics.
- **Docs.** Rewrote the README, filled in the reflection, and replaced the README's partial sample output with the full real output of `python main.py`.
- **Independent checks.** It ran two multi-agent workflows: four fact-checkers over the reflection, then three reviewers over the new feature (one tried to break the code, one mutated a copy of it to see if the tests noticed, one checked the docs against the code).
- **Git.** Committed the test suite as `4f9f9ee` and pushed it to `main` using the message I gave.

### What I had to verify or fix manually

**Corrections I made as the human in the loop**

- **Commit message.** The agent's first commit command added a `Co-Authored-By` trailer. I rejected that command and told it to remove the trailer, so the pushed commit has none (earlier commits in the history still carry it).
- **Screenshots.** The agent cannot see my browser, so I ran the app myself and supplied the three screenshots. They showed something the tests had not: the plan can contain two tasks at 08:00, because the plan chooses tasks by priority and time and does not resolve clashes. That is now listed as a limitation in the README and the reflection.
- **Image handling.** I decided to keep the screenshots as normal inline README images with the files in `docs/`, rather than embedding them as base64.

**Things the agent got wrong, and how they were caught**

| Mistake | How it was caught | Fix |
|---------|-------------------|-----|
| The first diagram PNG showed `__init__`, `__post_init__` and `__str__` as bold "init", "post_init", "str" (Mermaid reads double underscores as markdown) | Opening the rendered PNG, not the `.mmd` text | Escaped the underscores in the Mermaid source and re-rendered |
| `main.py` had a syntax error after the weighted demo was inserted (an escaped newline became a real one inside a string) | Running `python main.py` | Fixed the three strings by hand-editing them |
| The README's first sample output was only the start of the real `main.py` output | Running the command and comparing | Replaced it with the full output |
| The README still said `app.py` was not connected to the logic layer, and a screenshot predated the Planning style option | Reading the README against the code; the review workflow flagged the screenshot | Updated the text; added a note under the screenshot that it shows the default mode |
| Reflection and README claims that were wrong or overstated: completion status described as a ranking factor (it is a filter), the plan explanation "exactly" matching a quoted phrase, midnight called untested, the Co-Authored-By trailer called dropped, the commit history called a clean match for the phases | The reflection fact-check workflow (8 problems found in total) | Reworded each one against the code and git history |
| The reflection listed sorting tie-break by priority and sorting an empty owner as tested; no test existed for either | The same fact-check workflow | Added 3 tests rather than shrinking the claim |
| Several bugs injected into the weighted explanation survived all 172 tests (the explanation ignoring the weighted flag, a wrong minutes-used line, wrong numbers in the scoring text) | The mutation reviewer (39 of 43 injected bugs were caught; the survivors were all here) | Added 3 tests; re-injecting the bugs now fails them |
| Edited `diagrams/uml.mmd` in place, overwriting the Phase 1 draft | Realizing, when saving `uml_final.mmd`, that the Phase 1 draft was worth keeping for the reflection's comparison | Restored it with `git checkout`; the final diagram lives in `uml_final.mmd` |

### Follow-up task: data persistence

**Asked:** make PawPal+ remember pets and tasks between runs by saving them to `data.json`.

**Files modified:** `pawpal_system.py` (`to_dict` / `from_dict` on `Task`, `Pet` and `Owner`; `Owner.save` and `Owner.load`), `app.py` (load at start, autosave, a "Saved data" panel with a confirmed delete, a warning for an unreadable file), `main.py` (a save-and-reload demo), `.gitignore` (`data.json` and its temporary and `.corrupt` files), `diagrams/uml_final.mmd` and `.png`, `README.md` (new Data persistence section, walkthrough step 9, tests table, limitations), `reflection.md` (counts and now-stale statements), and two new test files, `tests/test_persistence.py` (76 tests) and `tests/test_app_persistence.py` (9 tests that drive the real app). The suite grew from 175 to 260 tests.

**Completed:** atomic writes, a versioned file format, strict validation on load (one bad value rejects the whole file), and an unreadable file is kept as `data.json.corrupt` instead of being overwritten. In the app, the saved owner name and time budget now seed their widgets; before that the widgets' own defaults would have overwritten them on every restart.

**Corrections and checks:** I ran the app tests against a temporary file (`PAWPAL_DATA_FILE`) so the suite never touches a real `data.json`, and confirmed none appeared in the project folder. While updating the diagram, the double-underscore escapes (`#95;`) in the Mermaid source made my first patch miss `__str__`; I caught it from the failed assertion and patched the escaped form. Statements in the README and reflection that persistence made untrue ("no saved data", "data disappears when the page reloads", "the UI is not in the test suite") were rewritten.

**Not verifiable from the repository:** the accounts in `reflection.md` of earlier chat sessions (which suggestions were accepted or rejected, the earlier mutation-test counts) are recorded from my own recollection. Only the work listed above is backed by this log and the git history.

---

## Prompt Comparison (SF11)

> Compare two different prompts (or two different models) on the same task.

| | Option A | Option B |
|-|----------|----------|
| **Model / tool used** | | |
| **Prompt** | | |
| **Response summary** | | |
| **What was useful** | | |
| **Problems noticed** | | |
| **Decision** | | |

**Which approach did you use in your final implementation and why?**

<!-- Your conclusion -->
