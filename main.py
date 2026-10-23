"""Terminal demo of the PawPal+ logic layer, with icons, colour-coded labels and boxed tables."""

import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

from formatting import LEGEND, budget_bar, summary_line, tasks_table
from pawpal_system import Owner, Pet, Scheduler, Task


def print_tasks(title: str, tasks: list[Task]) -> None:
    """Print tasks as a boxed table with icons and colour-coded priority and status, under a title."""
    if title:
        print(f"\n{title}")
    print(indent(tasks_table(tasks)))


def indent(text: str, spaces: int = 2) -> str:
    """Indent every line of a block of text."""
    pad = " " * spaces
    return "\n".join(pad + line for line in text.splitlines())


def print_todays_schedule(scheduler: Scheduler) -> None:
    today = date.today()
    plan = scheduler.generate_plan(today)
    used = sum(t.duration for t in plan)
    print(f"\n=== Today's Schedule: {today:%A, %B %d, %Y} ===")
    print_tasks("", plan)
    print(f"\n  {summary_line(plan)}")
    print(f"  Time budget  {budget_bar(used, scheduler.owner.available_minutes)}")


def sorting_check() -> None:
    print("\n=== Sorting check ===")
    today = date.today()
    owner = Owner(name="Sam")
    pet = Pet(name="Buddy", species="dog", age=3)
    owner.add_pet(pet)
    for description, at in [("Dinner", "18:00"), ("Breakfast", "08:00"), ("Lunch walk", "12:30"), ("Coffee break", "09:00")]:
        pet.add_task(
            Task(description=description, time=at, duration=15, priority="medium", frequency="once", due_date=today)
        )

    print_tasks("Insertion order:", pet.tasks)
    ordered = Scheduler(owner).sort_by_time()
    print_tasks("Via scheduler.sort_by_time():", ordered)
    times = [t.time for t in ordered]
    print(f"\n  Times ascend: {times == sorted(times)} {times}")


def priority_sorting_check() -> None:
    """Show sort_by_time and sort_by_priority ordering the same tasks differently."""
    print("\n=== Priority-first sorting ===")
    owner = Owner("Sam")
    buddy = Pet("Buddy", "dog", 3)
    owner.add_pet(buddy)
    buddy.add_task(Task("Evening meds", "20:00", 5, "high", "daily"))
    buddy.add_task(Task("Play fetch", "07:00", 20, "low", "once"))
    buddy.add_task(Task("Lunch walk", "12:00", 30, "medium", "once"))
    buddy.add_task(Task("Breakfast", "06:30", 10, "high", "daily"))
    scheduler = Scheduler(owner)
    print_tasks("By time:", scheduler.sort_by_time())
    print_tasks("By priority (high first, then time):", scheduler.sort_by_priority())


def completion_check(title: str, days_late: int) -> None:
    """Complete a daily task due `days_late` days ago and show when its next occurrence lands."""
    print(f"\n=== {title} ===")
    today = date.today()
    owner = Owner(name="Sam")
    pet = Pet(name="Buddy", species="dog", age=3)
    owner.add_pet(pet)
    scheduler = Scheduler(owner)
    task = Task(
        description="Evening walk",
        time="18:00",
        duration=30,
        priority="medium",
        frequency="daily",
        due_date=today - timedelta(days=days_late),
    )
    pet.add_task(task)

    follow_up = scheduler.complete_task(task)
    print(f"  Original due {task.due_date}, completed on {today}")
    print_tasks("New task:", [follow_up])
    print(f"\n  new due_date == today + 1: {follow_up.due_date == today + timedelta(days=1)} ({follow_up.due_date})")
    if days_late:
        print(f"  new due_date == original due_date + 1: {follow_up.due_date == task.due_date + timedelta(days=1)}")


def print_conflicts(scheduler: Scheduler) -> None:
    for warning in scheduler.detect_conflicts() or ["(none)"]:
        print(f"  {warning}")


def conflict_check() -> None:
    print("\n=== Conflict warnings ===")
    today = date.today()
    owner = Owner(name="Sam")
    buddy = Pet(name="Buddy", species="dog", age=3)
    mia = Pet(name="Mia", species="cat", age=2)
    owner.add_pet(buddy)
    owner.add_pet(mia)
    walk = Task(description="Walk", time="08:00", duration=30, priority="high", frequency="once", due_date=today)
    feed = Task(description="Breakfast", time="08:00", duration=10, priority="high", frequency="once", due_date=today)
    buddy.add_task(walk)
    mia.add_task(feed)
    scheduler = Scheduler(owner)

    print("Both pending:")
    print_conflicts(scheduler)
    walk.mark_complete()
    print("After marking 'Walk' complete:")
    print_conflicts(scheduler)


def overlap_and_free_slot_check() -> None:
    """Show same-start and overlapping tasks being flagged, back-to-back tasks being left alone, and free-slot search."""
    print("\n=== Overlap detection and next free slot ===")
    owner = Owner("Sam")
    buddy, mia = Pet("Buddy", "dog", 3), Pet("Mia", "cat", 2)
    owner.add_pet(buddy)
    owner.add_pet(mia)
    buddy.add_task(Task("Long walk", "09:00", 60, "medium", "once"))  # busy 09:00-10:00
    buddy.add_task(Task("Brush", "09:00", 15, "low", "once"))  # same start as the walk
    mia.add_task(Task("Feed", "09:30", 10, "high", "once"))  # starts while the walk is still going
    mia.add_task(Task("Meds", "10:00", 5, "high", "once"))  # starts the minute the walk ends: no clash
    scheduler = Scheduler(owner)

    print_tasks("Tasks:", scheduler.sort_by_time())
    print("\nWarnings:")
    for warning in scheduler.detect_conflicts():
        print(f"  {warning}")
    print("\nNext free slot (first time the whole task fits between the others):")
    for minutes, earliest in ((30, "08:00"), (15, "09:00"), (60, "09:00")):
        slot = scheduler.suggest_free_time(minutes, earliest=earliest)
        print(f"  {minutes} min, not before {earliest}: {slot or 'nothing fits today'}")


def weighted_planning_check() -> None:
    """Show strict priority and priority-with-aging choosing differently when the budget allows only one task."""
    print("\n=== Weighted prioritization (aging) ===")
    owner = Owner("Sam", available_minutes=30)  # room for exactly one 30-minute task
    buddy = Pet("Buddy", "dog", 3)
    owner.add_pet(buddy)
    buddy.add_task(Task("Evening walk", "18:00", 30, "medium", "once"))
    buddy.add_task(Task("Brush teeth", "09:00", 30, "low", "once", due_date=date.today() - timedelta(days=5)))
    scheduler = Scheduler(owner)

    for task in scheduler.sort_by_time():
        print(f"  score {scheduler.task_score(task):>2}  {task}")
    print("\nStrict priority:")
    print(scheduler.explain_plan())
    print("\nPriority with aging:")
    print(scheduler.explain_plan(weighted=True))


def persistence_check() -> None:
    """Save an owner to a JSON file, load it back, and show that nothing was lost (uses a temporary folder)."""
    print("\n=== Data persistence ===")
    owner = Owner("Sam", available_minutes=90)
    buddy, mia = Pet("Buddy", "dog", 3), Pet("Mia", "cat", 2)
    owner.add_pet(buddy)
    owner.add_pet(mia)
    buddy.add_task(Task("Morning walk", "08:00", 30, "high", "daily"))
    buddy.add_task(Task("Grooming", "16:00", 45, "low", "weekly", due_date=date.today() - timedelta(days=3)))
    done = Task("Medication", "12:30", 5, "high", "once")
    done.mark_complete()
    mia.add_task(done)

    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "data.json"
        owner.save_to_json(path)
        print(f"  Saved {len(owner.pets)} pets and {len(owner.get_all_tasks())} tasks to {path.name} ({path.stat().st_size} bytes)")
        loaded = Owner.load_from_json(path)

    pets = ", ".join(f"{p.name} ({len(p.tasks)} task{'s' if len(p.tasks) != 1 else ''})" for p in loaded.pets)
    print(f"  Reloaded: {loaded.name}, {loaded.available_minutes} minutes, pets {pets}")
    print(f"  Reloaded owner equals the original: {loaded == owner}")
    print_tasks("Reloaded tasks, sorted by time:", Scheduler(loaded).sort_by_time())

    try:
        Owner.from_dict({"name": "Sam", "available_minutes": 90, "pets": [
            {"name": "Rex", "species": "dog", "age": 2, "tasks": [
                {"description": "Walk", "time": "8am", "duration": 30, "priority": "high",
                 "frequency": "once", "completed": False, "due_date": "2026-03-02"}]}]})
    except ValueError as err:
        print(f"\n  A task with a bad time in the file is rejected: {err}")


def use_utf8_output() -> None:
    """Make stdout able to print emoji and box lines.

    A Windows console on a legacy code page cannot encode them and would stop the demo with a UnicodeEncodeError.
    Does nothing if the stream cannot be reconfigured (for example an in-memory capture).
    """
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError, OSError):
        pass


def main() -> None:
    use_utf8_output()
    owner = Owner("Sam", available_minutes=90)
    buddy = Pet("Buddy", "dog", 3)
    mia = Pet("Mia", "cat", 2)
    owner.add_pet(buddy)
    owner.add_pet(mia)

    # Added out of time order on purpose, so sorting has work to do.
    buddy.add_task(Task("Grooming", "16:00", 45, "low", "weekly"))
    buddy.add_task(Task("Morning walk", "08:00", 30, "high", "daily"))
    mia.add_task(Task("Breakfast", "08:00", 10, "high", "daily"))  # same time as the walk
    mia.add_task(Task("Medication", "12:30", 5, "high", "daily"))
    buddy.add_task(Task("Evening walk", "18:00", 30, "medium", "daily"))

    scheduler = Scheduler(owner)

    print(f"Owner: {owner.name}, {owner.available_minutes} minutes available")
    print(f"{LEGEND}\n")
    print_todays_schedule(scheduler)
    print_tasks("All tasks, sorted by time:", scheduler.sort_by_time())

    print("\nConflicts:")
    for warning in scheduler.detect_conflicts() or ["(none)"]:
        print(f"  {warning}")

    print("\n" + scheduler.explain_plan())

    walk = buddy.tasks[1]
    follow_up = scheduler.complete_task(walk)
    print(f"\nCompleted '{walk.description}'; next occurrence due {follow_up.due_date}")

    print_tasks("Buddy's pending tasks:", scheduler.filter_tasks(pet_name="Buddy", status=False))
    print_tasks("Completed tasks:", scheduler.filter_tasks(status=True))

    sorting_check()
    priority_sorting_check()
    completion_check("Daily recurrence (happy path)", days_late=0)
    completion_check("Late completion", days_late=3)
    conflict_check()
    overlap_and_free_slot_check()
    weighted_planning_check()
    persistence_check()


if __name__ == "__main__":
    main()
