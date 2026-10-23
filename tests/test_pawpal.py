from datetime import date, timedelta

import pytest

import pawpal_system
from pawpal_system import Owner, Pet, Scheduler, Task

TODAY = date(2026, 3, 2)  # fixed so plan tests don't depend on the real clock


class _FrozenDate(date):
    @classmethod
    def today(cls):
        return TODAY


@pytest.fixture
def frozen_today(monkeypatch):
    """Make pawpal_system see TODAY as the current date.

    Scheduler.complete_task has no from_date parameter; it passes date.today() to
    Task.next_occurrence, so tests that go through it need today pinned to a fixed date.
    """
    monkeypatch.setattr(pawpal_system, "date", _FrozenDate)


def make_task(description="Walk", time="08:00", duration=30, priority="medium", frequency="once", **kwargs):
    kwargs.setdefault("due_date", TODAY)
    return Task(description, time, duration, priority, frequency, **kwargs)


@pytest.fixture
def household():
    """Owner with two pets and one scheduler; tasks are added by each test."""
    owner = Owner("Sam", available_minutes=90)
    buddy = Pet("Buddy", "dog", 3)
    mia = Pet("Mia", "cat", 2)
    owner.add_pet(buddy)
    owner.add_pet(mia)
    return owner, buddy, mia, Scheduler(owner)


# --- Task -------------------------------------------------------------------


def test_mark_complete_changes_status():
    task = make_task()
    assert task.completed is False
    task.mark_complete()
    assert task.completed is True


@pytest.mark.parametrize(
    "frequency, expected",
    [("daily", TODAY + timedelta(days=1)), ("weekly", TODAY + timedelta(days=7)), ("once", None)],
)
def test_next_occurrence(frequency, expected):
    assert make_task(frequency=frequency).next_occurrence(from_date=TODAY) == expected


@pytest.mark.parametrize(
    "due, expected",
    [
        (date(2026, 1, 31), date(2026, 2, 1)),  # month boundary after a 31-day month
        (date(2026, 4, 30), date(2026, 5, 1)),  # month boundary after a 30-day month
        (date(2026, 12, 31), date(2027, 1, 1)),  # year boundary
    ],
)
def test_next_occurrence_rolls_over_month_and_year(due, expected):
    """A daily task whose anchor is its own due_date (from_date ≤ due_date) rolls to the 1st of the next month."""
    task = make_task(frequency="daily", due_date=due)
    assert task.next_occurrence(from_date=date(2026, 1, 1)) == expected


@pytest.mark.parametrize(
    "bad_time", ["9:00", "24:00", "08:60", "08:5", "0800", "", "ab:cd", "0٨:00", "08:00abc", "08:00 ", "08:00\n"]
)
def test_task_rejects_bad_time(bad_time):
    with pytest.raises(ValueError):
        make_task(time=bad_time)


@pytest.mark.parametrize(
    "field, value",
    [("duration", 0), ("duration", -5), ("priority", "urgent"), ("priority", "High"), ("frequency", "monthly")],
)
def test_task_rejects_invalid_fields(field, value):
    with pytest.raises(ValueError):
        make_task(**{field: value})


# --- Pet --------------------------------------------------------------------


def test_add_task_increases_pet_task_count():
    pet = Pet("Buddy", "dog", 3)
    assert len(pet.tasks) == 0
    pet.add_task(make_task("Walk"))
    pet.add_task(make_task("Feed"))
    assert len(pet.tasks) == 2


def test_add_task_records_pet_name_on_task():
    pet = Pet("Buddy", "dog", 3)
    task = make_task()
    pet.add_task(task)
    assert task.pet_name == "Buddy"


def test_pet_constructed_with_tasks_stamps_names_and_copies_list():
    tasks = [make_task("Feed")]
    pet = Pet("Rex", "dog", 2, tasks)
    assert tasks[0].pet_name == "Rex"
    assert pet.tasks is not tasks


def test_pets_do_not_share_default_task_lists():
    a, b = Pet("A", "dog", 1), Pet("B", "cat", 1)
    a.add_task(make_task())
    assert b.tasks == []


# --- Owner ------------------------------------------------------------------


def test_get_all_tasks_flattens_every_pet(household):
    owner, buddy, mia, _ = household
    buddy.add_task(make_task("Walk"))
    mia.add_task(make_task("Feed"))
    mia.add_task(make_task("Medication"))
    assert {t.description for t in owner.get_all_tasks()} == {"Walk", "Feed", "Medication"}


def test_get_all_tasks_empty_when_no_pets_or_tasks():
    owner = Owner("Sam")
    assert owner.get_all_tasks() == []
    owner.add_pet(Pet("Buddy", "dog", 3))
    assert owner.get_all_tasks() == []


@pytest.mark.parametrize("duplicate", ["Buddy", "buddy", "BUDDY"])
def test_add_pet_rejects_duplicate_name_ignoring_case(household, duplicate):
    owner, *_ = household
    with pytest.raises(ValueError):
        owner.add_pet(Pet(duplicate, "rabbit", 1))
    assert len(owner.pets) == 2


# --- Scheduler: sorting and filtering ----------------------------------------


def test_sort_by_time_orders_tasks_added_out_of_order(household):
    _, buddy, mia, scheduler = household
    buddy.add_task(make_task("Evening", "18:00"))
    mia.add_task(make_task("Morning", "08:00"))
    buddy.add_task(make_task("Noon", "12:30"))
    assert [t.description for t in scheduler.sort_by_time()] == ["Morning", "Noon", "Evening"]


def test_sort_by_time_puts_earlier_dates_first(household):
    _, buddy, _, scheduler = household
    buddy.add_task(make_task("Tomorrow early", "07:00", due_date=TODAY + timedelta(days=1)))
    buddy.add_task(make_task("Today late", "21:00"))
    assert [t.description for t in scheduler.sort_by_time()] == ["Today late", "Tomorrow early"]


def test_scheduler_sees_pets_added_after_it_was_created():
    owner = Owner("Sam")
    scheduler = Scheduler(owner)
    pet = Pet("Late", "cat", 1)
    owner.add_pet(pet)
    pet.add_task(make_task("Feed"))
    assert [t.description for t in scheduler.sort_by_time()] == ["Feed"]


def test_filter_by_pet_name_ignores_case(household):
    _, buddy, mia, scheduler = household
    buddy.add_task(make_task("Walk"))
    mia.add_task(make_task("Feed"))
    assert [t.description for t in scheduler.filter_tasks(pet_name="buddy")] == ["Walk"]
    assert scheduler.filter_tasks(pet_name="Nobody") == []


def test_filter_by_status_and_combined(household):
    _, buddy, mia, scheduler = household
    done = make_task("Done walk")
    done.mark_complete()
    buddy.add_task(done)
    buddy.add_task(make_task("Pending walk"))
    mia.add_task(make_task("Pending feed"))
    assert [t.description for t in scheduler.filter_tasks(status=True)] == ["Done walk"]
    assert {t.description for t in scheduler.filter_tasks(status=False)} == {"Pending walk", "Pending feed"}
    assert [t.description for t in scheduler.filter_tasks(pet_name="Buddy", status=False)] == ["Pending walk"]


def test_filter_with_no_arguments_returns_everything(household):
    _, buddy, mia, scheduler = household
    buddy.add_task(make_task("Walk"))
    mia.add_task(make_task("Feed"))
    assert len(scheduler.filter_tasks()) == 2


# --- Scheduler: conflicts ----------------------------------------------------


def test_detect_conflicts_flags_same_time_across_pets(household):
    _, buddy, mia, scheduler = household
    buddy.add_task(make_task("Walk", "08:00"))
    mia.add_task(make_task("Feed", "08:00"))
    warnings = scheduler.detect_conflicts()
    assert len(warnings) == 1
    assert "08:00" in warnings[0] and "Walk" in warnings[0] and "Feed" in warnings[0]


def test_detect_conflicts_flags_same_time_for_one_pet(household):
    _, buddy, _, scheduler = household
    buddy.add_task(make_task("Walk", "08:00"))
    buddy.add_task(make_task("Brush", "08:00"))
    assert len(scheduler.detect_conflicts()) == 1


def test_detect_conflicts_empty_when_times_differ(household):
    _, buddy, mia, scheduler = household
    buddy.add_task(make_task("Walk", "08:00"))
    mia.add_task(make_task("Feed", "08:30"))
    assert scheduler.detect_conflicts() == []


def test_detect_conflicts_ignores_completed_tasks_and_other_dates(household):
    _, buddy, mia, scheduler = household
    done = make_task("Done", "08:00")
    done.mark_complete()
    buddy.add_task(done)
    mia.add_task(make_task("Pending", "08:00"))
    buddy.add_task(make_task("Tomorrow", "08:00", due_date=TODAY + timedelta(days=1)))
    assert scheduler.detect_conflicts() == []


def test_detect_conflicts_does_not_crash_on_empty_owner():
    assert Scheduler(Owner("Sam")).detect_conflicts() == []


# --- Scheduler: recurring tasks ----------------------------------------------


@pytest.mark.parametrize("frequency, days", [("daily", 1), ("weekly", 7)])
def test_completing_recurring_task_creates_next_occurrence(household, frozen_today, frequency, days):
    _, buddy, _, scheduler = household
    task = make_task("Walk", frequency=frequency)
    buddy.add_task(task)

    follow_up = scheduler.complete_task(task)

    assert task.completed is True
    assert follow_up.completed is False
    assert follow_up.due_date == TODAY + timedelta(days=days)
    assert follow_up.pet_name == "Buddy"
    assert follow_up in buddy.tasks and len(buddy.tasks) == 2
    assert (follow_up.description, follow_up.time, follow_up.duration) == ("Walk", "08:00", 30)


def test_completing_one_off_task_creates_nothing(household):
    _, buddy, _, scheduler = household
    task = make_task("Vet visit", frequency="once")
    buddy.add_task(task)
    assert scheduler.complete_task(task) is None
    assert task.completed is True
    assert len(buddy.tasks) == 1


def test_completing_a_task_twice_does_not_duplicate_it(household):
    _, buddy, _, scheduler = household
    task = make_task(frequency="daily")
    buddy.add_task(task)
    scheduler.complete_task(task)
    assert scheduler.complete_task(task) is None
    assert len(buddy.tasks) == 2


def test_completing_recurring_task_with_unknown_pet_raises_and_leaves_it_pending(household):
    _, _, _, scheduler = household
    orphan = make_task(frequency="daily", pet_name="Ghost")
    with pytest.raises(ValueError):
        scheduler.complete_task(orphan)
    assert orphan.completed is False


# --- Scheduler: daily plan ---------------------------------------------------


def test_plan_lists_tasks_chronologically_across_pets(household):
    _, buddy, mia, scheduler = household
    buddy.add_task(make_task("Evening", "18:00", 10))
    mia.add_task(make_task("Morning", "08:00", 10))
    assert [t.description for t in scheduler.generate_plan(TODAY)] == ["Morning", "Evening"]


def test_plan_drops_low_priority_task_when_time_is_short(household):
    owner, buddy, mia, scheduler = household
    owner.available_minutes = 60
    buddy.add_task(make_task("Grooming", "09:00", 45, priority="low"))
    mia.add_task(make_task("Medication", "12:00", 30, priority="high"))
    mia.add_task(make_task("Walk", "08:00", 30, priority="medium"))
    plan = scheduler.generate_plan(TODAY)
    assert [t.description for t in plan] == ["Walk", "Medication"]
    assert sum(t.duration for t in plan) <= owner.available_minutes


def test_plan_prefers_high_priority_over_earlier_time(household):
    owner, buddy, _, scheduler = household
    owner.available_minutes = 30
    buddy.add_task(make_task("Early low", "06:00", 30, priority="low"))
    buddy.add_task(make_task("Late high", "20:00", 30, priority="high"))
    assert [t.description for t in scheduler.generate_plan(TODAY)] == ["Late high"]


def test_plan_skips_a_task_that_does_not_fit_but_keeps_smaller_ones(household):
    owner, buddy, _, scheduler = household
    owner.available_minutes = 40
    buddy.add_task(make_task("Big", "08:00", 60, priority="high"))
    buddy.add_task(make_task("Small", "09:00", 10, priority="low"))
    assert [t.description for t in scheduler.generate_plan(TODAY)] == ["Small"]


def test_plan_can_use_exactly_the_whole_budget(household):
    owner, buddy, _, scheduler = household
    owner.available_minutes = 60
    buddy.add_task(make_task("A", "08:00", 30))
    buddy.add_task(make_task("B", "09:00", 30))
    assert len(scheduler.generate_plan(TODAY)) == 2


def test_plan_is_empty_with_zero_minutes_or_no_tasks(household):
    owner, buddy, _, scheduler = household
    assert scheduler.generate_plan(TODAY) == []
    buddy.add_task(make_task())
    owner.available_minutes = 0
    assert scheduler.generate_plan(TODAY) == []


def test_plan_excludes_completed_and_future_tasks_but_includes_overdue(household):
    _, buddy, _, scheduler = household
    done = make_task("Done")
    done.mark_complete()
    buddy.add_task(done)
    buddy.add_task(make_task("Future", due_date=TODAY + timedelta(days=1)))
    buddy.add_task(make_task("Overdue", due_date=TODAY - timedelta(days=2)))
    buddy.add_task(make_task("Today"))
    assert {t.description for t in scheduler.generate_plan(TODAY)} == {"Overdue", "Today"}


def test_plan_shows_overdue_before_today_at_same_priority(household):
    _, buddy, _, scheduler = household
    buddy.add_task(make_task("Today early", "06:00"))
    buddy.add_task(make_task("Overdue late", "22:00", due_date=TODAY - timedelta(days=1)))
    assert [t.description for t in scheduler.generate_plan(TODAY)] == ["Overdue late", "Today early"]


def test_plan_after_completing_recurring_task_moves_it_to_tomorrow(household, frozen_today):
    _, buddy, _, scheduler = household
    task = make_task("Walk", frequency="daily")
    buddy.add_task(task)
    scheduler.complete_task(task)
    assert scheduler.generate_plan(TODAY) == []
    assert [t.due_date for t in scheduler.generate_plan(TODAY + timedelta(days=1))] == [TODAY + timedelta(days=1)]


def test_explain_plan_reports_usage_and_left_out_tasks(household):
    owner, buddy, _, scheduler = household
    owner.available_minutes = 40
    buddy.add_task(make_task("Walk", "08:00", 30, priority="high"))
    buddy.add_task(make_task("Grooming", "09:00", 45, priority="low"))
    text = scheduler.explain_plan(TODAY)
    assert "30 of 40" in text
    assert "Walk" in text
    assert "Left out" in text and "Grooming" in text


def test_explain_plan_omits_left_out_section_when_everything_fits(household):
    _, buddy, _, scheduler = household
    buddy.add_task(make_task("Walk", duration=10))
    assert "Left out" not in scheduler.explain_plan(TODAY)


def test_explain_plan_marks_overdue_tasks(household):
    _, buddy, _, scheduler = household
    buddy.add_task(make_task("Old", due_date=TODAY - timedelta(days=3)))
    assert "overdue since 2026-02-27" in scheduler.explain_plan(TODAY)


# --- Boundaries, defaults and ordering (gaps found by mutation testing) -------


@pytest.mark.parametrize("time", ["00:00", "23:59"])
def test_extreme_valid_times_are_accepted(time):
    assert make_task(time=time).time == time


def test_one_minute_duration_is_valid():
    assert make_task(duration=1).duration == 1


def test_new_task_defaults():
    task = Task("Walk", "08:00", 30, "medium", "once")
    assert task.pet_name == ""
    assert task.completed is False
    assert task.due_date == date.today()


def test_next_occurrence_is_repeatable_and_leaves_due_date_unchanged():
    task = make_task(frequency="daily")
    assert task.next_occurrence(from_date=TODAY) == TODAY + timedelta(days=1)
    assert task.due_date == TODAY
    assert task.next_occurrence(from_date=TODAY) == TODAY + timedelta(days=1)


def test_task_str_shows_status_time_description_pet_duration_and_priority():
    task = make_task("Walk", "08:00", 30, "high", pet_name="Buddy")
    assert str(task) == "[ ] 08:00 Walk (Buddy) - 30 min, high"
    task.mark_complete()
    assert str(task).startswith("[x] ")


def test_task_str_omits_pet_when_unassigned():
    assert str(make_task("Feed", "07:15", 5, "low")) == "[ ] 07:15 Feed - 5 min, low"


def test_owner_default_time_budget_is_a_full_day():
    assert Owner("Sam").available_minutes == 480


def test_pets_tasks_and_owner_keep_insertion_order():
    owner = Owner("Sam")
    a, b = Pet("A", "dog", 1), Pet("B", "cat", 1)
    owner.add_pet(a)
    owner.add_pet(b)
    a.add_task(make_task("a1"))
    a.add_task(make_task("a2"))
    b.add_task(make_task("b1"))
    assert [p.name for p in owner.pets] == ["A", "B"]
    assert [t.description for t in a.tasks] == ["a1", "a2"]
    assert [t.description for t in owner.get_all_tasks()] == ["a1", "a2", "b1"]


def test_sort_by_time_includes_completed_tasks(household):
    _, buddy, _, scheduler = household
    done = make_task("Done", "07:00")
    done.mark_complete()
    buddy.add_task(done)
    buddy.add_task(make_task("Pending", "09:00"))
    assert [t.description for t in scheduler.sort_by_time()] == ["Done", "Pending"]


def test_sort_by_time_keeps_insertion_order_for_ties(household):
    _, buddy, mia, scheduler = household
    buddy.add_task(make_task("Zed", "08:00"))
    mia.add_task(make_task("Apple", "08:00"))
    assert [t.description for t in scheduler.sort_by_time()] == ["Zed", "Apple"]


def test_filter_pet_name_must_match_the_whole_name(household):
    _, buddy, _, scheduler = household
    buddy.add_task(make_task("Walk"))
    assert scheduler.filter_tasks(pet_name="Bud") == []
    assert scheduler.filter_tasks(pet_name="ddy") == []
    assert scheduler.filter_tasks(pet_name="") == []


def test_filter_default_returns_completed_and_pending(household):
    _, buddy, _, scheduler = household
    done = make_task("Done")
    done.mark_complete()
    buddy.add_task(done)
    buddy.add_task(make_task("Pending"))
    assert {t.description for t in scheduler.filter_tasks()} == {"Done", "Pending"}


def test_detect_conflicts_message_and_order(household):
    _, buddy, mia, scheduler = household
    later = TODAY + timedelta(days=1)
    buddy.add_task(make_task("Late A", "08:00", due_date=later))  # inserted first on purpose
    mia.add_task(make_task("Late B", "08:00", due_date=later))
    buddy.add_task(make_task("Early A", "09:00"))
    mia.add_task(make_task("Early B", "09:00"))
    assert scheduler.detect_conflicts() == [
        "Conflict on 2026-03-02 at 09:00: Early A (Buddy), Early B (Mia)",
        "Conflict on 2026-03-03 at 08:00: Late A (Buddy), Late B (Mia)",
    ]


@pytest.mark.parametrize("frequency, days", [("daily", 1), ("weekly", 7)])
def test_next_occurrence_early_completion(frequency, days):
    """Completed before it was due: the next one counts from the original due date, not from today."""
    due = TODAY + timedelta(days=8)
    task = make_task(frequency=frequency, due_date=due)
    assert task.next_occurrence(from_date=TODAY) == due + timedelta(days=days)


@pytest.mark.parametrize("frequency, days", [("daily", 1), ("weekly", 7)])
def test_next_occurrence_on_time(frequency, days):
    """Completed on its due date: due date and completion date agree."""
    task = make_task(frequency=frequency, due_date=TODAY)
    assert task.next_occurrence(from_date=TODAY) == TODAY + timedelta(days=days)


@pytest.mark.parametrize("frequency, days", [("daily", 1), ("weekly", 7)])
def test_next_occurrence_late_completion(frequency, days):
    """Completed after it was due: the next one counts from today, not from the missed due date."""
    due = TODAY - timedelta(days=10)
    task = make_task(frequency=frequency, due_date=due)
    assert task.next_occurrence(from_date=TODAY) == TODAY + timedelta(days=days)


def test_follow_up_goes_to_the_tasks_own_pet(household):
    _, buddy, mia, scheduler = household
    task = make_task("Feed", frequency="daily")
    mia.add_task(task)
    follow_up = scheduler.complete_task(task)
    assert follow_up in mia.tasks and len(mia.tasks) == 2
    assert buddy.tasks == []
    assert follow_up.pet_name == "Mia"


def test_pet_lookup_when_completing_is_an_exact_name_match(household):
    _, _, _, scheduler = household
    stray = make_task(frequency="daily", pet_name="buddy")  # the pet is "Buddy"
    with pytest.raises(ValueError):
        scheduler.complete_task(stray)
    assert stray.completed is False


def test_completing_a_one_off_task_with_no_pet_still_works():
    task = make_task(frequency="once", pet_name="Ghost")
    assert Scheduler(Owner("Sam")).complete_task(task) is None
    assert task.completed is True


def test_plan_ranks_medium_above_low(household):
    owner, buddy, _, scheduler = household
    owner.available_minutes = 30
    buddy.add_task(make_task("Low", "08:00", 30, priority="low"))
    buddy.add_task(make_task("Medium", "09:00", 30, priority="medium"))
    assert [t.description for t in scheduler.generate_plan(TODAY)] == ["Medium"]


def test_plan_prefers_overdue_over_earlier_time_when_budget_is_tight(household):
    owner, buddy, _, scheduler = household
    owner.available_minutes = 30
    buddy.add_task(make_task("Today early", "06:00", 30))
    buddy.add_task(make_task("Overdue late", "22:00", 30, due_date=TODAY - timedelta(days=1)))
    assert [t.description for t in scheduler.generate_plan(TODAY)] == ["Overdue late"]


def test_plan_prefers_earlier_time_at_same_priority_and_date_when_budget_is_tight(household):
    owner, buddy, _, scheduler = household
    owner.available_minutes = 30
    buddy.add_task(make_task("Late", "20:00", 30))
    buddy.add_task(make_task("Early", "08:00", 30))
    assert [t.description for t in scheduler.generate_plan(TODAY)] == ["Early"]


def test_explain_plan_does_not_mark_todays_tasks_overdue(household):
    _, buddy, _, scheduler = household
    buddy.add_task(make_task("Walk"))
    assert "overdue since" not in scheduler.explain_plan(TODAY)


def test_explain_plan_header_counts_planned_tasks_not_skipped_ones(household):
    owner, buddy, _, scheduler = household
    owner.available_minutes = 40
    buddy.add_task(make_task("Walk", "08:00", 30, priority="high"))
    buddy.add_task(make_task("G1", "09:00", 45, priority="low"))
    buddy.add_task(make_task("G2", "10:00", 45, priority="low"))
    assert "1 task(s)" in scheduler.explain_plan(TODAY)


def test_explain_plan_lists_left_out_tasks_in_priority_order(household):
    owner, buddy, _, scheduler = household
    owner.available_minutes = 10
    buddy.add_task(make_task("G1", "09:00", 45, priority="low"))
    buddy.add_task(make_task("G2", "10:00", 45, priority="low"))
    text = scheduler.explain_plan(TODAY)
    assert text.index("G1") < text.index("G2")


# --- Second round of mutation-testing gaps ------------------------------------


@pytest.mark.parametrize("bad", ["", "y", "once daily", "Daily", "WEEKLY"])
def test_frequency_must_be_an_exact_known_value(bad):
    with pytest.raises(ValueError):
        make_task(frequency=bad)


@pytest.mark.parametrize("bad", ["", "m", "igh", "high medium"])
def test_priority_must_be_an_exact_known_value(bad):
    with pytest.raises(ValueError):
        make_task(priority=bad)


def test_validation_errors_name_the_offending_field():
    with pytest.raises(ValueError, match="time"):
        make_task(time="9:00")
    with pytest.raises(ValueError, match="duration.*-5"):
        make_task(duration=-5)


def test_mark_complete_is_idempotent_and_leaves_due_date_alone():
    task = make_task(frequency="daily")
    task.mark_complete()
    task.mark_complete()
    assert task.completed is True
    assert task.due_date == TODAY


def test_constructor_keeps_completed_flag():
    assert make_task(completed=True).completed is True


def test_add_task_restamps_and_keeps_name_exactly_as_given():
    task = make_task(pet_name="Old")
    pet = Pet("max", "dog", 3)
    pet.add_task(task)
    assert task.pet_name == "max"


def test_add_task_keeps_two_equal_looking_tasks():
    pet = Pet("Buddy", "dog", 3)
    pet.add_task(make_task("Walk"))
    pet.add_task(make_task("Walk"))
    assert len(pet.tasks) == 2


def test_pet_constructed_with_several_tasks_stamps_all_of_them():
    tasks = [make_task("A"), make_task("B", "09:00")]
    Pet("Rex", "dog", 2, tasks)
    assert [t.pet_name for t in tasks] == ["Rex", "Rex"]


def test_add_pet_checks_every_existing_pet_for_a_duplicate(household):
    owner, *_ = household
    with pytest.raises(ValueError):
        owner.add_pet(Pet("mia", "cat", 1))  # the second pet, not the first
    assert len(owner.pets) == 2


def test_add_pet_rejects_the_same_pet_object_twice(household):
    owner, buddy, *_ = household
    with pytest.raises(ValueError):
        owner.add_pet(buddy)


@pytest.mark.parametrize("name", ["Bud", "Buddy Jr", "Bella"])
def test_add_pet_accepts_similar_but_different_names(household, name):
    owner, *_ = household
    owner.add_pet(Pet(name, "dog", 1))
    assert len(owner.pets) == 3


def test_get_all_tasks_includes_tasks_appended_without_a_pet_name():
    owner = Owner("Sam")
    pet = Pet("Buddy", "dog", 3)
    owner.add_pet(pet)
    task = make_task()
    pet.tasks.append(task)
    assert owner.get_all_tasks() == [task]


def test_sort_orders_by_minutes_within_the_same_hour(household):
    _, buddy, _, scheduler = household
    buddy.add_task(make_task("Half past", "08:30"))
    buddy.add_task(make_task("On the hour", "08:00"))
    assert [t.description for t in scheduler.sort_by_time()] == ["On the hour", "Half past"]


def test_sort_ties_keep_insertion_order_regardless_of_duration(household):
    _, buddy, mia, scheduler = household
    buddy.add_task(make_task("Long", "08:00", 60))
    mia.add_task(make_task("Short", "08:00", 5))
    assert [t.description for t in scheduler.sort_by_time()] == ["Long", "Short"]


def test_sort_by_time_does_not_reorder_the_pets_own_lists(household):
    _, buddy, _, scheduler = household
    buddy.add_task(make_task("Late", "20:00"))
    buddy.add_task(make_task("Early", "06:00"))
    scheduler.sort_by_time()
    assert [t.description for t in buddy.tasks] == ["Late", "Early"]


def test_filter_pet_name_is_not_trimmed(household):
    _, buddy, _, scheduler = household
    buddy.add_task(make_task("Walk"))
    assert scheduler.filter_tasks(pet_name=" Buddy ") == []


def test_filter_keeps_insertion_order(household):
    _, buddy, _, scheduler = household
    buddy.add_task(make_task("Late", "20:00"))
    buddy.add_task(make_task("Early", "06:00"))
    assert [t.description for t in scheduler.filter_tasks(pet_name="Buddy")] == ["Late", "Early"]


def test_detect_conflicts_orders_same_day_warnings_by_time_ascending(household):
    _, buddy, mia, scheduler = household
    buddy.add_task(make_task("Evening A", "18:00"))
    mia.add_task(make_task("Evening B", "18:00"))
    buddy.add_task(make_task("Morning A", "07:00"))
    mia.add_task(make_task("Morning B", "07:00"))
    first, second = scheduler.detect_conflicts()
    assert "07:00" in first and "18:00" in second


def test_detect_conflict_lists_every_task_in_owner_order(household):
    _, buddy, mia, scheduler = household
    buddy.add_task(make_task("Zulu", "08:00"))
    mia.add_task(make_task("Alpha", "08:00"))
    buddy.add_task(make_task("Mike", "08:00"))
    (warning,) = scheduler.detect_conflicts()
    assert warning == "Conflict on 2026-03-02 at 08:00: Zulu (Buddy), Mike (Buddy), Alpha (Mia)"


def test_detect_conflicts_flags_identical_descriptions_and_overdue_tasks(household):
    _, buddy, mia, scheduler = household
    past = date(2020, 1, 1)
    buddy.add_task(make_task("Feed", "08:00", due_date=past))
    mia.add_task(make_task("Feed", "08:00", due_date=past))
    assert len(scheduler.detect_conflicts()) == 1


def test_completing_an_already_completed_task_is_a_no_op_even_without_its_pet(household):
    _, _, _, scheduler = household
    task = make_task(frequency="daily", pet_name="Ghost")
    task.mark_complete()
    assert scheduler.complete_task(task) is None


def test_follow_up_keeps_frequency_priority_and_goes_last(household):
    _, buddy, _, scheduler = household
    task = make_task("Meds", frequency="weekly", priority="high")
    buddy.add_task(task)
    buddy.add_task(make_task("Other"))
    follow_up = scheduler.complete_task(task)
    assert (follow_up.frequency, follow_up.priority) == ("weekly", "high")
    assert buddy.tasks[-1] is follow_up


def test_plan_ranks_high_above_medium(household):
    owner, buddy, _, scheduler = household
    owner.available_minutes = 30
    buddy.add_task(make_task("Medium", "08:00", 30, priority="medium"))
    buddy.add_task(make_task("High", "09:00", 30, priority="high"))
    assert [t.description for t in scheduler.generate_plan(TODAY)] == ["High"]


def test_explain_plan_lists_tasks_chronologically_not_by_priority(household):
    _, buddy, _, scheduler = household
    buddy.add_task(make_task("Alpha", "08:00", 10, priority="low"))
    buddy.add_task(make_task("Bravo", "09:00", 10, priority="high"))
    text = scheduler.explain_plan(TODAY)
    assert text.index("Alpha") < text.index("Bravo")


def test_explain_plan_left_out_tasks_follow_priority_not_time(household):
    owner, buddy, _, scheduler = household
    owner.available_minutes = 5
    buddy.add_task(make_task("Early low", "07:00", 30, priority="low"))
    buddy.add_task(make_task("Late high", "21:00", 30, priority="high"))
    text = scheduler.explain_plan(TODAY)
    assert text.index("Late high") < text.index("Early low")


def test_explain_plan_flags_overdue_tasks_that_were_left_out(household):
    owner, buddy, _, scheduler = household
    owner.available_minutes = 5
    buddy.add_task(make_task("Old", "08:00", 30, due_date=TODAY - timedelta(days=3)))
    left_out = scheduler.explain_plan(TODAY).split("Left out")[1]
    assert "overdue since 2026-02-27" in left_out


def test_explain_plan_header_uses_the_requested_day(household):
    _, buddy, _, scheduler = household
    other_day = date(2031, 7, 4)
    buddy.add_task(make_task("Walk", due_date=other_day))
    text = scheduler.explain_plan(other_day)
    assert "Plan for 2031-07-04" in text and "Walk" in text


def test_plan_and_explanation_default_to_the_real_today(household):
    _, buddy, _, scheduler = household
    buddy.add_task(make_task("Now", due_date=date.today()))
    buddy.add_task(make_task("Tomorrow", due_date=date.today() + timedelta(days=1)))
    assert [t.description for t in scheduler.generate_plan()] == ["Now"]
    text = scheduler.explain_plan()
    assert f"Plan for {date.today()}" in text and "Now" in text and "Tomorrow" not in text


# --- Leap day, overlapping durations, existing follow-up ---


@pytest.mark.parametrize(
    "due, expected",
    [
        (date(2028, 2, 28), date(2028, 2, 29)),  # leap year: Feb 29 exists
        (date(2028, 2, 29), date(2028, 3, 1)),
        (date(2027, 2, 28), date(2027, 3, 1)),  # non-leap year: straight to March
    ],
)
def test_next_occurrence_handles_leap_day(due, expected):
    task = make_task(frequency="daily", due_date=due)
    assert task.next_occurrence(from_date=due) == expected


def test_weekly_next_occurrence_lands_on_leap_day():
    task = make_task(frequency="weekly", due_date=date(2028, 2, 22))
    assert task.next_occurrence(from_date=date(2028, 2, 22)) == date(2028, 2, 29)


def test_detect_conflicts_flags_overlapping_durations(household):
    _, buddy, mia, scheduler = household
    buddy.add_task(make_task("Long walk", "09:00", duration=60))
    mia.add_task(make_task("Feed", "09:30", duration=10))
    assert scheduler.detect_conflicts() == [
        "Overlap on 2026-03-02: Long walk (Buddy) 09:00-10:00 runs into Feed (Mia) at 09:30"
    ]


def test_back_to_back_tasks_do_not_overlap(household):
    _, buddy, mia, scheduler = household
    buddy.add_task(make_task("Walk", "09:00", duration=30))
    mia.add_task(make_task("Feed", "09:30", duration=10))
    assert scheduler.detect_conflicts() == []


def test_same_start_time_is_one_conflict_not_also_an_overlap(household):
    _, buddy, mia, scheduler = household
    buddy.add_task(make_task("Walk", "09:00", duration=60))
    mia.add_task(make_task("Feed", "09:00", duration=10))
    assert scheduler.detect_conflicts() == ["Conflict on 2026-03-02 at 09:00: Walk (Buddy), Feed (Mia)"]


def test_one_long_task_overlaps_each_task_it_runs_into(household):
    _, buddy, mia, scheduler = household
    buddy.add_task(make_task("Groom", "09:00", duration=120))
    mia.add_task(make_task("Feed", "09:30", duration=30))
    mia.add_task(make_task("Meds", "10:00", duration=5))
    warnings = scheduler.detect_conflicts()
    assert len(warnings) == 2
    assert "Feed" in warnings[0] and "Meds" in warnings[1]  # Feed and Meds themselves only touch


def test_overlap_ignores_completed_tasks_and_other_dates(household):
    _, buddy, mia, scheduler = household
    done = make_task("Done", "09:00", duration=60)
    done.mark_complete()
    buddy.add_task(done)
    buddy.add_task(make_task("Long", "09:00", duration=120, due_date=TODAY + timedelta(days=1)))
    mia.add_task(make_task("Feed", "09:30"))
    assert scheduler.detect_conflicts() == []


def test_overlap_is_cut_off_at_midnight(household):
    _, buddy, mia, scheduler = household
    buddy.add_task(make_task("Late walk", "23:30", duration=90))
    mia.add_task(make_task("Snack", "23:45", duration=5))
    (warning,) = scheduler.detect_conflicts()
    assert "23:30-24:00" in warning


def test_completing_a_recurring_task_reuses_an_identical_pending_follow_up(household, frozen_today):
    _, buddy, _, scheduler = household
    task = make_task("Walk", frequency="daily")
    existing = make_task("Walk", frequency="daily", due_date=TODAY + timedelta(days=1))
    buddy.add_task(task)
    buddy.add_task(existing)

    follow_up = scheduler.complete_task(task)

    assert follow_up is existing
    assert len(buddy.tasks) == 2
    assert scheduler.detect_conflicts() == []


def test_a_completed_or_different_next_task_does_not_block_the_follow_up(household, frozen_today):
    _, buddy, _, scheduler = household
    task = make_task("Walk", frequency="daily")
    tomorrow = TODAY + timedelta(days=1)
    already_done = make_task("Walk", frequency="daily", due_date=tomorrow)
    already_done.mark_complete()
    other_time = make_task("Walk", "17:00", frequency="daily", due_date=tomorrow)
    for t in (task, already_done, other_time):
        buddy.add_task(t)

    follow_up = scheduler.complete_task(task)

    assert follow_up not in (already_done, other_time)
    assert follow_up.due_date == tomorrow and follow_up.time == "08:00"
    assert len(buddy.tasks) == 4


# --- suggest_free_time ---------------------------------------------------------


def test_suggest_free_time_on_an_empty_day_is_the_earliest_time(household):
    _, _, _, scheduler = household
    assert scheduler.suggest_free_time(30, TODAY) == "00:00"
    assert scheduler.suggest_free_time(30, TODAY, earliest="07:15") == "07:15"


def test_suggest_free_time_skips_past_a_busy_task(household):
    _, buddy, _, scheduler = household
    buddy.add_task(make_task("Walk", "08:00", duration=30))
    assert scheduler.suggest_free_time(20, TODAY, earliest="08:00") == "08:30"
    assert scheduler.suggest_free_time(20, TODAY, earliest="08:10") == "08:30"  # starts inside the task


def test_suggest_free_time_uses_a_gap_that_fits_exactly(household):
    _, buddy, mia, scheduler = household
    buddy.add_task(make_task("A", "08:00", duration=30))  # busy 08:00-08:30
    mia.add_task(make_task("B", "09:00", duration=30))  # busy 09:00-09:30
    assert scheduler.suggest_free_time(30, TODAY, earliest="08:00") == "08:30"  # the 30-minute gap fits exactly
    assert scheduler.suggest_free_time(31, TODAY, earliest="08:00") == "09:30"  # one minute too long, so after B


def test_suggest_free_time_chains_back_to_back_tasks(household):
    _, buddy, mia, scheduler = household
    buddy.add_task(make_task("A", "08:00", duration=30))
    mia.add_task(make_task("B", "08:30", duration=30))
    assert scheduler.suggest_free_time(15, TODAY, earliest="08:00") == "09:00"


def test_suggest_free_time_ignores_completed_tasks_other_dates_and_the_ignored_task(household):
    _, buddy, _, scheduler = household
    done = make_task("Done", "08:00", duration=60)
    done.mark_complete()
    moving = make_task("Moving", "08:00", duration=60)
    for t in (done, moving, make_task("Tomorrow", "08:00", duration=60, due_date=TODAY + timedelta(days=1))):
        buddy.add_task(t)
    assert scheduler.suggest_free_time(30, TODAY, earliest="08:00") == "09:00"  # only `moving` blocks
    assert scheduler.suggest_free_time(30, TODAY, earliest="08:00", ignore=moving) == "08:00"


def test_suggest_free_time_returns_none_when_nothing_fits_before_midnight(household):
    _, buddy, _, scheduler = household
    buddy.add_task(make_task("Late", "23:00", duration=45))  # busy 23:00-23:45
    assert scheduler.suggest_free_time(30, TODAY, earliest="23:00") is None
    assert scheduler.suggest_free_time(15, TODAY, earliest="23:00") == "23:45"
    assert scheduler.suggest_free_time(15, TODAY, earliest="23:50") is None  # 23:50 + 15 runs past midnight


@pytest.mark.parametrize("duration, earliest", [(0, "08:00"), (-5, "08:00"), (30, "8:00"), (30, "25:00")])
def test_suggest_free_time_rejects_bad_input(household, duration, earliest):
    _, _, _, scheduler = household
    with pytest.raises(ValueError):
        scheduler.suggest_free_time(duration, TODAY, earliest=earliest)


def test_suggestion_resolves_the_conflict_it_was_made_for(household):
    _, buddy, mia, scheduler = household
    buddy.add_task(make_task("Walk", "08:00", duration=30))
    clash = make_task("Feed", "08:00", duration=10)
    mia.add_task(clash)
    assert scheduler.detect_conflicts()
    clash.time = scheduler.suggest_free_time(clash.duration, clash.due_date, earliest=clash.time, ignore=clash)
    assert clash.time == "08:30" and scheduler.detect_conflicts() == []


# --- sort_by_time: priority tiebreak and empty inputs ---------------------------


def test_sort_by_time_breaks_same_time_ties_by_priority(household):
    _, buddy, mia, scheduler = household
    buddy.add_task(make_task("Low", "08:00", priority="low"))
    mia.add_task(make_task("High", "08:00", priority="high"))
    buddy.add_task(make_task("Medium", "08:00", priority="medium"))
    assert [t.description for t in scheduler.sort_by_time()] == ["High", "Medium", "Low"]


def test_sort_by_time_priority_never_outranks_an_earlier_time(household):
    _, buddy, _, scheduler = household
    buddy.add_task(make_task("Late but high", "18:00", priority="high"))
    buddy.add_task(make_task("Early but low", "07:00", priority="low"))
    assert [t.description for t in scheduler.sort_by_time()] == ["Early but low", "Late but high"]


def test_sort_by_time_is_empty_with_no_pets_or_no_tasks(household):
    _, _, _, scheduler = household  # two pets, neither has a task
    assert scheduler.sort_by_time() == []
    assert Scheduler(Owner("Sam")).sort_by_time() == []


# --- Weighted prioritization with aging -----------------------------------------


def _names(tasks):
    return [t.description for t in tasks]


@pytest.mark.parametrize(
    "priority, days_overdue, expected",
    [("high", 0, 10), ("medium", 0, 5), ("low", 0, 2), ("low", 3, 5), ("high", 4, 14)],
)
def test_task_score_is_priority_points_plus_one_per_day_overdue(household, priority, days_overdue, expected):
    _, _, _, scheduler = household
    task = make_task(priority=priority, due_date=TODAY - timedelta(days=days_overdue))
    assert scheduler.task_score(task, TODAY) == expected


def test_task_score_gives_no_bonus_or_penalty_for_a_future_task(household):
    _, _, _, scheduler = household
    task = make_task(priority="medium", due_date=TODAY + timedelta(days=5))
    assert scheduler.task_score(task, TODAY) == 5


def test_a_long_overdue_low_task_outranks_a_medium_task_due_today_when_weighted(household):
    owner, buddy, _, scheduler = household
    owner.available_minutes = 30  # room for exactly one of the two
    buddy.add_task(make_task("Medium today", "08:00", priority="medium"))
    buddy.add_task(make_task("Low, 5 days late", "09:00", priority="low", due_date=TODAY - timedelta(days=5)))
    assert _names(scheduler.generate_plan(TODAY)) == ["Medium today"]  # strict priority: the default
    assert _names(scheduler.generate_plan(TODAY, weighted=True)) == ["Low, 5 days late"]  # 2 + 5 beats 5


def test_aging_has_to_catch_up_before_a_low_task_beats_a_high_one(household):
    owner, buddy, _, scheduler = household
    owner.available_minutes = 30
    buddy.add_task(make_task("High today", "08:00", priority="high"))
    buddy.add_task(make_task("Low, 7 days late", "09:00", priority="low", due_date=TODAY - timedelta(days=7)))
    assert _names(scheduler.generate_plan(TODAY, weighted=True)) == ["High today"]  # 9 < 10


def test_a_score_tie_goes_to_the_older_due_date(household):
    owner, buddy, _, scheduler = household
    owner.available_minutes = 30
    buddy.add_task(make_task("High today", "08:00", priority="high"))
    buddy.add_task(make_task("Low, 8 days late", "09:00", priority="low", due_date=TODAY - timedelta(days=8)))
    assert _names(scheduler.generate_plan(TODAY, weighted=True)) == ["Low, 8 days late"]  # 10 ties 10; older wins


def test_weighted_plan_matches_strict_plan_when_nothing_is_overdue(household):
    owner, buddy, mia, scheduler = household
    owner.available_minutes = 60
    buddy.add_task(make_task("A", "10:00", priority="low"))
    buddy.add_task(make_task("B", "09:00", priority="high"))
    mia.add_task(make_task("C", "11:00", priority="medium"))
    mia.add_task(make_task("D", "08:00", priority="medium"))
    assert _names(scheduler.generate_plan(TODAY, weighted=True)) == _names(scheduler.generate_plan(TODAY))


@pytest.mark.parametrize("budget", [0, 29, 30, 59, 60, 95, 300])
def test_weighted_plan_never_exceeds_the_time_budget(household, budget):
    owner, buddy, mia, scheduler = household
    owner.available_minutes = budget
    for i, (pet, prio, late) in enumerate([(buddy, "high", 0), (buddy, "low", 6), (mia, "medium", 2), (mia, "low", 0)]):
        pet.add_task(make_task(f"T{i}", f"{8 + i}:00".zfill(5), duration=30, priority=prio, due_date=TODAY - timedelta(days=late)))
    plan = scheduler.generate_plan(TODAY, weighted=True)
    assert sum(t.duration for t in plan) <= budget


def test_weighted_plan_still_skips_completed_and_future_tasks(household):
    _, buddy, _, scheduler = household
    done = make_task("Done", "08:00", priority="high", due_date=TODAY - timedelta(days=9))
    done.mark_complete()
    buddy.add_task(done)
    buddy.add_task(make_task("Future", "09:00", priority="high", due_date=TODAY + timedelta(days=1)))
    buddy.add_task(make_task("Today", "10:00"))
    assert _names(scheduler.generate_plan(TODAY, weighted=True)) == ["Today"]


def test_weighted_plan_is_listed_chronologically_not_by_score(household):
    _, buddy, _, scheduler = household
    buddy.add_task(make_task("Late high", "18:00", priority="high"))
    buddy.add_task(make_task("Early low", "07:00", priority="low"))
    assert _names(scheduler.generate_plan(TODAY, weighted=True)) == ["Early low", "Late high"]


def test_explain_plan_shows_scores_only_when_weighted(household):
    _, buddy, _, scheduler = household
    buddy.add_task(make_task("Walk", priority="low", due_date=TODAY - timedelta(days=3)))
    weighted = scheduler.explain_plan(TODAY, weighted=True)
    assert "[score 5]" in weighted and "priority points" in weighted and "overdue since" in weighted
    strict = scheduler.explain_plan(TODAY)
    assert "[score" not in strict and "priority points" not in strict


def _tight_budget_household(household):
    """40 minutes, one 30-minute medium task due today and one 30-minute low task five days late."""
    owner, buddy, _, scheduler = household
    owner.available_minutes = 40
    buddy.add_task(make_task("Medium today", "08:00", priority="medium"))
    buddy.add_task(make_task("Low, 5 days late", "09:00", priority="low", due_date=TODAY - timedelta(days=5)))
    return scheduler


def test_weighted_explanation_lists_the_weighted_choice_and_what_it_left_out(household):
    scheduler = _tight_budget_household(household)
    lines = scheduler.explain_plan(TODAY, weighted=True).splitlines()
    assert lines[0] == f"Plan for {TODAY}: 1 task(s), 30 of 40 available minutes used."
    left_out = lines.index("Left out because they did not fit in the available time:")
    chosen_lines, skipped_lines = lines[2:left_out], lines[left_out + 1:]
    assert len(chosen_lines) == 1 and "Low, 5 days late" in chosen_lines[0] and "[score 7]" in chosen_lines[0]
    assert len(skipped_lines) == 1 and "Medium today" in skipped_lines[0] and "[score 5]" in skipped_lines[0]


def test_strict_explanation_for_the_same_tasks_chooses_the_other_one(household):
    scheduler = _tight_budget_household(household)
    lines = scheduler.explain_plan(TODAY).splitlines()
    left_out = lines.index("Left out because they did not fit in the available time:")
    assert "Medium today" in lines[2] and "Low, 5 days late" in lines[left_out + 1]


def test_weighted_explanation_states_the_scoring_rule_with_its_numbers(household):
    scheduler = _tight_budget_household(household)
    text = scheduler.explain_plan(TODAY, weighted=True)
    assert "priority points: high 10, medium 5, low 2; plus 1 per day overdue" in text
