"""The Streamlit app saves to the data file and reloads it on the next run (driven with Streamlit's test harness)."""

import json
from datetime import time
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")


@pytest.fixture
def data_file(tmp_path, monkeypatch):
    path = tmp_path / "data.json"
    monkeypatch.setenv("PAWPAL_DATA_FILE", str(path))
    return path


def start() -> AppTest:
    """A fresh run of the app, like opening it in a new browser tab."""
    return AppTest.from_file(APP, default_timeout=30).run()


def widget(at, kind, label):
    return next(w for w in getattr(at, kind) if w.label == label)


def click(at, label):
    next(b for b in at.button if b.label == label).click()
    at.run()


def add_pet(at, name, species="dog", age=3):
    widget(at, "text_input", "Pet name").set_value(name)
    widget(at, "selectbox", "Species").set_value(species)
    widget(at, "number_input", "Age (years)").set_value(age)
    click(at, "Add pet")


def add_task(at, pet, description, at_time=time(8, 0), minutes=30, priority="high", repeats="once"):
    widget(at, "selectbox", "Pet").set_value(pet)
    widget(at, "text_input", "Task description").set_value(description)
    widget(at, "time_input", "Time").set_value(at_time)
    widget(at, "number_input", "Duration (minutes)").set_value(minutes)
    widget(at, "selectbox", "Priority").set_value(priority)
    widget(at, "selectbox", "Repeats").set_value(repeats)
    click(at, "Add task")


def task_rows(at):
    """Rows of the sorted task table (the only table with a Repeats column)."""
    for table in at.table:
        if "Repeats" in table.value.columns:
            return table.value.to_dict("records")
    return []


def pet_rows(at):
    for table in at.table:
        if "Species" in table.value.columns:
            return table.value.to_dict("records")
    return []


def test_a_fresh_start_creates_no_file_until_something_changes(data_file):
    at = start()
    assert not at.exception and not data_file.exists()


def test_pets_and_tasks_are_still_there_after_a_restart(data_file):
    at = start()
    add_pet(at, "Buddy", "dog", 3)
    add_task(at, "Buddy", "Morning walk", time(8, 0), 30, "high", "daily")
    assert data_file.exists()

    again = start()  # a brand-new session: nothing is carried over except the file
    assert not again.exception
    assert [(r["Name"], r["Species"], r["Age"], r["Tasks"]) for r in pet_rows(again)] == [("Buddy", "dog", 3, 1)]
    rows = task_rows(again)
    assert [(r["Task"], r["Time"], r["Pet"], r["Min"], r["Priority"], r["Repeats"], r["Done"]) for r in rows] == [
        ("Morning walk", "08:00", "Buddy", 30, "high", "daily", "no")
    ]


def test_the_owner_name_and_time_budget_are_remembered(data_file):
    at = start()
    widget(at, "text_input", "Owner name").set_value("Sam")
    widget(at, "number_input", "Minutes available today").set_value(90)
    at.run()
    assert json.loads(data_file.read_text(encoding="utf-8"))["owner"]["available_minutes"] == 90

    again = start()
    assert widget(again, "text_input", "Owner name").value == "Sam"
    assert widget(again, "number_input", "Minutes available today").value == 90


def test_marking_a_task_done_and_its_follow_up_are_saved(data_file):
    at = start()
    add_pet(at, "Buddy")
    add_task(at, "Buddy", "Morning walk", repeats="daily")
    click(at, "Mark complete")

    again = start()
    rows = task_rows(again)
    assert [(r["Task"], r["Done"]) for r in rows] == [("Morning walk", "yes"), ("Morning walk", "no")]
    assert rows[0]["Date"] != rows[1]["Date"]  # the follow-up is on a later day


def test_every_pet_and_task_is_saved_not_just_the_latest(data_file):
    at = start()
    add_pet(at, "Buddy")
    add_pet(at, "Mia", "cat", 2)
    add_task(at, "Buddy", "Walk", time(8, 0))
    add_task(at, "Mia", "Feed", time(9, 0), 10)
    add_task(at, "Buddy", "Brush", time(17, 0), 15, "low")

    again = start()
    assert {r["Name"]: r["Tasks"] for r in pet_rows(again)} == {"Buddy": 2, "Mia": 1}
    assert [r["Task"] for r in task_rows(again)] == ["Walk", "Feed", "Brush"]


def test_a_clash_is_still_reported_after_a_restart(data_file):
    at = start()
    add_pet(at, "Buddy")
    add_task(at, "Buddy", "Walk", time(8, 0))
    add_task(at, "Buddy", "Brush", time(8, 0), 10)

    again = start()
    assert any("Conflict on" in w.value for w in again.warning)


def test_an_unreadable_data_file_is_kept_and_the_app_starts_empty(data_file):
    data_file.write_text("{this is not json", encoding="utf-8")
    at = start()
    assert not at.exception
    assert any("Could not load data.json" in w.value for w in at.warning)
    assert pet_rows(at) == []
    kept = data_file.with_name("data.json.corrupt")
    assert kept.read_text(encoding="utf-8") == "{this is not json"  # not overwritten or lost

    add_pet(at, "Buddy")  # the next save writes a fresh, valid file next to the kept one
    assert json.loads(data_file.read_text(encoding="utf-8"))["owner"]["pets"][0]["name"] == "Buddy"
    assert kept.exists()


def test_a_file_with_invalid_task_data_is_not_half_loaded(data_file):
    bad = {"version": 1, "owner": {"name": "Sam", "available_minutes": 90, "pets": [
        {"name": "Buddy", "species": "dog", "age": 3, "tasks": [
            {"description": "Walk", "time": "8am", "duration": 30, "priority": "high",
             "frequency": "once", "completed": False, "due_date": "2026-03-02"}]}]}}
    data_file.write_text(json.dumps(bad), encoding="utf-8")
    at = start()
    assert not at.exception and pet_rows(at) == [] and task_rows(at) == []
    assert any("Could not load" in w.value for w in at.warning)


def test_delete_all_saved_data_needs_the_checkbox_and_then_empties_everything(data_file):
    at = start()
    add_pet(at, "Buddy")
    add_task(at, "Buddy", "Walk")
    assert data_file.exists()

    delete = next(b for b in at.button if b.label == "Delete all saved data")
    assert delete.disabled  # nothing happens until the box is ticked
    next(c for c in at.checkbox if c.label == "I want to delete all pets and tasks").check()
    at.run()
    click(at, "Delete all saved data")

    assert not data_file.exists()
    assert pet_rows(at) == [] and task_rows(at) == []
    assert pet_rows(start()) == []
