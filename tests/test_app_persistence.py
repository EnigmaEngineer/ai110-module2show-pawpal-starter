"""The Streamlit app saves to the data file and reloads it on the next run (driven with Streamlit's test harness)."""

import json
import os
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
    for table in at.dataframe:
        if "Repeats" in table.value.columns:
            return table.value.to_dict("records")
    return []


def pet_rows(at):
    for table in at.dataframe:
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
    assert [(r["Task"], r["Time"], r["Pet"], r["Min"], r["Priority"], r["Repeats"], r["Status"]) for r in rows] == [
        ("Morning walk", "08:00", "Buddy", 30, "🔴 High", "daily", "⏳ Pending")
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
    assert [(r["Task"], r["Status"]) for r in rows] == [("Morning walk", "✅ Done"), ("Morning walk", "⏳ Pending")]
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


# --- Hardening: completion, delete, failures, bad files and two windows ---------------------------


def warnings_text(at):
    return " | ".join(w.value for w in at.warning)


def tick_and_delete(at):
    next(c for c in at.checkbox if c.label == "I want to delete all pets and tasks").check()
    at.run()
    click(at, "Delete all saved data")


def test_completing_a_one_off_task_is_saved(data_file):
    at = start()
    add_pet(at, "Buddy")
    add_task(at, "Buddy", "Vet visit", repeats="once")
    click(at, "Mark complete")

    again = start()
    assert [(r["Task"], r["Status"]) for r in task_rows(again)] == [("Vet visit", "✅ Done")]


def test_several_saves_in_one_session_never_trigger_the_other_window_warning(data_file):
    at = start()
    add_pet(at, "Buddy")
    add_task(at, "Buddy", "Walk", time(8, 0))
    add_task(at, "Buddy", "Feed", time(9, 0), 10)
    widget(at, "text_input", "Owner name").set_value("Sam")
    at.run()
    assert not at.exception and "another window" not in warnings_text(at)
    assert [t["description"] for t in json.loads(data_file.read_text(encoding="utf-8"))["owner"]["pets"][0]["tasks"]] == ["Walk", "Feed"]


def test_delete_puts_the_name_and_time_budget_back_to_their_defaults(data_file):
    at = start()
    widget(at, "text_input", "Owner name").set_value("Sam")
    widget(at, "number_input", "Minutes available today").set_value(90)
    at.run()
    add_pet(at, "Buddy")
    tick_and_delete(at)

    assert widget(at, "text_input", "Owner name").value == "Jordan"
    assert widget(at, "number_input", "Minutes available today").value == 480
    assert not data_file.exists()  # an untouched fresh owner does not recreate the file
    assert widget(start(), "text_input", "Owner name").value == "Jordan"


def test_deleting_when_there_is_no_file_does_not_crash(data_file):
    at = start()
    tick_and_delete(at)
    assert not at.exception and not data_file.exists()


def test_deleting_keeps_the_backup_of_an_unreadable_file(data_file):
    data_file.write_text("{broken", encoding="utf-8")
    at = start()
    assert "Could not load" in warnings_text(at)
    tick_and_delete(at)
    assert not at.exception
    assert data_file.with_name("data.json.corrupt").read_text(encoding="utf-8") == "{broken"
    assert "Could not load" not in warnings_text(at)  # the notice goes away with the reset


def test_the_notice_says_where_the_unreadable_file_was_kept(data_file):
    data_file.write_text("nope", encoding="utf-8")
    assert "It was kept as data.json.corrupt." in warnings_text(start())


def test_a_second_unreadable_file_does_not_overwrite_the_first_backup(data_file):
    data_file.write_text("first bad file", encoding="utf-8")
    start()
    data_file.write_text("second bad file", encoding="utf-8")
    at = start()
    assert data_file.with_name("data.json.corrupt").read_text(encoding="utf-8") == "first bad file"
    assert data_file.with_name("data.json.corrupt2").read_text(encoding="utf-8") == "second bad file"
    assert "data.json.corrupt2" in warnings_text(at)


def test_when_the_unreadable_file_cannot_be_moved_nothing_is_ever_written_over_it(data_file, monkeypatch):
    data_file.write_text("{broken", encoding="utf-8")

    real_replace = os.replace

    def locked(src, dst):
        if Path(src) == data_file:  # only moving the unreadable file aside fails; saving (temp file -> data.json) would work
            raise OSError("file is locked")
        real_replace(src, dst)

    monkeypatch.setattr(os, "replace", locked)
    at = start()
    assert not at.exception and "nothing will be saved" in warnings_text(at)
    add_pet(at, "Buddy")
    assert not at.exception
    assert [r["Name"] for r in pet_rows(at)] == ["Buddy"]  # the app still works in memory
    assert data_file.read_text(encoding="utf-8") == "{broken"  # but the unreadable file is untouched
    assert sorted(p.name for p in data_file.parent.iterdir()) == ["data.json"]


def test_a_save_that_fails_shows_a_warning_instead_of_crashing(tmp_path, monkeypatch):
    monkeypatch.setenv("PAWPAL_DATA_FILE", str(tmp_path / "no-such-folder" / "data.json"))
    at = start()
    add_pet(at, "Buddy")
    assert not at.exception
    assert "Could not save to data.json" in warnings_text(at)
    assert [r["Name"] for r in pet_rows(at)] == ["Buddy"]


def test_a_folder_where_the_data_file_should_be_does_not_crash_the_app(data_file):
    data_file.mkdir()
    at = start()
    assert not at.exception and "Could not load" in warnings_text(at)
    assert pet_rows(at) == []


def test_a_valid_file_saved_with_a_utf8_bom_loads_without_complaint(data_file):
    payload = {"version": 1, "owner": {"name": "Sam", "available_minutes": 60, "pets": [
        {"name": "Buddy", "species": "dog", "age": 3, "tasks": []}]}}
    data_file.write_bytes(b"\xef\xbb\xbf" + json.dumps(payload).encode("utf-8"))
    at = start()
    assert not at.exception and "Could not load" not in warnings_text(at)
    assert [r["Name"] for r in pet_rows(at)] == ["Buddy"]
    assert not data_file.with_name("data.json.corrupt").exists()


def saved_pet_names(data_file):
    return [p["name"] for p in json.loads(data_file.read_text(encoding="utf-8"))["owner"]["pets"]]


def two_windows(data_file):
    """Two sessions open on the same empty data; the second one saves a pet first. Returns (stale window, saved file)."""
    stale, other = start(), start()
    add_pet(other, "Rex")
    assert saved_pet_names(data_file) == ["Rex"]
    add_pet(stale, "Mia")  # this window never saw Rex
    return stale


def test_a_stale_window_does_not_silently_erase_another_windows_work(data_file):
    stale = two_windows(data_file)
    assert not stale.exception
    assert "changed by another window or program" in warnings_text(stale)
    assert saved_pet_names(data_file) == ["Rex"]  # Rex survived
    assert [b.label for b in stale.button if "Overwrite" in b.label or "Reload" in b.label] == [
        "Overwrite the file with this window",
        "Reload the saved file (discard this window's changes)",
    ]


def test_the_stale_window_can_reload_what_the_other_window_saved(data_file):
    stale = two_windows(data_file)
    click(stale, "Reload the saved file (discard this window's changes)")
    stale.run()  # the test harness shows the page from before st.rerun() until the next run, so refresh it
    assert [r["Name"] for r in pet_rows(stale)] == ["Rex"]
    assert "another window" not in warnings_text(stale)
    assert saved_pet_names(data_file) == ["Rex"]


def test_the_stale_window_can_choose_to_overwrite_the_file(data_file):
    stale = two_windows(data_file)
    click(stale, "Overwrite the file with this window")
    stale.run()  # refresh the page as above
    assert saved_pet_names(data_file) == ["Mia"]
    assert "another window" not in warnings_text(stale)
    add_pet(stale, "Zoe")  # saving works normally again afterwards
    assert saved_pet_names(data_file) == ["Mia", "Zoe"]


def test_a_window_notices_when_the_file_was_deleted_by_someone_else(data_file):
    at = start()
    add_pet(at, "Buddy")
    data_file.unlink()
    add_pet(at, "Mia")
    assert "changed by another window or program" in warnings_text(at)
    assert not data_file.exists()  # nothing was written until the user chooses
