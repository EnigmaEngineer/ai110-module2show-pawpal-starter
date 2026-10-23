"""Presentation helpers for PawPal+: icons, colour-coded labels, summaries and text tables.

Kept apart from pawpal_system.py so the scheduling engine stays free of display code. The terminal demo and the
Streamlit app both use these functions, so a task looks the same everywhere.

Colour comes from emoji (red, yellow and green circles), so it works in any terminal and in the web app without
escape codes. Every emoji used here is a double-width character without a variation selector, which keeps text
tables lined up.
"""

import re
from datetime import date

from pawpal_system import Task

try:
    from tabulate import tabulate
except ImportError:  # only the terminal tables need it; without it they fall back to plain text and the web app is unaffected
    tabulate = None

PRIORITY_ICON = {"high": "🔴", "medium": "🟡", "low": "🟢"}
STATUS_DONE = "✅ Done"
STATUS_PENDING = "⏳ Pending"
STATUS_OVERDUE = "🚨 Overdue"
DEFAULT_ICON = "🐾"
LEGEND = "Priority: 🔴 high  🟡 medium  🟢 low    Status: ✅ done  ⏳ pending  🚨 overdue"

# Tasks have no "type" field, so the kind of care is guessed from the description. The first pattern that matches
# wins, which is why "Lunch walk" is a walk and not a meal. Anything unrecognised gets the paw print.
_TYPE_PATTERNS = [
    (icon, re.compile(pattern, re.IGNORECASE))
    for icon, pattern in (
        ("🏥", r"\b(?:vet|doctor|appointment|check-?up|vaccin(?:e|es|ation|ations|ated))\b"),
        ("💊", r"\b(?:meds?|medication|medicine|pills?|dose|drops|injection|insulin)\b"),
        ("🦮", r"\b(?:walk(?:s|ed|ing)?|jog(?:s|ged|ging)?|hike|hikes|hiking|run(?:s|ning)?)\b"),
        ("🍖", r"\b(?:feed(?:s|ing)?|breakfast|lunch|dinner|meals?|food|treats?|snacks?)\b"),
        ("🛁", r"\b(?:groom(?:s|ed|ing)?|brush(?:es|ed|ing)?|bath(?:e|es|ing)?|wash(?:es|ed|ing)?|nails?|trim(?:s|med|ming)?|teeth)\b"),
        ("🎾", r"\b(?:play(?:s|ing|time)?|fetch|toys?|train(?:s|ed|ing)?|enrichment|puzzle)\b"),
        ("🚽", r"\b(?:litter|potty|poop(?:s|ing)?|clean(?:s|ed|ing)?)\b"),
        ("💧", r"\bwater\b"),
    )
]


def task_icon(description: str) -> str:
    """Return an emoji for the kind of care a task describes (walk, meal, medicine, grooming, play and so on)."""
    for icon, pattern in _TYPE_PATTERNS:
        if pattern.search(description):
            return icon
    return DEFAULT_ICON


def priority_label(priority: str) -> str:
    """Return the priority with its colour-coded circle, e.g. "🔴 High"."""
    return f"{PRIORITY_ICON[priority]} {priority.title()}"


def status_label(task: Task, today: date | None = None) -> str:
    """Return "✅ Done", "🚨 Overdue" (pending and due before `today`) or "⏳ Pending"."""
    if task.completed:
        return STATUS_DONE
    return STATUS_OVERDUE if task.due_date < (today or date.today()) else STATUS_PENDING


def task_rows(tasks: list[Task], today: date | None = None) -> list[dict]:
    """Return one display row per task, as dicts with the same column names the app's tables use."""
    today = today or date.today()
    return [
        {
            "Date": f"{t.due_date:%b %d}",
            "Time": t.time,
            "Type": task_icon(t.description),
            "Task": t.description,
            "Pet": t.pet_name,
            "Min": t.duration,
            "Priority": priority_label(t.priority),
            "Repeats": t.frequency,
            "Status": status_label(t, today),
        }
        for t in tasks
    ]


def summary_counts(tasks: list[Task], today: date | None = None) -> dict:
    """Count tasks by status: {"total", "pending", "done", "overdue"}. Overdue tasks are not also counted as pending."""
    labels = [status_label(t, today) for t in tasks]
    return {
        "total": len(tasks),
        "pending": labels.count(STATUS_PENDING),
        "done": labels.count(STATUS_DONE),
        "overdue": labels.count(STATUS_OVERDUE),
    }


def summary_line(tasks: list[Task], today: date | None = None) -> str:
    """Return a one-line tally such as "📋 5 tasks   ⏳ 3 pending   ✅ 1 done   🚨 1 overdue"."""
    c = summary_counts(tasks, today)
    noun = "task" if c["total"] == 1 else "tasks"
    return f"📋 {c['total']} {noun}   ⏳ {c['pending']} pending   ✅ {c['done']} done   🚨 {c['overdue']} overdue"


def budget_bar(used: int, available: int, width: int = 20) -> str:
    """Return a text gauge of minutes used, e.g. "[███████████████░░░░░] 75 of 90 min (83%)"."""
    if available <= 0:
        return f"[{'░' * width}] {used} of {available} min"
    share = min(used / available, 1.0)
    filled = round(share * width)
    return f"[{'█' * filled}{'░' * (width - filled)}] {used} of {available} min ({share:.0%})"


def tasks_table(tasks: list[Task], today: date | None = None, tablefmt: str = "rounded_outline", repeats: bool = False) -> str:
    """Return the tasks as a boxed text table with icons and colour-coded priority and status.

    `repeats` adds the Repeats column. Returns "(no tasks)" for an empty list.
    """
    if not tasks:
        return "(no tasks)"
    rows = task_rows(tasks, today)
    headers = ["Date", "Time", "Type", "Task", "Pet", "Min", "Priority", "Status"]
    if repeats:
        headers.insert(7, "Repeats")
    body = [[row[h] for h in headers] for row in rows]
    alignment = ["right" if h == "Min" else "left" for h in headers]
    if tabulate is None:
        return _plain_table(headers, body, alignment)
    return tabulate(body, headers=headers, tablefmt=tablefmt, colalign=alignment, disable_numparse=True)


def _plain_table(headers: list[str], body: list[list], alignment: list[str]) -> str:
    """Return a simple aligned table made of plain text, used when tabulate is not installed."""
    cells = [[str(cell) for cell in row] for row in body]
    widths = [max(len(text) for text in column) for column in zip(headers, *cells)]

    def line(row: list[str]) -> str:
        return " | ".join(
            text.rjust(width) if side == "right" else text.ljust(width) for text, width, side in zip(row, widths, alignment)
        ).rstrip()

    rule = "-+-".join("-" * width for width in widths)
    return "\n".join([line(headers), rule, *(line(row) for row in cells)])


_MARKDOWN_SPECIAL = re.compile(r"([\\`*_\[\]()#~$<>|{}&])")


def escape_markdown(text: str) -> str:
    """Return `text` with Markdown characters escaped and line breaks turned into spaces, so Streamlit shows it literally.

    Streamlit renders the text of warnings, messages and (some) tables as Markdown, so a task called "[click](http://x)" or
    "**bold**" would otherwise become a link or bold text, and an image link would make the browser fetch that address.
    """
    return _MARKDOWN_SPECIAL.sub(r"\\\1", re.sub(r"\s*[\r\n]+\s*", " ", str(text)))
