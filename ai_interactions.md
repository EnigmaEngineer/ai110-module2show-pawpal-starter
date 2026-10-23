# AI Interactions Log

> **Stretch features only.** Only fill in the sections that apply to stretch features you attempted. If you did not attempt a stretch feature, leave its section blank or delete it. This file is not required for the core project.

---

## Agent Workflow (SF7)

> Document your experience using an AI agent (e.g., Cursor Agent, Claude, Copilot) to make multi-step changes autonomously.

The agent was Claude Code, running in VS Code with permission to read and edit files, run the shell, and start sub-agents. This log covers the final stretch of the project: hardening the scheduler, polishing the UI, redrawing the UML and writing the docs. Earlier phases (class skeletons, first implementation) are in the git history, not here.

### Files modified

| File | What changed | Commit |
|------|--------------|------------|
| `pawpal_system.py` | Overlap detection in `detect_conflicts`; `complete_task` reuses an identical pending follow-up instead of adding a copy; new `suggest_free_time`; new weighted prioritization (`task_score`, `weighted=` on `generate_plan` / `explain_plan`) | `4f9f9ee`, `330e860` |
| `tests/test_pawpal.py` | Grew from 126 to 175 tests: leap days, overlap, duplicate follow-up, free slots, sorting tie-breaks, weighted planning | `4f9f9ee`, `330e860` |
| `app.py` | Conflict banner above a sorted table, pet and status filters, "Mark a task done", next-free-slot message when a new task clashes, "Planning style" choice | `330e860` |
| `main.py` | Added a weighted-planning section to the terminal demo | `330e860` |
| `README.md` | Rewritten as a manual: features, demo walkthrough with real CLI output, scheduler behavior, testing, limitations | `4f9f9ee`, `330e860` |
| `reflection.md` | Filled in sections 1c, 2, 3c, 4 and 5; corrected two stale facts in 3b | `4f9f9ee`, `330e860` |
| `diagrams/uml_final.mmd`, `uml_final.png` | New: the final class diagram, redrawn from the code | `330e860` |
| `diagrams/uml.mmd` | Edited, then restored with `git checkout` so it stays as the Phase 1 draft | n/a |
| `docs/screenshot-*.png` | Three screenshots I took of the running app | `330e860` |
| `ai_interactions.md` | This section | `330e860` |

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

**Files modified:** `pawpal_system.py` (`to_dict` / `from_dict` on `Task`, `Pet` and `Owner`; `Owner.save_to_json` and `Owner.load_from_json`), `app.py` (load at start, autosave, a "Saved data" panel with a confirmed delete, a warning for an unreadable file), `main.py` (a save-and-reload demo), `.gitignore` (`data.json` and its temporary and `.corrupt` files), `diagrams/uml_final.mmd` and `.png`, `README.md` (new Data persistence section, walkthrough step 9, tests table, limitations), `reflection.md` (counts and now-stale statements), and two new test files, `tests/test_persistence.py` (91 tests) and `tests/test_app_persistence.py` (24 tests that drive the real app). The suite grew from 175 to 290 tests.

**Completed:** atomic writes, a versioned file format, strict validation on load (one bad value rejects the whole file), and an unreadable file is kept as `data.json.corrupt` instead of being overwritten. In the app, the saved owner name and time budget now seed their widgets; before that the widgets' own defaults would have overwritten them on every restart.

**Corrections and checks:** I ran the app tests against a temporary file (`PAWPAL_DATA_FILE`) so the suite never touches a real `data.json`, and confirmed none appeared in the project folder. While updating the diagram, the double-underscore escapes (`#95;`) in the Mermaid source made my first patch miss `__str__`; I caught it from the failed assertion and patched the escaped form. Statements in the README and reflection that persistence made untrue ("no saved data", "data disappears when the page reloads", "the UI is not in the test suite") were rewritten.

**Review and hardening (after the first commit):** the request named the methods `save_to_json` and `load_from_json`, so I renamed `Owner.save` and `Owner.load` to those everywhere (engine, app, demo, tests, docs, diagram). A three-reviewer workflow then attacked the feature: one tried to lose data, one injected 116 bugs into copies of the code (81 caught by the tests at the time), one checked the docs against the code. The real problems it found, all fixed: the app crashed on startup if the data path was a folder or the JSON was absurdly nested; a valid file with a byte-order mark was treated as corrupt; a second unreadable file overwrote the first backup; if the unreadable file could not be moved aside the next save could overwrite it; and two browser windows could silently erase each other's work (the app now checks that the file is unchanged before writing and asks which version to keep). I also added the tests it said were missing and re-injected 14 bugs into the fixed code to confirm the suite catches each one; one survived because my first version of the failed-move test patched too much, which I corrected. It also found that the Commit column in the table above was out of date, which is now fixed. One item I chose not to change: the engine accepts very large ages and durations from a hand-edited file, which the app's table cannot display.

### Follow-up task: priority-first sorting

**Asked:** add a Low, Medium or High priority to `Task` and update the `Scheduler` to sort by priority first, then by time.

**What was already there:** `Task` already had a validated `priority` ("low", "medium" or "high") and the daily plan already chose tasks by priority, so no change to `Task` was needed. What was missing was a plain sort of the task list by priority.

**Files modified:** `pawpal_system.py` (new `Scheduler.sort_by_priority`), `app.py` (an **Order by** choice, Time or Priority first, that works together with the filters), `main.py` (a short demo section), `diagrams/uml_final.mmd` and `.png`, `README.md`, `reflection.md`, `tests/test_pawpal.py` (15 new tests) and a new `tests/test_app_ordering.py` (4 tests that drive the real app against a temporary data file).

**Design choice:** the sort key is priority, then due date, then time of day, not priority then time alone. With tasks on several days, time alone would interleave days; putting the due date second keeps overdue tasks first within a priority and matches the order the daily plan already uses. The key is stable, so full ties keep the order they were added.

**Checks:** I injected 7 bugs into a copy of the sort (time before priority, priority ignored, low before high, due date or time dropped, time reversed, completed tasks dropped); the tests caught all 7. One of my own test expectations was wrong at first (ties follow the order `get_all_tasks` lists tasks, pet by pet, not the global order they were added) and I corrected the test, not the code.

### Follow-up task: CLI output examples in the README

**Asked:** show the enhanced scheduling logic as terminal output in the README, not screenshots.

**Done:** added an overlap-and-free-slot section to the `main.py` demo (it previously had no example of overlap detection or the free-slot search), added `tests/test_demo.py` (5 tests when first added, 11 now, that run the demo and check each section's key lines, so the quoted output cannot quietly drift from what the code prints), and added a README subsection, "Enhanced scheduling logic in action", with one real excerpt per feature: priority-first sorting, conflict and overlap warnings with free slots, weighted prioritization, daily recurrence and late completion, and saving and reloading. The excerpts are cut from a real run of `python main.py`, not typed by hand.

### Follow-up task: professional UI and output formatting

**Asked:** add friendly output such as colour-coded status indicators, emojis for task types, or structured CLI tables with a library like `tabulate`. I took all three.

**Files modified:** new `formatting.py` (icons, labels, summaries, a time gauge and `tabulate` tables, shared by the app and the demo), `app.py` (tally metrics, icon column, colour-coded priority and status, a progress bar for the time budget), `main.py` (boxed tables, a legend, UTF-8 output), `requirements.txt` (`tabulate`, `wcwidth`), `tests/test_formatting.py` (new: 56 tests when first written, 194 now), `tests/test_demo.py` and `tests/test_app_persistence.py` (updated for the new table layout), `README.md`, `reflection.md`, `diagrams/uml_final.mmd` and this file.

**Design choices:** display code lives in `formatting.py`, not in the engine, so `pawpal_system.py` still prints nothing. Colour comes from emoji circles instead of ANSI escape codes, so it also works in redirected output and in the browser. Task "types" are guessed from the description rather than stored, which avoided a new field and a change to the saved file format.

**Problems caught while building it:** a Windows console on the legacy code page cannot print emoji at all, and my first run failed with a `UnicodeEncodeError`; `main.py` now switches its output to UTF-8 when run as a script. I picked only emoji that are reliably two columns wide, because a variation-selector emoji such as the warning sign would misalign the table borders. A test caught that my "Washington" example matched the washing pattern, because the patterns allowed any word ending, so I tightened them to specific word endings. A script I used to patch the code turned a regex word-boundary escape into a backspace character in sixteen places, which the new tests exposed immediately; I restored them and scanned every source and doc file for stray control characters.

**Review and fixes:** a three-reviewer workflow then attacked the formatting work. It found three real problems, all fixed: (1) task and pet names went into `st.table` and `st.warning` as Markdown, so a task named `[click](http://x)` became a live link and an image link made the browser fetch the address (HTML was already escaped, so this was not script injection); the app now uses dataframes for its tables and `escape_markdown` for its messages; (2) `main.main()` crashed with a `UnicodeEncodeError` when called from another program on a legacy console, because the UTF-8 switch only ran in the script entry block; it now runs at the start of `main()`; (3) the app failed to start in a virtual environment that lacked `tabulate`, which was true of this project's own `.venv`; the import is now optional with a plain-text fallback. The reviewer also injected 224 bugs, and 112 survived the tests I had. I added tests for the meaningful ones (every word each icon pattern knows, the precedence between kinds, the exact column order, numeric-looking text, the fallback, escaping, the demo run on a legacy encoding, and the app's tally, legend, task picker, schedule section, progress bar and score column) and re-injected 13 targeted bugs to confirm they are caught; one of those initially survived because my sample data hid it, so I added an early completed task to make the plan and the full list differ. I did not re-run all 224. Eight of the survivors cannot be killed by any test (defensive clamps and guards that the app can never reach), and I left them. The suite is now 526 tests.

**Not verifiable from the repository:** the accounts in `reflection.md` of earlier chat sessions (which suggestions were accepted or rejected, the earlier mutation-test counts) are recorded from my own recollection. Only the work listed above is backed by this log and the git history.

---

## Prompt Comparison (SF11)

> Compare two different prompts (or two different models) on the same task.

Four tools answered the same prompt: **Claude Opus 5.5**, **Claude Haiku 5.5**, **Gemini 3.5 Flash-Lite** and **GPT-6**. The two Claude models were run as sub-agents inside Claude Code. Gemini and GPT-6 were run by hand in their own chat apps and only their code was copied back. The model names for those two are as I reported them; I have no record of the date or the plan tier.

### The task

I picked the logic for **rescheduling a weekly task**, written as one pure function, `reschedule_weekly`. It is a good test because it combines several things that are easy to get subtly wrong:

- weekday arithmetic that survives month ends, year ends and leap days;
- "strictly after the later of the due date and the completion date", so a late completion never lands in the past;
- finding the earliest whole-minute start that avoids unsorted, duplicated and overlapping busy blocks, with blocks that merely touch allowed;
- blocks that run past midnight counting only on their own day;
- a limit on how many weeks to try, and a list of inputs that must raise `ValueError`.

The full prompt, with the rules and three worked examples, is in [`prompt_comparison/PROMPT.md`](prompt_comparison/PROMPT.md).

### How it was run

- **Same prompt, word for word.** Every tool got the text of `PROMPT.md`. The two Claude models also got one line about how to hand the answer back (a structured reply with code, approach and ambiguities) and ran as fresh sub-agents in Claude Code (`claude-opus-5-5`, `claude-haiku-5-5`). Gemini and GPT-6 were each given the prompt once in a chat app, with no extra line and no follow-up questions.
- **No peeking.** The Claude models could test their code in their own scratch folder and were told not to read anything else. I checked their logged tool calls afterwards: none of the four Claude agents (two solvers, two reviewers) opened the hidden tests or any project file. Gemini and GPT-6 never had access to the project at all.
- **Scored by tests, not by impression.** The scoring files are in [`prompt_comparison/`](prompt_comparison/): 84 hand-computed cases in five groups (which day, busy blocks, full days and how many weeks to try, the end of the day, bad input), 5 checks on behaviour such as not mutating arguments, and 2,000 seeded random inputs compared with a reference answer. Run it with `python prompt_comparison/evaluate.py prompt_comparison/solutions/claude_opus.py prompt_comparison/solutions/gpt_6.py` (and so on). No model saw any of this.
- **Blind review of the two Claude answers.** Two Claude Sonnet 5.5 reviewers compared them without knowing which model wrote which, once with each listed first. I did not run this for Gemini and GPT-6, so those two have only my own reading and the tests.
- **Only code came back from Gemini and GPT-6.** The prompt also asked for an explanation and a list of ambiguities. What I pasted back was the code alone, so there is nothing to compare for those two on explanation quality.

### Comparison

| | Option A | Option B | Option C | Option D |
|-|----------|----------|----------|----------|
| **Model / tool used** | Claude Opus 5.5, Claude Code sub-agent | Claude Haiku 5.5, Claude Code sub-agent | Gemini 3.5 Flash-Lite, chat app | GPT-6, chat app |
| **Prompt** | Identical text | Identical text | Identical text | Identical text |
| **Response summary** | 67 lines, 1 comment. Validates everything first, groups busy blocks by day clipped at midnight, sorts each candidate day's blocks once and sweeps through them. Explained its approach and listed 7 ambiguities. | 66 lines, 4 comments. Same validation and grouping, then repeatedly finds a block that overlaps the slot and jumps the start to its end. Listed 9 ambiguities. | 75 lines, 4 comments. Validates, finds the first candidate day, then for each week scans the whole busy list for that day and jumps past the latest-ending overlapping block. Code only. | 81 lines, 8 comments plus a docstring. Same sort-and-sweep as Opus with the clearest comments of the four. Code only. |
| **What was useful** | Fastest design: 1, 5 and 19 ms on 1,000, 5,760 and 20,000 one-minute blocks. Regex `fullmatch` with `[0-9]` is strict. Only 2 tool calls. | Easiest loop to read and verify. Works out each candidate date from the week number, so it never steps past the last representable date. Noticed the end-of-calendar risk and wrote it down. | Correct on all the main logic and the lazy per-week date (no end-of-calendar error). Checks that each busy block is a list or tuple of three. Jumps past the latest-ending overlap, which is right. | Strict validation: rejects a trailing newline, booleans and floats. Fast (7 ms and 24 ms at 5,760 and 20,000 blocks). Docstring and comments make it the easiest to review. |
| **Problems noticed** | Adds a week after every failed attempt, including the last, so a task due Friday 9999-12-24 with the last day booked and `max_weeks=1` raises `OverflowError` instead of returning `None`. I reproduced it. The explanation did not mention it. | Rescans every block on each jump (worst case quadratic): 26, 56 and 68 ms on the same three days, 15 to 30 times slower than A and still fast in absolute terms. Digit check done one character at a time. | **Weakest input checking.** Its regex uses `$`, which also matches before a trailing newline, so `"08:00\n"` is accepted (the rules say that must raise). It also accepts full-width and Arabic-Indic digits, `True` and `30.5` as a duration, and `True` as `max_weeks`; a string duration or `None` for `max_weeks` raises `TypeError`, not `ValueError`. Slowest in the worst cases (95 ms at 20,000 blocks, 50 ms over 61 weeks). | Same end-of-calendar `OverflowError` as A, for the same reason. `\d` without an ASCII flag lets a non-ASCII digit through in the last minute digit (`"08:0٠"` is accepted). A comment says "at or before our end" where the test is strict. |
| **Score on my hidden tests** | 83 of 84 cases, 5 of 5 checks, 2,000 of 2,000 random | **84 of 84**, 5 of 5, 2,000 of 2,000 | 82 of 84 (both misses are the trailing newline), 5 of 5, 2,000 of 2,000 | 83 of 84 (the end-of-calendar case), 5 of 5, 2,000 of 2,000 |
| **Effort** | 38,963 tokens, 2 tool calls, about 43 s | 45,095 tokens, 6 tool calls, about 43 s | Not measured | Not measured |
| **Blind review** | Judge 1 (A first): slightly worse. Judge 2 (B first): tie. | Judge 1: slightly better. Judge 2: tie. | Not reviewed | Not reviewed |
| **Decision** | Not used as is. Its sweep is worth keeping. | Not used as is. Its lazy candidate date is worth keeping. | Not used. The validation gaps are the reason. | Not used as is. Its comments and strict checks are worth copying. |

### Scores changed as I added cases, and I want that on record

I added test cases after seeing answers, so how the four rank depends on which extra checks I thought of:

| Cases | Opus | Haiku | Gemini | GPT-6 |
|-------|------|-------|--------|-------|
| First 81 (written before any model ran) | 81 | 81 | 81 | 81 |
| Plus case 82: end-of-calendar `max_weeks=1` (added after a reviewer spotted it in Opus's code) | 81 of 82 | 82 | 82 | 81 of 82 |
| Plus cases 83 and 84: a time or busy start followed by a newline (added after I read Gemini's regex) | 83 of 84 | 84 | 82 of 84 | 83 of 84 |

So **all four tied on the original 81 cases.** The differences come from cases I added afterwards. Each added case follows directly from a rule that was already in the prompt (return `None` when nothing fits; raise `ValueError` for a time that is not exactly zero-padded `HH:MM`), and my own reference answer also had the end-of-calendar flaw until the review caught it. But a different reviewer might have added different cases and ranked them differently.

### What I learned from the comparison

- **A precise prompt makes the models agree.** All four got the main logic right: weekday, late completion, leap days, gaps that fit exactly, midnight, the busy blocks. The differences were all in corners the prompt did not spell out: the end of the calendar (Opus, GPT-6), strictness of input checks (Gemini), and speed on very crowded days (Haiku, Gemini). The comparison measured care in the corners, not whether any tool could do the main task.
- **No tool won on everything.** Haiku has the only perfect score but is among the slowest; Opus and GPT-6 are the fastest but share the calendar-end flaw; Gemini 3.5 Flash-Lite has the weakest validation. One run each is not enough to say anything general about the models, so I am not claiming that.
- **Speed barely matters for this app.** The slow cases need thousands of bookings on a single day. A pet scheduler has a handful of tasks a day, so the differences of tens of milliseconds would never show. Strict validation and readable code matter more here.
- **The comparison found a bug in my own reference answer.** I wrote it with the same one-week-too-far step as Opus. I fixed it and kept the added case.
- **Limits.** One run per tool; both Claude models and both reviewers are from the same vendor, so their blind spots may overlap (that is partly why the other two were worth running); I did not measure effort for Gemini or GPT-6.

### Which approach did you use in your final implementation and why?

**None of the four was merged into the app.** `reschedule_weekly` implements a different rule from the app's `complete_task` (which sets the next date to 7 days after the later of the due date and today and does no search for free time), and swapping it in would change behaviour that the 526 tests and the README describe. I kept it as a self-contained experiment in `prompt_comparison/`.

If I did wire it in, I would start from [`prompt_comparison/solutions/hybrid.py`](prompt_comparison/solutions/hybrid.py): Opus's single-pass sweep and strict ASCII regex check, with the next candidate date worked out from the week number as Haiku and Gemini do, and GPT-6's habit of explaining each step in a comment. It scores 84 of 84 cases and 2,000 of 2,000 random inputs. I wrote that file myself after the comparison, so it is not any tool's answer. If I had to pick one answer exactly as delivered, I would take Haiku's: it is the only one that passes everything and its loop is the easiest to check by eye.
