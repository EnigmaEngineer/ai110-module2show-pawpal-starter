"""PawPal+ logic layer: Owner, Pet, Task, and Scheduler.

Attributes and method signatures mirror diagrams/uml.mmd. The Scheduler
reads every task through Owner.get_all_tasks(), never from a single Pet.
"""

import re
from dataclasses import dataclass, field, replace
from datetime import date, timedelta

PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}  # lower rank = more important
FREQUENCY_DAYS = {"daily": 1, "weekly": 7}  # "once" never recurs
MINUTES_PER_DAY = 24 * 60
TIME_PATTERN = re.compile(r"([01]\d|2[0-3]):[0-5]\d", re.ASCII)  # ASCII: \d must not match other scripts' digits


@dataclass
class Task:
    description: str
    time: str  # "HH:MM", zero-padded so plain string sorting is chronological
    duration: int  # minutes
    priority: str  # "high" | "medium" | "low"
    frequency: str  # "once" | "daily" | "weekly"
    completed: bool = False
    due_date: date = field(default_factory=date.today)
    pet_name: str = ""  # set by Pet.add_task

    def __post_init__(self) -> None:
        """Reject a malformed time, a non-positive duration, or an unknown priority or frequency."""
        if not TIME_PATTERN.fullmatch(self.time):
            raise ValueError(f"time must be zero-padded HH:MM, got {self.time!r}")
        if self.duration <= 0:
            raise ValueError(f"duration must be positive, got {self.duration}")
        if self.priority not in PRIORITY_RANK:
            raise ValueError(f"priority must be one of {list(PRIORITY_RANK)}, got {self.priority!r}")
        if self.frequency != "once" and self.frequency not in FREQUENCY_DAYS:
            raise ValueError(f"frequency must be 'once', 'daily' or 'weekly', got {self.frequency!r}")

    def mark_complete(self) -> None:
        """Mark this task as done."""
        self.completed = True

    def next_occurrence(self, from_date: date | None = None) -> date | None:
        """Return the next due date, counted from the later of due_date and from_date (default today); None for a one-off task."""
        days = FREQUENCY_DAYS.get(self.frequency)
        if not days:
            return None
        anchor = max(self.due_date, from_date or date.today())
        return anchor + timedelta(days=days)

    def __str__(self) -> str:
        """Return a one-line summary: completion mark, time, description, pet, duration and priority."""
        mark = "x" if self.completed else " "
        pet = f" ({self.pet_name})" if self.pet_name else ""
        return f"[{mark}] {self.time} {self.description}{pet} - {self.duration} min, {self.priority}"


@dataclass
class Pet:
    name: str
    species: str
    age: int
    tasks: list[Task] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Copy any tasks passed to the constructor and record this pet's name on each."""
        self.tasks = list(self.tasks)  # don't alias the caller's list
        for task in self.tasks:
            task.pet_name = self.name

    def add_task(self, task: Task) -> None:
        """Attach a task to this pet and record the pet's name on it."""
        task.pet_name = self.name
        self.tasks.append(task)


@dataclass
class Owner:
    name: str
    pets: list[Pet] = field(default_factory=list)
    available_minutes: int = 480  # time budget the daily plan must fit into

    def add_pet(self, pet: Pet) -> None:
        """Attach a pet to this owner. Rejects a duplicate pet name, since tasks link to pets by name."""
        if any(p.name.lower() == pet.name.lower() for p in self.pets):
            raise ValueError(f"{self.name} already has a pet named {pet.name!r}")
        self.pets.append(pet)

    def get_all_tasks(self) -> list[Task]:
        """Return every task across all pets as one flat list."""
        return [task for pet in self.pets for task in pet.tasks]


def _to_minutes(time: str) -> int:
    """Convert a validated "HH:MM" string to minutes after midnight."""
    hours, minutes = time.split(":")
    return int(hours) * 60 + int(minutes)


def _format_minutes(total: int) -> str:
    """Convert minutes after midnight back to "HH:MM"."""
    return f"{total // 60:02d}:{total % 60:02d}"


def _same_occurrence(a: Task, b: Task) -> bool:
    """Return True if two tasks describe the same job at the same date and time."""
    return (a.description, a.time, a.due_date, a.frequency) == (b.description, b.time, b.due_date, b.frequency)


class Scheduler:
    def __init__(self, owner: Owner) -> None:
        """Create a scheduler that reads all its tasks through the given owner."""
        self.owner = owner

    def sort_by_time(self) -> list[Task]:
        """Return all tasks in chronological order (due date, then time, then priority, high first)."""
        return sorted(
            self.owner.get_all_tasks(),
            key=lambda t: (t.due_date, t.time, PRIORITY_RANK.get(t.priority, 99)),
        )

    def filter_tasks(self, pet_name: str | None = None, status: bool | None = None) -> list[Task]:
        """Return tasks narrowed by pet name and/or completion status (True = completed)."""
        tasks = self.owner.get_all_tasks()
        if pet_name is not None:
            tasks = [t for t in tasks if t.pet_name.lower() == pet_name.lower()]
        if status is not None:
            tasks = [t for t in tasks if t.completed == status]
        return tasks

    def detect_conflicts(self) -> list[str]:
        """Return a warning for each pending clash: a shared start time, or a task that starts before another ends.

        Only the due date's own day is considered, so a task running past midnight is cut off at 24:00.
        """
        pending = [t for t in self.owner.get_all_tasks() if not t.completed]
        slots: dict[tuple[date, str], list[Task]] = {}
        for task in pending:
            slots.setdefault((task.due_date, task.time), []).append(task)
        warnings = [
            ((day, time), f"Conflict on {day} at {time}: " + ", ".join(f"{t.description} ({t.pet_name})" for t in tasks))
            for (day, time), tasks in slots.items()
            if len(tasks) > 1
        ]
        for first, second in self._overlapping_pairs(pending):
            end = _format_minutes(min(_to_minutes(first.time) + first.duration, MINUTES_PER_DAY))
            warnings.append((
                (first.due_date, second.time),
                f"Overlap on {first.due_date}: {first.description} ({first.pet_name}) {first.time}-{end} "
                f"runs into {second.description} ({second.pet_name}) at {second.time}",
            ))
        return [message for _, message in sorted(warnings, key=lambda w: w[0])]

    @staticmethod
    def _overlapping_pairs(tasks: list[Task]) -> list[tuple[Task, Task]]:
        """Return (earlier, later) pairs on one day where the later starts after the earlier but before it ends."""
        pairs = []
        ordered = sorted(tasks, key=lambda t: (t.due_date, _to_minutes(t.time)))
        for i, first in enumerate(ordered):
            first_start = _to_minutes(first.time)
            for second in ordered[i + 1:]:
                if second.due_date != first.due_date:
                    break
                second_start = _to_minutes(second.time)
                if second_start == first_start:
                    continue  # identical start times are reported as a shared-slot conflict
                if second_start >= first_start + first.duration:
                    break  # sorted by start, so nothing later can overlap `first`
                pairs.append((first, second))
        return pairs

    def complete_task(self, task: Task) -> Task | None:
        """Mark a task complete; if it recurs, make sure its pet has the next occurrence and return it.

        If the pet already has an identical pending task on that date, that one is returned instead of adding a copy.
        """
        if task.completed:
            return None
        next_due = task.next_occurrence(date.today())
        pet = next((p for p in self.owner.pets if p.name == task.pet_name), None)
        if next_due is not None and pet is None:
            raise ValueError(f"No pet named {task.pet_name!r} to receive the next occurrence")
        task.mark_complete()
        if next_due is None:
            return None
        follow_up = replace(task, completed=False, due_date=next_due)
        existing = next((t for t in pet.tasks if not t.completed and _same_occurrence(t, follow_up)), None)
        if existing is not None:
            return existing
        pet.add_task(follow_up)
        return follow_up

    def generate_plan(self, day: date | None = None) -> list[Task]:
        """Build the ordered daily plan, fitting tasks into owner.available_minutes."""
        return self._build_plan(day or date.today())[0]

    def explain_plan(self, day: date | None = None) -> str:
        """Return a human-readable explanation of the plan's ordering and what was left out."""
        day = day or date.today()
        plan, skipped = self._build_plan(day)
        budget = self.owner.available_minutes
        used = sum(t.duration for t in plan)
        lines = [
            f"Plan for {day}: {len(plan)} task(s), {used} of {budget} available minutes used.",
            "Tasks were chosen by priority (high first), then oldest due date (overdue first), "
            "then earliest time, until time ran out; they are listed in the order they happen.",
        ]

        def describe(task: Task) -> str:
            """Return the task's summary line, flagged if it was due before `day`."""
            overdue = f" (overdue since {task.due_date})" if task.due_date < day else ""
            return f"  {task}{overdue}"

        lines += [describe(t) for t in plan]
        if skipped:
            lines.append("Left out because they did not fit in the available time:")
            lines += [describe(t) for t in skipped]
        return "\n".join(lines)

    def _build_plan(self, day: date) -> tuple[list[Task], list[Task]]:
        """Return (plan, skipped): pending tasks due by `day`, split by what fits in the time budget."""
        pending = [t for t in self.owner.get_all_tasks() if not t.completed and t.due_date <= day]
        by_importance = sorted(pending, key=lambda t: (PRIORITY_RANK[t.priority], t.due_date, t.time))
        remaining = self.owner.available_minutes
        chosen: list[Task] = []
        skipped: list[Task] = []
        for task in by_importance:
            if task.duration <= remaining:
                chosen.append(task)
                remaining -= task.duration
            else:
                skipped.append(task)
        return sorted(chosen, key=lambda t: (t.due_date, t.time)), skipped
