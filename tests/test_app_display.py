"""What the Streamlit app shows: the tally, legend, task picker, schedule section and literal text (Streamlit's test harness)."""

import json
from datetime import date, timedelta
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from formatting import LEGEND

APP = str(Path(__file__).resolve().parent.parent / "app.py")
TODAY = date.today()


def task(description, time, duration, priority, frequency="once", *, done=False, days_ago=0):
    return {
        "description": description, "time": time, "duration": duration, "priority": priority, "frequency": frequency,
        "completed": done, "due_date": (TODAY - timedelta(days=days_ago)).isoformat(),
    }


def household(minutes=60, buddy_tasks=None, mia_tasks=None, buddy="Buddy"):
    return {"version": 1, "owner": {"name": "Sam", "available_minutes": minutes, "pets": [
        {"name": buddy, "species": "dog", "age": 3, "tasks": buddy_tasks if buddy_tasks is not None else [
            task("Morning walk", "08:00", 30, "high", "daily"),
            task("Grooming", "16:00", 45, "low"),
            task("Old meds", "07:00", 5, "high", days_ago=2),  # overdue
        ]},
        {"name": "Mia", "species": "cat", "age": 2, "tasks": mia_tasks if mia_tasks is not None else [
            task("Breakfast", "08:00", 10, "high"),
            task("Vet visit", "10:00", 20, "medium", done=True),
            task("Early bath", "06:00", 10, "low", done=True, days_ago=3),  # sorts before every planned task
        ]},
    ]}}


@pytest.fixture
def start(tmp_path, monkeypatch):
    """Return a function that writes `payload` to a throwaway data file and opens the app on it."""
    monkeypatch.setenv("PAWPAL_DATA_FILE", str(tmp_path / "data.json"))

    def open_app(payload):
        (tmp_path / "data.json").write_text(json.dumps(payload), encoding="utf-8")
        return AppTest.from_file(APP, default_timeout=30).run()

    return open_app


def widget(at, kind, label):
    return next(w for w in getattr(at, kind) if w.label == label)


def frame(at, column):
    """The first dataframe that has `column`."""
    return next(f.value for f in at.dataframe if column in f.value.columns)


def generate(at):
    next(b for b in at.button if b.label == "Generate schedule").click()
    at.run()


# --- Tally, legend and task picker ------------------------------------------------------------------------------


def test_the_tally_counts_every_task_by_status(start):
    at = start(household())
    assert not at.exception
    assert [(m.label, m.value) for m in at.metric] == [("📋 Tasks", "6"), ("⏳ Pending", "3"), ("🚨 Overdue", "1"), ("✅ Done", "2")]


def test_filters_change_the_table_but_not_the_tally(start):
    at = start(household())
    widget(at, "selectbox", "Show pet").set_value("Mia")
    widget(at, "radio", "Show tasks").set_value("Completed")
    at.run()
    assert list(frame(at, "Repeats")["Task"]) == ["Early bath", "Vet visit"]
    assert [(m.label, m.value) for m in at.metric] == [("📋 Tasks", "6"), ("⏳ Pending", "3"), ("🚨 Overdue", "1"), ("✅ Done", "2")]


def test_the_legend_sits_under_the_task_table(start):
    at = start(household())
    assert LEGEND in [c.value for c in at.caption]


def test_task_table_has_icons_and_colour_coded_priority_and_status(start):
    table = frame(start(household()), "Repeats")
    assert list(table.columns) == ["Date", "Time", "Type", "Task", "Pet", "Min", "Priority", "Repeats", "Status"]
    rows = {r["Task"]: r for r in table.to_dict("records")}
    assert (rows["Old meds"]["Type"], rows["Old meds"]["Priority"], rows["Old meds"]["Status"]) == ("💊", "🔴 High", "🚨 Overdue")
    assert (rows["Morning walk"]["Type"], rows["Morning walk"]["Status"], rows["Morning walk"]["Repeats"]) == ("🦮", "⏳ Pending", "daily")
    assert (rows["Grooming"]["Type"], rows["Grooming"]["Priority"]) == ("🛁", "🟢 Low")
    assert (rows["Vet visit"]["Type"], rows["Vet visit"]["Priority"], rows["Vet visit"]["Status"]) == ("🏥", "🟡 Medium", "✅ Done")


def test_the_mark_done_list_offers_only_open_tasks_each_with_its_icon(start):
    options = widget(start(household()), "selectbox", "Mark a task done").options
    assert len(options) == 4 and not any("Vet visit" in o for o in options)  # the completed task is not offered
    assert any(o.startswith("💊") and "Old meds (Buddy)" in o for o in options)
    assert any(o.startswith("🦮") and "Morning walk (Buddy)" in o for o in options)
    assert any(o.startswith("🍖") and "Breakfast (Mia)" in o for o in options)
    assert any(o.startswith("🛁") and "Grooming (Buddy)" in o for o in options)
    assert all(f"{TODAY:%b %d}" in o or f"{TODAY - timedelta(days=2):%b %d}" in o for o in options)  # each shows its date


# --- The schedule section ---------------------------------------------------------------------------------------


def test_generate_schedule_shows_the_plan_with_icons_and_a_time_budget_bar(start):
    at = start(household(minutes=60))
    generate(at)
    assert not at.exception
    plan = next(f.value for f in at.dataframe if "Repeats" not in f.value.columns and "Priority" in f.value.columns and "Species" not in f.value.columns)
    assert list(plan.columns) == ["Time", "Type", "Task", "Pet", "Min", "Priority"]
    assert list(plan["Task"]) == ["Old meds", "Morning walk", "Breakfast"]  # Grooming (45 min) no longer fits
    assert list(plan["Type"]) == ["💊", "🦮", "🍖"]
    assert list(plan["Priority"]) == ["🔴 High"] * 3
    assert [s.value for s in at.success][-1] == "3 task(s), 45 of 60 minutes used."
    (bar,) = at.get("progress")
    assert (bar.value, bar.text) == (75, "Time budget: 45 of 60 minutes")


def test_a_full_budget_fills_the_bar_and_a_zero_budget_has_none(start):
    at = start(household(minutes=90))
    generate(at)
    (bar,) = at.get("progress")
    assert bar.value == 100 and bar.text == "Time budget: 90 of 90 minutes"
    empty = start(household(minutes=0))
    generate(empty)
    assert not empty.exception and empty.get("progress") == []


def test_priority_with_aging_adds_a_score_column_matching_each_row(start):
    at = start(household(minutes=60))
    widget(at, "radio", "Planning style").set_value("Priority with aging")
    at.run()
    generate(at)
    plan = next(f.value for f in at.dataframe if "Score" in f.value.columns)
    assert list(plan.columns) == ["Time", "Type", "Task", "Pet", "Min", "Priority", "Score"]
    assert dict(zip(plan["Task"], plan["Score"])) == {"Old meds": 12, "Morning walk": 10, "Breakfast": 10}  # 10 + 2 days overdue for the meds


def test_strict_priority_has_no_score_column(start):
    at = start(household(minutes=60))
    generate(at)
    assert not any("Score" in f.value.columns for f in at.dataframe)


# --- Text is shown literally, not as Markdown ----------------------------------------------------------------------

TRICKY = "[click me](http://evil.example/x) **bold** ![px](http://127.0.0.1:9/p.png) # big"


def test_task_and_pet_names_are_shown_as_typed_not_as_markdown(start):
    payload = household(
        buddy="Rex_*the*_dog",
        buddy_tasks=[task(TRICKY, "08:00", 30, "high"), task("Plain walk", "08:00", 30, "medium")],  # same start: a conflict
        mia_tasks=[],
    )
    at = start(payload)
    assert not at.exception
    table = frame(at, "Repeats")
    assert TRICKY in list(table["Task"]) and set(table["Pet"]) == {"Rex_*the*_dog"}  # the table cells are untouched
    assert frame(at, "Species")["Name"].tolist() == ["Rex_*the*_dog", "Mia"]
    warnings = " ".join(w.value for w in at.warning)
    assert r"\[click me\]\(http://evil.example/x\)" in warnings and r"\*\*bold\*\*" in warnings
    assert r"Rex\_\*the\*\_dog" in warnings
    assert "[click me](" not in warnings and "![px](" not in warnings  # no live link or image syntax is left


def test_the_done_message_escapes_the_task_name(start):
    at = start(household(buddy_tasks=[task(TRICKY, "08:00", 30, "high")], mia_tasks=[]))
    next(b for b in at.button if b.label == "Mark complete").click()
    at.run()
    assert any(r"Completed '\[click me\]\(http://evil.example/x\)" in s.value for s in at.success)


def test_messages_about_a_task_escape_its_name_too(start):
    at = start(household(buddy_tasks=[], mia_tasks=[]))
    widget(at, "text_input", "Task description").set_value(TRICKY)
    next(b for b in at.button if b.label == "Add task").click()
    at.run()
    assert not at.exception
    assert any(r"Added '\[click me\]\(http://evil.example/x\)" in s.value for s in at.success)
