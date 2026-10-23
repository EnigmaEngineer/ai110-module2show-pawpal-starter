"""PawPal+ logic layer: Owner, Pet, Task, and Scheduler.

Attributes and method signatures mirror diagrams/uml_final.mmd. The Scheduler
reads every task through Owner.get_all_tasks(), never from a single Pet.
"""

import json
import os
import re
from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from pathlib import Path

PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}  # lower rank = more important
PRIORITY_POINTS = {"high": 10, "medium": 5, "low": 2}  # base score for weighted planning
OVERDUE_POINTS_PER_DAY = 1  # aging: each day overdue adds this many points
FREQUENCY_DAYS = {"daily": 1, "weekly": 7}  # "once" never recurs
MINUTES_PER_DAY = 24 * 60
DATA_VERSION = 1  # bump if the saved JSON layout changes
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

    def to_dict(self) -> dict:
        """Return this task as JSON-ready data. The pet name is left out: the owning Pet restores it on load."""
        return {
            "description": self.description,
            "time": self.time,
            "duration": self.duration,
            "priority": self.priority,
            "frequency": self.frequency,
            "completed": self.completed,
            "due_date": self.due_date.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        """Rebuild a task from to_dict output; raise ValueError if the data is missing, mistyped or invalid."""
        try:
            description, duration, completed = data["description"], data["duration"], data["completed"]
            if not isinstance(description, str) or not description.strip():
                raise ValueError("description must be non-empty text")
            if isinstance(duration, bool) or not isinstance(duration, int):
                raise ValueError("duration must be a whole number of minutes")
            if not isinstance(completed, bool):
                raise ValueError("completed must be true or false")
            return cls(
                description, data["time"], duration, data["priority"], data["frequency"],
                completed=completed, due_date=date.fromisoformat(data["due_date"]),
            )
        except (KeyError, TypeError, AttributeError) as err:  # missing key, wrong type, or data that is not a dict
            raise ValueError(f"invalid task data: {err!r}") from err

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

    def to_dict(self) -> dict:
        """Return this pet and all its tasks as JSON-ready data."""
        return {"name": self.name, "species": self.species, "age": self.age, "tasks": [t.to_dict() for t in self.tasks]}

    @classmethod
    def from_dict(cls, data: dict) -> "Pet":
        """Rebuild a pet and its tasks from to_dict output; raise ValueError if the data is invalid."""
        try:
            name, species, age, tasks = data["name"], data["species"], data["age"], data["tasks"]
            if not isinstance(name, str) or not name.strip():
                raise ValueError("pet name must be non-empty text")
            if not isinstance(species, str):
                raise ValueError("species must be text")
            if isinstance(age, bool) or not isinstance(age, int) or age < 0:
                raise ValueError("age must be a whole number, zero or more")
            if not isinstance(tasks, list):
                raise ValueError("tasks must be a list")
            return cls(name, species, age, [Task.from_dict(t) for t in tasks])
        except (KeyError, TypeError, AttributeError) as err:
            raise ValueError(f"invalid pet data: {err!r}") from err


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

    def to_dict(self) -> dict:
        """Return the owner, pets and tasks as JSON-ready data."""
        return {"name": self.name, "available_minutes": self.available_minutes, "pets": [p.to_dict() for p in self.pets]}

    @classmethod
    def from_dict(cls, data: dict) -> "Owner":
        """Rebuild an owner from to_dict output; raise ValueError if the data is invalid or repeats a pet name."""
        try:
            name, minutes, pets = data["name"], data["available_minutes"], data["pets"]
            if not isinstance(name, str):
                raise ValueError("owner name must be text")
            if isinstance(minutes, bool) or not isinstance(minutes, int) or not 0 <= minutes <= MINUTES_PER_DAY:
                raise ValueError(f"available_minutes must be a whole number from 0 to {MINUTES_PER_DAY}")
            if not isinstance(pets, list):
                raise ValueError("pets must be a list")
            owner = cls(name, available_minutes=minutes)
            for pet_data in pets:
                owner.add_pet(Pet.from_dict(pet_data))  # add_pet rejects a repeated name
            return owner
        except (KeyError, TypeError, AttributeError) as err:
            raise ValueError(f"invalid owner data: {err!r}") from err

    def save(self, path: str | Path) -> None:
        """Write the owner, pets and tasks to a JSON file. The file is replaced in one step, so a crash mid-save
        cannot leave a half-written data file."""
        path = Path(path)
        temp = path.with_name(path.name + ".tmp")
        payload = {"version": DATA_VERSION, "owner": self.to_dict()}
        try:
            temp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            os.replace(temp, path)
        finally:
            temp.unlink(missing_ok=True)  # no-op after a successful replace

    @classmethod
    def load(cls, path: str | Path) -> "Owner | None":
        """Read an owner saved by save(). Return None if the file does not exist; raise ValueError if it is unreadable,
        from another version, or holds invalid data (the file itself is never modified)."""
        path = Path(path)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as err:  # bad JSON or bad UTF-8 (both are ValueErrors)
            raise ValueError(f"{path.name} could not be read as JSON: {err}") from err
        if not isinstance(payload, dict) or payload.get("version") != DATA_VERSION:
            raise ValueError(f"{path.name} is not a PawPal+ data file (expected version {DATA_VERSION})")
        return cls.from_dict(payload.get("owner"))


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

    def suggest_free_time(
        self, duration: int, day: date | None = None, earliest: str = "00:00", ignore: Task | None = None
    ) -> str | None:
        """Return the first "HH:MM" at or after `earliest` where `duration` minutes fit between pending tasks on `day`.

        `ignore` leaves one task out of the check, e.g. the task being moved. Returns None if nothing fits before midnight.
        """
        if duration <= 0:
            raise ValueError(f"duration must be positive, got {duration}")
        if not TIME_PATTERN.fullmatch(earliest):
            raise ValueError(f"earliest must be zero-padded HH:MM, got {earliest!r}")
        day = day or date.today()
        busy = sorted(
            (_to_minutes(t.time), _to_minutes(t.time) + t.duration)
            for t in self.owner.get_all_tasks()
            if not t.completed and t.due_date == day and t is not ignore
        )
        start = _to_minutes(earliest)
        for busy_start, busy_end in busy:
            if start + duration <= busy_start:
                break  # fits in the gap before this task
            start = max(start, busy_end)
        return _format_minutes(start) if start + duration <= MINUTES_PER_DAY else None

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

    def task_score(self, task: Task, day: date | None = None) -> int:
        """Return the task's weighted-planning score: priority points plus a bonus for each day overdue on `day`."""
        days_overdue = max(0, ((day or date.today()) - task.due_date).days)
        return PRIORITY_POINTS[task.priority] + OVERDUE_POINTS_PER_DAY * days_overdue

    def generate_plan(self, day: date | None = None, weighted: bool = False) -> list[Task]:
        """Build the ordered daily plan, fitting tasks into owner.available_minutes.

        By default tasks are chosen strictly by priority. With `weighted=True` they are chosen by task_score, so a
        task that has been overdue long enough can outrank a higher-priority task due today.
        """
        return self._build_plan(day or date.today(), weighted)[0]

    def explain_plan(self, day: date | None = None, weighted: bool = False) -> str:
        """Return a human-readable explanation of the plan's ordering and what was left out."""
        day = day or date.today()
        plan, skipped = self._build_plan(day, weighted)
        budget = self.owner.available_minutes
        used = sum(t.duration for t in plan)
        if weighted:
            how = (
                f"Tasks were chosen by score (priority points: high {PRIORITY_POINTS['high']}, medium "
                f"{PRIORITY_POINTS['medium']}, low {PRIORITY_POINTS['low']}; plus {OVERDUE_POINTS_PER_DAY} per day overdue), "
                "highest first, until time ran out; they are listed in the order they happen."
            )
        else:
            how = (
                "Tasks were chosen by priority (high first), then oldest due date (overdue first), "
                "then earliest time, until time ran out; they are listed in the order they happen."
            )
        lines = [f"Plan for {day}: {len(plan)} task(s), {used} of {budget} available minutes used.", how]

        def describe(task: Task) -> str:
            """Return the task's summary line, flagged if it was due before `day` and scored if weighted."""
            overdue = f" (overdue since {task.due_date})" if task.due_date < day else ""
            score = f" [score {self.task_score(task, day)}]" if weighted else ""
            return f"  {task}{overdue}{score}"

        lines += [describe(t) for t in plan]
        if skipped:
            lines.append("Left out because they did not fit in the available time:")
            lines += [describe(t) for t in skipped]
        return "\n".join(lines)

    def _build_plan(self, day: date, weighted: bool = False) -> tuple[list[Task], list[Task]]:
        """Return (plan, skipped): pending tasks due by `day`, split by what fits in the time budget."""
        pending = [t for t in self.owner.get_all_tasks() if not t.completed and t.due_date <= day]
        if weighted:
            by_importance = sorted(pending, key=lambda t: (-self.task_score(t, day), t.due_date, t.time))
        else:
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
