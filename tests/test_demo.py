"""The terminal demo (main.py) runs cleanly and shows each scheduling feature the README quotes."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

import main


def run_demo(capsys):
    main.main()
    return capsys.readouterr().out


def section(output, title):
    """Return the lines printed under a '=== title ===' heading, up to the next heading."""
    lines = output.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("===") and title in line)
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("===")), len(lines))
    return lines[start + 1:end]


def test_the_demo_runs_to_the_end_and_does_not_touch_a_data_file(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    output = run_demo(capsys)
    assert "Data persistence" in output
    assert list(tmp_path.iterdir()) == []  # the save-and-reload demo uses its own temporary folder


def task_order(lines, names):
    """Return the task names in the order their table rows appear in `lines`."""
    return [name for line in lines for name in names if f"│ {name} " in line]


def test_priority_sorting_puts_high_first_and_time_breaks_ties(capsys):
    lines = section(run_demo(capsys), "Priority-first sorting")
    split = lines.index("By priority (high first, then time):")
    names = ["Breakfast", "Play fetch", "Lunch walk", "Evening meds"]
    assert task_order(lines[:split], names) == ["Breakfast", "Play fetch", "Lunch walk", "Evening meds"]
    assert task_order(lines[split:], names) == ["Breakfast", "Evening meds", "Lunch walk", "Play fetch"]


def test_tables_show_task_icons_and_colour_coded_priority_and_status(capsys):
    output = run_demo(capsys)
    for label in ("🔴 High", "🟡 Medium", "🟢 Low", "⏳ Pending", "✅ Done"):
        assert label in output
    assert "🦮" in output and "🍖" in output and "💊" in output and "🛁" in output  # walk, meal, medicine, grooming
    assert "Priority: 🔴 high  🟡 medium  🟢 low" in output  # the legend
    assert "Time budget  [" in output and "75 of 90 min (83%)" in output


def test_overlap_section_shows_a_conflict_an_overlap_and_the_free_slots(capsys):
    text = "\n".join(section(run_demo(capsys), "Overlap detection"))
    assert "Conflict on" in text and "Long walk (Buddy), Brush (Buddy)" in text
    assert "Overlap on" in text and "09:00-10:00 runs into Feed (Mia) at 09:30" in text
    assert "Meds" in text and text.count("Overlap on") == 1  # starting the minute the walk ends is not an overlap
    assert "30 min, not before 08:00: 08:00" in text
    assert "15 min, not before 09:00: 10:05" in text
    assert "60 min, not before 09:00: 10:05" in text


def test_weighted_section_shows_strict_and_aging_choosing_different_tasks(capsys):
    text = "\n".join(section(run_demo(capsys), "Weighted prioritization"))
    strict, aging = text.split("Priority with aging:")
    assert "Evening walk" in strict.split("Left out")[0] and "Brush teeth" in strict.split("Left out")[1]
    assert "Brush teeth" in aging.split("Left out")[0] and "[score 7]" in aging
    assert "Evening walk" in aging.split("Left out")[1] and "[score 5]" in aging


def test_recurrence_sections_report_the_next_due_dates(capsys):
    output = run_demo(capsys)
    assert "new due_date == today + 1: True" in output
    assert "Late completion" in output and "== today + 1: True" in "\n".join(section(output, "Late completion"))


# --- Which tasks appear in which table, and in what order ---------------------------------------------------------

ALL_NAMES = [
    "Morning walk", "Breakfast", "Medication", "Evening walk", "Grooming", "Dinner", "Lunch walk", "Coffee break",
    "Long walk", "Brush", "Feed", "Meds", "Play fetch", "Evening meds", "Brush teeth",
]


def table_names(output, title):
    """Task names in the table printed right under the line `title`, top to bottom."""
    lines = output.splitlines()
    start = lines.index(title)
    end = next(i for i in range(start, len(lines)) if lines[i].strip().startswith("╰"))
    return [name for line in lines[start:end] for name in sorted(ALL_NAMES, key=len, reverse=True) if f"│ {name} " in line]


def test_todays_schedule_lists_only_the_planned_tasks_with_a_summary_and_gauge(capsys):
    output = run_demo(capsys)
    lines = section(output, "Today's Schedule")  # runs on until the next "===" heading, so cut it at the first table's bottom edge
    table = lines[: next(i for i, line in enumerate(lines) if line.strip().startswith("╰")) + 1]
    rows = [line for line in table if line.strip().startswith("│") and "Task" not in line]
    assert [name for line in rows for name in ALL_NAMES if f"│ {name} " in line] == ["Morning walk", "Breakfast", "Medication", "Evening walk"]
    assert not any("Grooming" in line for line in table)  # 45 minutes does not fit in what is left
    assert "  📋 4 tasks   ⏳ 4 pending   ✅ 0 done   🚨 0 overdue" in lines
    assert any(line.startswith("  Time budget  [") and line.endswith("75 of 90 min (83%)") for line in lines)


def test_the_demo_tables_hold_the_right_tasks_in_the_right_order(capsys):
    output = run_demo(capsys)
    assert table_names(output, "All tasks, sorted by time:") == ["Morning walk", "Breakfast", "Medication", "Grooming", "Evening walk"]
    assert table_names(output, "Buddy's pending tasks:") == ["Grooming", "Evening walk", "Morning walk"]
    assert table_names(output, "Completed tasks:") == ["Morning walk"]
    assert table_names(output, "Insertion order:") == ["Dinner", "Breakfast", "Lunch walk", "Coffee break"]
    assert table_names(output, "Via scheduler.sort_by_time():") == ["Breakfast", "Coffee break", "Lunch walk", "Dinner"]
    assert table_names(output, "Tasks:") == ["Long walk", "Brush", "Feed", "Meds"]
    assert table_names(output, "Reloaded tasks, sorted by time:") == ["Grooming", "Morning walk", "Medication"]
    assert table_names(output, "New task:") == ["Evening walk"]
    completed = output[output.index("Completed tasks:"):]
    assert "✅ Done" in completed.split("╰")[0]
    assert "✅ Done" in output[output.index("Reloaded tasks, sorted by time:"):].split("╰")[0]  # the saved, completed Medication


# --- Running as a program on a console that cannot print emoji ----------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent


def run_python(args, encoding_env, tmp_path):
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONIOENCODING", "PYTHONUTF8")}
    env.update(encoding_env)
    return subprocess.run([sys.executable, *args], cwd=ROOT, env=env, capture_output=True, timeout=120)


@pytest.mark.parametrize("encoding_env", [{"PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"}, {"PYTHONUTF8": "0"}], ids=["cp1252", "default"])
def test_running_main_py_on_a_legacy_console_encoding_still_prints_emoji(encoding_env, tmp_path):
    result = run_python(["main.py"], encoding_env, tmp_path)
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")[-400:]
    assert "🔴".encode("utf-8") in result.stdout and "╭".encode("utf-8") in result.stdout


@pytest.mark.parametrize("encoding_env", [{"PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"}], ids=["cp1252"])
def test_importing_main_and_calling_main_also_works_on_a_legacy_console(encoding_env, tmp_path):
    result = run_python(["-c", "import main; main.main()"], encoding_env, tmp_path)
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")[-400:]
    assert "🦮".encode("utf-8") in result.stdout
