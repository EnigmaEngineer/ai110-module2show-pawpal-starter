"""Temporary terminal testing ground for the PawPal+ logic layer."""

from datetime import date, timedelta

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

    sorting_check()
    completion_check("Daily recurrence (happy path)", days_late=0)
    completion_check("Late completion", days_late=3)
    conflict_check()


if __name__ == "__main__":
    main()
