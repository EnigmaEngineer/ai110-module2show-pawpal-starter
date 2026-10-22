"""Temporary terminal testing ground for the PawPal+ logic layer."""

from datetime import date

from pawpal_system import Owner, Pet, Scheduler, Task


def print_tasks(title: str, tasks: list[Task]) -> None:
    print(f"\n{title}")
    for task in tasks:
        print(f"  {task}")
    if not tasks:
        print("  (none)")


def print_todays_schedule(scheduler: Scheduler) -> None:
    today = date.today()
    print(f"\n=== Today's Schedule ({today:%A, %B %d, %Y}) ===")
    for task in scheduler.generate_plan(today):
        print(f"  {task.time}  {task.description:<14} {task.pet_name:<7} {task.duration:>3} min  [{task.priority}]")


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
