"""Saving and loading an Owner (pets and tasks) as JSON."""

import copy
import json
from datetime import date, timedelta
from pathlib import Path

import pytest

import pawpal_system
from pawpal_system import DATA_VERSION, Owner, Pet, Scheduler, Task

TODAY = date(2026, 3, 2)


@pytest.fixture
def owner():
    """Two pets with a mix of priorities, frequencies, due dates and a completed task."""
    sam = Owner("Sam", available_minutes=90)
    buddy = Pet("Buddy", "dog", 3)
    mia = Pet("Mia", "cat", 2)  # starts with no tasks of its own below
    sam.add_pet(buddy)
    sam.add_pet(mia)
    buddy.add_task(Task("Morning walk", "08:00", 30, "high", "daily", due_date=TODAY))
    buddy.add_task(Task("Grooming", "16:00", 45, "low", "weekly", due_date=TODAY - timedelta(days=3)))
    done = Task("Medication", "12:30", 5, "high", "once", due_date=TODAY)
    done.mark_complete()
    mia.add_task(done)
    return sam


@pytest.fixture
def path(tmp_path):
    return tmp_path / "data.json"


def payload_of(owner):
    return {"version": DATA_VERSION, "owner": owner.to_dict()}


def write_payload(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


# --- Round trip ---------------------------------------------------------------


def test_save_then_load_restores_an_equal_owner(owner, path):
    owner.save_to_json(path)
    assert Owner.load_from_json(path) == owner


def test_load_restores_every_task_field(owner, path):
    owner.save_to_json(path)
    loaded = Owner.load_from_json(path)
    original = {t.description: t for t in owner.get_all_tasks()}
    for task in loaded.get_all_tasks():
        twin = original[task.description]
        assert (task.time, task.duration, task.priority, task.frequency, task.completed, task.due_date, task.pet_name) == (
            twin.time, twin.duration, twin.priority, twin.frequency, twin.completed, twin.due_date, twin.pet_name
        )


def test_load_restores_the_owner_details(owner, path):
    owner.save_to_json(path)
    loaded = Owner.load_from_json(path)
    assert (loaded.name, loaded.available_minutes) == ("Sam", 90)
    assert [(p.name, p.species, p.age) for p in loaded.pets] == [("Buddy", "dog", 3), ("Mia", "cat", 2)]


def test_load_keeps_pets_and_tasks_in_their_original_order(owner, path):
    owner.save_to_json(path)
    loaded = Owner.load_from_json(path)
    assert [t.description for t in loaded.get_all_tasks()] == [t.description for t in owner.get_all_tasks()]


def test_loaded_tasks_know_which_pet_they_belong_to(owner, path):
    owner.save_to_json(path)
    loaded = Owner.load_from_json(path)
    assert {p.name: [t.pet_name for t in p.tasks] for p in loaded.pets} == {
        "Buddy": ["Buddy", "Buddy"],
        "Mia": ["Mia"],
    }


def test_an_owner_with_no_pets_round_trips(path):
    empty = Owner("Nobody", available_minutes=0)
    empty.save_to_json(path)
    assert Owner.load_from_json(path) == empty


def test_a_pet_with_no_tasks_round_trips(path):
    sam = Owner("Sam")
    sam.add_pet(Pet("Rex", "other", 0))
    sam.save_to_json(path)
    loaded = Owner.load_from_json(path)
    assert loaded == sam and loaded.pets[0].tasks == []


def test_text_with_accents_and_emoji_survives(path):
    sam = Owner("Zoë")
    pet = Pet("Café ☕", "dog", 1)
    sam.add_pet(pet)
    pet.add_task(Task("Promenade 🐕", "07:15", 20, "medium", "once", due_date=TODAY))
    sam.save_to_json(path)
    loaded = Owner.load_from_json(path)
    assert loaded == sam
    assert "Promenade 🐕" in path.read_text(encoding="utf-8")  # stored readably, not as \u escapes


def test_saving_twice_gives_an_identical_file(owner, path):
    owner.save_to_json(path)
    first = path.read_text(encoding="utf-8")
    Owner.load_from_json(path).save_to_json(path)
    assert path.read_text(encoding="utf-8") == first


# --- File format -----------------------------------------------------------------


def test_saved_file_is_versioned_json_with_iso_dates(owner, path):
    owner.save_to_json(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["version"] == DATA_VERSION
    first_task = data["owner"]["pets"][0]["tasks"][0]
    assert first_task["due_date"] == "2026-03-02"
    assert first_task["completed"] is False


def test_the_pet_name_is_not_stored_on_each_task(owner, path):
    owner.save_to_json(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert all("pet_name" not in t for p in data["owner"]["pets"] for t in p["tasks"])


def test_unknown_extra_keys_in_the_file_are_ignored(owner, path):
    payload = payload_of(owner)
    payload["owner"]["pets"][0]["tasks"][0]["note"] = "added by a newer version"
    payload["extra"] = True
    write_payload(path, payload)
    assert Owner.load_from_json(path) == owner


# --- Missing and unsafe files ------------------------------------------------------


def test_loading_a_missing_file_returns_none(tmp_path):
    assert Owner.load_from_json(tmp_path / "nothing-here.json") is None


def test_save_replaces_an_earlier_file_and_leaves_no_temporary_file(owner, path):
    Owner("Old").save_to_json(path)
    owner.save_to_json(path)
    assert Owner.load_from_json(path) == owner
    assert [p.name for p in path.parent.iterdir()] == ["data.json"]


def test_a_failed_save_keeps_the_old_file_and_cleans_up(owner, path, monkeypatch):
    Owner("Old").save_to_json(path)
    before = path.read_text(encoding="utf-8")

    def boom(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(pawpal_system.os, "replace", boom)
    with pytest.raises(OSError):
        owner.save_to_json(path)
    assert path.read_text(encoding="utf-8") == before
    assert [p.name for p in path.parent.iterdir()] == ["data.json"]


def test_saving_into_a_missing_folder_raises(owner, tmp_path):
    with pytest.raises(OSError):
        owner.save_to_json(tmp_path / "no-such-folder" / "data.json")


@pytest.mark.parametrize(
    "content",
    ["", "{not json", "[1, 2, 3]", "null", '"text"', '{"version": 1, "owner": null}'],
)
def test_unreadable_or_wrong_shaped_files_raise_value_error(path, content):
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError):
        Owner.load_from_json(path)
    assert path.read_text(encoding="utf-8") == content  # a failed load never touches the file


def test_a_file_that_is_not_utf8_raises_value_error(path):
    path.write_bytes(b"\xff\xfe\x00bad")
    with pytest.raises(ValueError):
        Owner.load_from_json(path)


@pytest.mark.parametrize("version", [0, 2, "1", None])
def test_a_different_file_version_is_rejected(owner, path, version):
    payload = payload_of(owner)
    payload["version"] = version
    write_payload(path, payload)
    with pytest.raises(ValueError, match="version"):
        Owner.load_from_json(path)


def test_a_file_without_a_version_is_rejected(owner, path):
    write_payload(path, {"owner": owner.to_dict()})
    with pytest.raises(ValueError):
        Owner.load_from_json(path)


# --- Invalid contents ----------------------------------------------------------------


def corrupt(owner, mutate):
    payload = copy.deepcopy(payload_of(owner))
    mutate(payload["owner"])
    return payload


BAD_TASKS = [
    ("time 9:00", lambda t: t.update(time="9:00")),
    ("time 24:00", lambda t: t.update(time="24:00")),
    ("time not text", lambda t: t.update(time=800)),
    ("duration 0", lambda t: t.update(duration=0)),
    ("duration negative", lambda t: t.update(duration=-5)),
    ("duration text", lambda t: t.update(duration="30")),
    ("duration true", lambda t: t.update(duration=True)),
    ("duration fraction", lambda t: t.update(duration=30.5)),
    ("priority unknown", lambda t: t.update(priority="urgent")),
    ("priority list", lambda t: t.update(priority=["high"])),
    ("frequency unknown", lambda t: t.update(frequency="monthly")),
    ("completed text", lambda t: t.update(completed="yes")),
    ("completed number", lambda t: t.update(completed=1)),
    ("date impossible", lambda t: t.update(due_date="2026-02-30")),
    ("date wrong format", lambda t: t.update(due_date="02/03/2026")),
    ("date number", lambda t: t.update(due_date=20260302)),
    ("description empty", lambda t: t.update(description="  ")),
    ("description number", lambda t: t.update(description=7)),
    ("missing description", lambda t: t.pop("description")),
    ("missing time", lambda t: t.pop("time")),
    ("missing due_date", lambda t: t.pop("due_date")),
    ("missing completed", lambda t: t.pop("completed")),
]


@pytest.mark.parametrize("name, mutate", BAD_TASKS, ids=[n for n, _ in BAD_TASKS])
def test_an_invalid_task_in_the_file_raises_value_error(owner, path, name, mutate):
    write_payload(path, corrupt(owner, lambda o: mutate(o["pets"][0]["tasks"][0])))
    with pytest.raises(ValueError):
        Owner.load_from_json(path)


def test_a_task_that_is_not_an_object_raises_value_error(owner, path):
    write_payload(path, corrupt(owner, lambda o: o["pets"][0]["tasks"].append("walk the dog")))
    with pytest.raises(ValueError):
        Owner.load_from_json(path)


BAD_PETS = [
    ("name empty", lambda p: p.update(name="")),
    ("name number", lambda p: p.update(name=5)),
    ("species number", lambda p: p.update(species=3)),
    ("age negative", lambda p: p.update(age=-1)),
    ("age text", lambda p: p.update(age="3")),
    ("age true", lambda p: p.update(age=True)),
    ("tasks not a list", lambda p: p.update(tasks={"a": 1})),
    ("missing tasks", lambda p: p.pop("tasks")),
    ("missing species", lambda p: p.pop("species")),
]


@pytest.mark.parametrize("name, mutate", BAD_PETS, ids=[n for n, _ in BAD_PETS])
def test_an_invalid_pet_in_the_file_raises_value_error(owner, path, name, mutate):
    write_payload(path, corrupt(owner, lambda o: mutate(o["pets"][0])))
    with pytest.raises(ValueError):
        Owner.load_from_json(path)


BAD_OWNERS = [
    ("minutes negative", lambda o: o.update(available_minutes=-1)),
    ("minutes over a day", lambda o: o.update(available_minutes=1441)),
    ("minutes text", lambda o: o.update(available_minutes="90")),
    ("minutes true", lambda o: o.update(available_minutes=True)),
    ("name number", lambda o: o.update(name=1)),
    ("pets not a list", lambda o: o.update(pets="Buddy")),
    ("missing pets", lambda o: o.pop("pets")),
    ("missing name", lambda o: o.pop("name")),
]


@pytest.mark.parametrize("name, mutate", BAD_OWNERS, ids=[n for n, _ in BAD_OWNERS])
def test_invalid_owner_details_in_the_file_raise_value_error(owner, path, name, mutate):
    write_payload(path, corrupt(owner, mutate))
    with pytest.raises(ValueError):
        Owner.load_from_json(path)


@pytest.mark.parametrize("second_name", ["Buddy", "buddy", "BUDDY"])
def test_two_pets_with_the_same_name_in_the_file_are_rejected(owner, path, second_name):
    def duplicate(o):
        o["pets"][1]["name"] = second_name

    write_payload(path, corrupt(owner, duplicate))
    with pytest.raises(ValueError, match="already has a pet"):
        Owner.load_from_json(path)


def test_boundary_values_are_accepted(path):
    payload = {
        "version": DATA_VERSION,
        "owner": {"name": "", "available_minutes": 1440, "pets": [
            {"name": "P", "species": "", "age": 0, "tasks": [
                {"description": "x", "time": "00:00", "duration": 1, "priority": "low",
                 "frequency": "once", "completed": True, "due_date": "0001-01-01"},
                {"description": "y", "time": "23:59", "duration": 240, "priority": "high",
                 "frequency": "weekly", "completed": False, "due_date": "9999-12-31"},
            ]},
        ]},
    }
    write_payload(path, payload)
    loaded = Owner.load_from_json(path)
    assert loaded.available_minutes == 1440 and len(loaded.get_all_tasks()) == 2


# --- A loaded owner behaves like a fresh one ---------------------------------------------


def test_the_scheduler_gives_the_same_answers_before_and_after_a_reload(owner, path):
    owner.save_to_json(path)
    loaded = Owner.load_from_json(path)
    before, after = Scheduler(owner), Scheduler(loaded)
    assert [str(t) for t in after.sort_by_time()] == [str(t) for t in before.sort_by_time()]
    assert after.detect_conflicts() == before.detect_conflicts()
    assert after.explain_plan(TODAY) == before.explain_plan(TODAY)
    assert after.explain_plan(TODAY, weighted=True) == before.explain_plan(TODAY, weighted=True)


def test_completing_a_recurring_task_after_a_reload_adds_the_next_one_to_the_right_pet(owner, path, monkeypatch):
    class FrozenDate(date):
        @classmethod
        def today(cls):
            return TODAY

    monkeypatch.setattr(pawpal_system, "date", FrozenDate)
    owner.save_to_json(path)
    loaded = Owner.load_from_json(path)
    walk = next(t for t in loaded.get_all_tasks() if t.description == "Morning walk")
    follow_up = Scheduler(loaded).complete_task(walk)
    assert follow_up.due_date == TODAY + timedelta(days=1) and follow_up.pet_name == "Buddy"
    assert follow_up in loaded.pets[0].tasks and follow_up not in loaded.pets[1].tasks


def test_a_completed_task_is_still_completed_after_a_reload_and_cannot_recur_twice(owner, path):
    walk = owner.pets[0].tasks[0]
    Scheduler(owner).complete_task(walk)
    owner.save_to_json(path)
    loaded = Owner.load_from_json(path)
    reloaded_walk = loaded.pets[0].tasks[0]
    assert reloaded_walk.completed is True
    assert Scheduler(loaded).complete_task(reloaded_walk) is None
    assert len(loaded.pets[0].tasks) == 3  # the two originals plus exactly one follow-up


def test_changes_made_after_a_reload_can_be_saved_again(owner, path):
    owner.save_to_json(path)
    loaded = Owner.load_from_json(path)
    loaded.pets[1].add_task(Task("Play", "19:00", 15, "low", "once", due_date=TODAY))
    loaded.save_to_json(path)
    assert [t.description for t in Owner.load_from_json(path).pets[1].tasks] == ["Medication", "Play"]


# --- Hardening: paths, odd files, order, and exact round trips ---------------------------


def test_plain_string_paths_work_as_well_as_path_objects(owner, tmp_path):
    where = str(tmp_path / "plain.json")
    owner.save_to_json(where)
    assert Owner.load_from_json(where) == owner


def test_the_temporary_file_sits_next_to_the_target_so_the_swap_stays_atomic(owner, path, monkeypatch):
    seen = {}
    real_replace = pawpal_system.os.replace

    def spy(src, dst):
        seen["src"], seen["dst"] = Path(src), Path(dst)
        real_replace(src, dst)

    monkeypatch.setattr(pawpal_system.os, "replace", spy)
    owner.save_to_json(path)
    assert seen["dst"] == path and seen["src"] != path and seen["src"].parent == path.parent


def test_a_file_saved_with_a_utf8_bom_still_loads(owner, path):
    path.write_bytes(b"\xef\xbb\xbf" + json.dumps(payload_of(owner)).encode("utf-8"))
    assert Owner.load_from_json(path) == owner


def test_a_folder_where_the_file_should_be_raises_value_error(tmp_path):
    folder = tmp_path / "data.json"
    folder.mkdir()
    with pytest.raises(ValueError):
        Owner.load_from_json(folder)


@pytest.mark.parametrize(
    "content",
    [pytest.param("[" * 100000, id="nested arrays"), pytest.param('{"a":' * 100000, id="nested objects")],
)
def test_absurdly_nested_json_raises_value_error_instead_of_crashing(path, content):
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError):
        Owner.load_from_json(path)


def test_a_file_with_a_version_but_no_owner_raises_value_error(path):
    path.write_text('{"version": 1}', encoding="utf-8")
    with pytest.raises(ValueError):
        Owner.load_from_json(path)


@pytest.mark.parametrize("value", ["", {}, 0, None, False])
def test_an_empty_or_falsy_value_where_a_list_belongs_is_rejected(owner, path, value):
    write_payload(path, corrupt(owner, lambda o: o.update(pets=value)))
    with pytest.raises(ValueError):
        Owner.load_from_json(path)
    write_payload(path, corrupt(owner, lambda o: o["pets"][0].update(tasks=value)))
    with pytest.raises(ValueError):
        Owner.load_from_json(path)


def test_the_original_order_of_pets_and_tasks_survives_even_when_it_is_not_sorted(path):
    sam = Owner("Sam")
    zed, amy = Pet("Zed", "dog", 1), Pet("Amy", "cat", 2)
    sam.add_pet(zed)
    sam.add_pet(amy)
    for pet, time, name in [(zed, "18:00", "Late"), (zed, "07:00", "Early"), (amy, "12:00", "Noon"), (amy, "06:00", "Dawn")]:
        pet.add_task(Task(name, time, 10, "low", "once", due_date=TODAY))
    sam.save_to_json(path)
    loaded = Owner.load_from_json(path)
    assert [p.name for p in loaded.pets] == ["Zed", "Amy"]
    assert [t.description for t in loaded.get_all_tasks()] == ["Late", "Early", "Noon", "Dawn"]


def test_names_keep_their_spaces_and_capitals_exactly(path):
    sam = Owner(" Sam O'Neil ")
    pet = Pet("  Rex the 3rd ", "Border Collie", 1)
    sam.add_pet(pet)
    pet.add_task(Task("  Walk  to the park ", "07:00", 10, "low", "once", due_date=TODAY))
    sam.save_to_json(path)
    loaded = Owner.load_from_json(path)
    assert (loaded.name, loaded.pets[0].name, loaded.pets[0].species) == (" Sam O'Neil ", "  Rex the 3rd ", "Border Collie")
    assert loaded.pets[0].tasks[0].description == "  Walk  to the park "


def test_the_file_is_indented_for_people_and_starts_with_the_version(owner, path):
    owner.save_to_json(path)
    text = path.read_text(encoding="utf-8")
    assert text.startswith('{\n  "version": 1,\n  "owner": {\n    "name": "Sam",')
    assert "\n" + " " * 12 + '"description": "Morning walk",' in text  # tasks sit four levels deep, two spaces each
