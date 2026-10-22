"""Temporary terminal testing ground for the PawPal+ logic layer."""

from datetime import date

from pawpal_system import Owner, Pet, Scheduler, Task


HEADERS = ("Date", "Time", "Task", "Pet", "Min", "Priority", "Done")


def print_tasks(title: str, tasks: list[Task]) -> None:
    """Print tasks as an aligned table under a title."""
    if title:
        print(f"\n{title}")
    if not tasks:
        print("  (none)")
        return
    rows = [
        (f"{t.due_date:%b %d}", t.time, t.description, t.pet_name, str(t.duration), t.priority, "yes" if t.completed else "no")
        for t in tasks
    ]
    widths = [max(len(h), *(len(r[i]) for r in rows)) for i, h in enumerate(HEADERS)]
    # Right-align the numeric Min column; left-align the rest.
    line = "  " + "  ".join(f"{{:{'>' if h == 'Min' else '<'}{w}}}" for h, w in zip(HEADERS, widths))
    print(line.format(*HEADERS).rstrip())
    print("  " + "  ".join("-" * w for w in widths))
    for row in rows:
        print(line.format(*row).rstrip())


def print_todays_schedule(scheduler: Scheduler) -> None:
    today = date.today()
    plan = scheduler.generate_plan(today)
    used = sum(t.duration for t in plan)
    print(f"\n=== Today's Schedule: {today:%A, %B %d, %Y} ===")
    print_tasks("", plan)
    print(f"\n  {len(plan)} tasks, {used} of {scheduler.owner.available_minutes} minutes used")


def main() -> None:
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


if __name__ == "__main__":
    main()
