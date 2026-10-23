"""The task list's "Order by" choice in the Streamlit app (driven with Streamlit's test harness)."""

from datetime import time
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")


@pytest.fixture(autouse=True)
def isolated_data_file(tmp_path, monkeypatch):
    """Point the app at a throwaway file so these tests never read or write the real data.json."""
    monkeypatch.setenv("PAWPAL_DATA_FILE", str(tmp_path / "data.json"))


def widget(at, kind, label):
    return next(w for w in getattr(at, kind) if w.label == label)


def click(at, label):
    next(b for b in at.button if b.label == label).click()
    at.run()


def add_task(at, description, at_time, priority):
    widget(at, "selectbox", "Pet").set_value("Buddy")
    widget(at, "text_input", "Task description").set_value(description)
    widget(at, "time_input", "Time").set_value(at_time)
    widget(at, "selectbox", "Priority").set_value(priority)
    click(at, "Add task")


def task_names(at):
    for table in at.dataframe:
        if "Repeats" in table.value.columns:
            return list(table.value["Task"])
    return []


@pytest.fixture
def app_with_tasks():
    at = AppTest.from_file(APP, default_timeout=30).run()
    widget(at, "text_input", "Pet name").set_value("Buddy")
    click(at, "Add pet")
    add_task(at, "Late high", time(20, 0), "high")
    add_task(at, "Early low", time(7, 0), "low")
    add_task(at, "Noon medium", time(12, 0), "medium")
    add_task(at, "Early high", time(6, 0), "high")
    return at


def test_the_list_is_in_time_order_by_default(app_with_tasks):
    assert widget(app_with_tasks, "radio", "Order by").value == "Time"
    assert task_names(app_with_tasks) == ["Early high", "Early low", "Noon medium", "Late high"]


def test_priority_first_lists_high_then_medium_then_low_and_time_within_each(app_with_tasks):
    widget(app_with_tasks, "radio", "Order by").set_value("Priority first")
    app_with_tasks.run()
    assert not app_with_tasks.exception
    assert task_names(app_with_tasks) == ["Early high", "Late high", "Noon medium", "Early low"]


def test_switching_back_to_time_restores_the_time_order(app_with_tasks):
    radio = widget(app_with_tasks, "radio", "Order by")
    radio.set_value("Priority first")
    app_with_tasks.run()
    widget(app_with_tasks, "radio", "Order by").set_value("Time")
    app_with_tasks.run()
    assert task_names(app_with_tasks) == ["Early high", "Early low", "Noon medium", "Late high"]


def test_the_filters_still_apply_when_ordered_by_priority(app_with_tasks):
    widget(app_with_tasks, "radio", "Order by").set_value("Priority first")
    widget(app_with_tasks, "radio", "Show tasks").set_value("Pending")
    app_with_tasks.run()
    assert task_names(app_with_tasks) == ["Early high", "Late high", "Noon medium", "Early low"]
    click(app_with_tasks, "Mark complete")  # completes the first task in the time-ordered list: Early high
    widget(app_with_tasks, "radio", "Show tasks").set_value("Completed")
    app_with_tasks.run()
    assert task_names(app_with_tasks) == ["Early high"]
