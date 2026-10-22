"""PawPal+ logic layer: Owner, Pet, Task, and Scheduler.

Skeleton only. Attributes and method signatures mirror diagrams/uml.mmd;
method bodies are filled in during later phases.
"""

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Task:
    description: str
    time: str  # "HH:MM", zero-padded so plain string sorting is chronological
    duration: int  # minutes
    priority: str  # "high" | "medium" | "low"
    frequency: str  # "once" | "daily" | "weekly"
    completed: bool = False
    pet_name: str = ""  # set by Pet.add_task

    def mark_complete(self) -> None:
        """Mark this task as done."""
        pass

    def next_occurrence(self) -> date:
        """Return the next due date for a recurring task."""
        pass


@dataclass
class Pet:
    name: str
    species: str
    age: int
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Attach a task to this pet and record the pet's name on it."""
        pass


@dataclass
class Owner:
    name: str
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Attach a pet to this owner."""
        pass

    def get_all_tasks(self) -> list[Task]:
        """Return every task across all pets as one flat list."""
        pass


class Scheduler:
    def __init__(self, owner: Owner) -> None:
        self.owner = owner

    def sort_by_time(self) -> list[Task]:
        """Return all tasks in chronological order."""
        pass

    def filter_tasks(self, pet_name: str | None = None, status: bool | None = None) -> list[Task]:
        """Return tasks narrowed by pet name and/or completion status."""
        pass

    def detect_conflicts(self) -> list[str]:
        """Return warning messages for tasks scheduled at the same time."""
        pass

    def generate_plan(self) -> list[Task]:
        """Build the ordered daily plan."""
        pass

    def explain_plan(self) -> str:
        """Return a human-readable explanation of the plan's ordering."""
        pass
