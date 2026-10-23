"""Icons, colour-coded labels, summaries and text tables (formatting.py)."""

from datetime import date, timedelta

import pytest
from wcwidth import wcswidth

from formatting import (
    DEFAULT_ICON,
    LEGEND,
    PRIORITY_ICON,
    STATUS_DONE,
    STATUS_OVERDUE,
    STATUS_PENDING,
    budget_bar,
    escape_markdown,
    priority_label,
    status_label,
    summary_counts,
    summary_line,
    task_icon,
    task_rows,
    tasks_table,
)
from pawpal_system import Task

TODAY = date(2026, 3, 2)


def make(description="Walk", priority="medium", due=TODAY, done=False, **kwargs):
    task = Task(description, "08:00", kwargs.pop("duration", 30), priority, kwargs.pop("frequency", "once"), due_date=due)
    task.pet_name = kwargs.pop("pet", "Buddy")
    if done:
        task.mark_complete()
    return task


# --- Task icons ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "description, icon",
    [
        ("Morning walk", "🦮"), ("Evening Walk", "🦮"), ("Walking the dog", "🦮"), ("Jog", "🦮"), ("Lunch walk", "🦮"),
        ("Breakfast", "🍖"), ("Feed", "🍖"), ("Feeding time", "🍖"), ("Dinner", "🍖"), ("Give a treat", "🍖"),
        ("Medication", "💊"), ("Evening meds", "💊"), ("Give pill", "💊"), ("Insulin", "💊"),
        ("Grooming", "🛁"), ("Brush teeth", "🛁"), ("Bath", "🛁"), ("Trim nails", "🛁"),
        ("Play fetch", "🎾"), ("Training session", "🎾"), ("Puzzle toy", "🎾"),
        ("Vet visit", "🏥"), ("Annual check-up", "🏥"), ("Vaccination", "🏥"),
        ("Clean litter box", "🚽"), ("Refill water", "💧"),
    ],
)
def test_task_icon_matches_the_kind_of_care(description, icon):
    assert task_icon(description) == icon


@pytest.mark.parametrize("description", ["Coffee break", "Medium today", "Low, 5 days late", "Social time", "", "   "])
def test_unrecognised_descriptions_get_the_paw_print(description):
    assert task_icon(description) == DEFAULT_ICON


def test_icons_ignore_capitals_and_the_first_matching_kind_wins():
    assert task_icon("MORNING WALK") == "🦮"
    assert task_icon("Vet: give meds") == "🏥"  # vet is checked before meds
    assert task_icon("Lunch walk") == "🦮"  # walk is checked before meals


def test_icons_need_whole_words_so_medium_is_not_medicine():
    assert task_icon("Medium priority chore") == DEFAULT_ICON
    assert task_icon("Wash") == "🛁" and task_icon("Washington") == DEFAULT_ICON


def test_every_icon_is_two_columns_wide_so_tables_line_up():
    from formatting import _TYPE_PATTERNS

    icons = [icon for icon, _ in _TYPE_PATTERNS] + [DEFAULT_ICON, *PRIORITY_ICON.values()]
    assert all(wcswidth(icon) == 2 and "️" not in icon for icon in icons)


# --- Priority and status labels -------------------------------------------------------------


@pytest.mark.parametrize("priority, label", [("high", "🔴 High"), ("medium", "🟡 Medium"), ("low", "🟢 Low")])
def test_priority_label_colour_codes_each_level(priority, label):
    assert priority_label(priority) == label


def test_status_label_distinguishes_done_overdue_and_pending():
    assert status_label(make(done=True), TODAY) == STATUS_DONE
    assert status_label(make(due=TODAY - timedelta(days=1)), TODAY) == STATUS_OVERDUE
    assert status_label(make(due=TODAY), TODAY) == STATUS_PENDING
    assert status_label(make(due=TODAY + timedelta(days=1)), TODAY) == STATUS_PENDING


def test_a_completed_overdue_task_shows_as_done_not_overdue():
    assert status_label(make(due=TODAY - timedelta(days=5), done=True), TODAY) == STATUS_DONE


def test_status_defaults_to_the_real_today():
    assert status_label(make(due=date.today() - timedelta(days=1))) == STATUS_OVERDUE
    assert status_label(make(due=date.today())) == STATUS_PENDING


# --- Rows, counts and summaries -------------------------------------------------------------


def test_task_rows_have_one_dict_per_task_in_order_with_every_column():
    tasks = [make("Morning walk", "high", pet="Buddy", duration=30, frequency="daily"), make("Brush", "low", pet="Mia")]
    rows = task_rows(tasks, TODAY)
    assert [r["Task"] for r in rows] == ["Morning walk", "Brush"]
    assert list(rows[0]) == ["Date", "Time", "Type", "Task", "Pet", "Min", "Priority", "Repeats", "Status"]
    assert rows[0] == {
        "Date": "Mar 02", "Time": "08:00", "Type": "🦮", "Task": "Morning walk", "Pet": "Buddy", "Min": 30,
        "Priority": "🔴 High", "Repeats": "daily", "Status": "⏳ Pending",
    }
    assert task_rows([], TODAY) == []


def test_summary_counts_split_tasks_by_status_without_double_counting():
    tasks = [
        make("A"), make("B"), make("C", due=TODAY - timedelta(days=2)),
        make("D", done=True), make("E", due=TODAY - timedelta(days=9), done=True),
    ]
    assert summary_counts(tasks, TODAY) == {"total": 5, "pending": 2, "done": 2, "overdue": 1}
    assert summary_counts([], TODAY) == {"total": 0, "pending": 0, "done": 0, "overdue": 0}


def test_summary_line_reads_naturally_and_handles_one_task():
    assert summary_line([make("A"), make("B", done=True)], TODAY) == "📋 2 tasks   ⏳ 1 pending   ✅ 1 done   🚨 0 overdue"
    assert summary_line([make("A")], TODAY).startswith("📋 1 task   ")
    assert summary_line([], TODAY) == "📋 0 tasks   ⏳ 0 pending   ✅ 0 done   🚨 0 overdue"


@pytest.mark.parametrize(
    "used, available, expected",
    [
        (75, 90, "[█████████████████░░░] 75 of 90 min (83%)"),
        (0, 90, "[░░░░░░░░░░░░░░░░░░░░] 0 of 90 min (0%)"),
        (90, 90, "[████████████████████] 90 of 90 min (100%)"),
        (120, 90, "[████████████████████] 120 of 90 min (100%)"),  # never draws past a full bar
        (5, 0, "[░░░░░░░░░░░░░░░░░░░░] 5 of 0 min"),
    ],
)
def test_budget_bar(used, available, expected):
    assert budget_bar(used, available) == expected


def test_budget_bar_width_can_change_and_stays_that_wide():
    bar = budget_bar(5, 10, width=10)
    assert bar.startswith("[█████░░░░░]") and len(bar.split("]")[0]) == 11


# --- Text table ------------------------------------------------------------------------------


def test_tasks_table_is_a_box_with_the_expected_headers_and_rows():
    table = tasks_table([make("Morning walk", "high", pet="Buddy"), make("Grooming", "low", pet="Mia")], TODAY)
    lines = table.splitlines()
    assert lines[0].startswith("╭") and lines[-1].startswith("╰")
    header = lines[1]
    for column in ("Date", "Time", "Type", "Task", "Pet", "Min", "Priority", "Status"):
        assert column in header
    assert "Repeats" not in header
    assert "Morning walk" in table and "🔴 High" in table and "🛁" in table and "⏳ Pending" in table


def test_tasks_table_can_show_the_repeats_column():
    table = tasks_table([make("Walk", frequency="weekly")], TODAY, repeats=True)
    assert "Repeats" in table and "weekly" in table


def test_every_line_of_the_table_is_the_same_display_width_even_with_emoji():
    tasks = [
        make("Morning walk", "high"), make("Grooming", "low", done=True), make("Medium today", "medium"),
        make("Old vet visit", "high", due=TODAY - timedelta(days=3)), make("Feed", "medium", duration=5),
    ]
    widths = {wcswidth(line) for line in tasks_table(tasks, TODAY).splitlines()}
    assert len(widths) == 1


def test_minutes_are_right_aligned():
    table = tasks_table([make("Short", duration=5), make("Long", duration=120)], TODAY)
    rows = [line for line in table.splitlines() if "Short" in line or "Long" in line]
    short_cell, long_cell = rows[0].split("│")[6], rows[1].split("│")[6]  # the Min column
    assert short_cell.strip() == "5" and short_cell.endswith("5 ") and short_cell.startswith("  ")
    assert long_cell.strip() == "120" and long_cell.endswith("120 ")


def test_tasks_table_for_no_tasks_says_so():
    assert tasks_table([], TODAY) == "(no tasks)"


def test_the_legend_names_every_colour_and_status():
    for label in ("🔴 high", "🟡 medium", "🟢 low", "✅ done", "⏳ pending", "🚨 overdue"):
        assert label in LEGEND


# --- Every word the icon patterns know, and the ones they must not match ------------------------------------------


VOCABULARY = {
    "🏥": ["vet", "doctor", "appointment", "check-up", "checkup", "vaccine", "vaccines", "vaccination", "vaccinations", "vaccinated"],
    "💊": ["med", "meds", "medication", "medicine", "pill", "pills", "dose", "drops", "injection", "insulin"],
    "🦮": ["walk", "walks", "walked", "walking", "jog", "jogs", "jogged", "jogging", "hike", "hikes", "hiking", "run", "runs", "running"],
    "🍖": ["feed", "feeds", "feeding", "breakfast", "lunch", "dinner", "meal", "meals", "food", "treat", "treats", "snack", "snacks"],
    "🛁": ["groom", "grooms", "groomed", "grooming", "brush", "brushes", "brushed", "brushing", "bath", "bathe", "bathes", "bathing",
           "wash", "washes", "washed", "washing", "nail", "nails", "trim", "trims", "trimmed", "trimming", "teeth"],
    "🎾": ["play", "plays", "playing", "playtime", "fetch", "toy", "toys", "train", "trains", "trained", "training", "enrichment", "puzzle"],
    "🚽": ["litter", "potty", "poop", "poops", "pooping", "clean", "cleans", "cleaned", "cleaning"],
    "💧": ["water"],
}


@pytest.mark.parametrize("icon, word", [(icon, word) for icon, words in VOCABULARY.items() for word in words])
def test_every_known_word_maps_to_its_icon(icon, word):
    assert task_icon(word.title()) == icon
    assert task_icon(f"Evening {word.upper()} for Rex") == icon  # at any position, in any case


@pytest.mark.parametrize(
    "description",
    ["Velvet", "Vetch", "Overdose", "Rerun", "Walker", "Seafood", "Feeder", "Replay", "Unclean", "Brushwood", "Bathroom", "Washington", "Medium"],
)
def test_words_that_merely_contain_a_known_word_get_the_paw_print(description):
    assert task_icon(description) == "🐾"


@pytest.mark.parametrize(
    "description, icon",
    [
        ("Vet meds", "🏥"),  # vet before medicine
        ("Walk after meds", "💊"),  # medicine before walk
        ("Lunch walk", "🦮"),  # walk before meal
        ("Brush after dinner", "🍖"),  # meal before grooming
        ("Play after bath", "🛁"),  # grooming before play
        ("Play then clean", "🎾"),  # play before litter
        ("Clean water bowl", "🚽"),  # litter before water
    ],
)
def test_when_two_kinds_match_the_earlier_one_in_the_list_wins(description, icon):
    assert task_icon(description) == icon


def test_the_shared_labels_are_exactly_these_characters():
    assert (DEFAULT_ICON, STATUS_DONE, STATUS_PENDING, STATUS_OVERDUE) == ("🐾", "✅ Done", "⏳ Pending", "🚨 Overdue")
    assert PRIORITY_ICON == {"high": "🔴", "medium": "🟡", "low": "🟢"}
    assert status_label(make(due=TODAY - timedelta(days=1)), TODAY) == "🚨 Overdue"


def test_summary_line_reports_different_counts_for_each_status():
    tasks = [make("A"), make("B"), make("C"), make("D", done=True)] + [make(f"Late {i}", due=TODAY - timedelta(days=1)) for i in range(2)]
    assert summary_line(tasks, TODAY) == "📋 6 tasks   ⏳ 3 pending   ✅ 1 done   🚨 2 overdue"


# --- Table details ----------------------------------------------------------------------------------------------


def header_cells(table):
    return [cell.strip() for cell in table.splitlines()[1].split("│")[1:-1]]


def test_the_columns_come_in_a_fixed_order_with_repeats_before_status():
    tasks = [make("Walk")]
    assert header_cells(tasks_table(tasks, TODAY)) == ["Date", "Time", "Type", "Task", "Pet", "Min", "Priority", "Status"]
    assert header_cells(tasks_table(tasks, TODAY, repeats=True)) == ["Date", "Time", "Type", "Task", "Pet", "Min", "Priority", "Repeats", "Status"]


@pytest.mark.parametrize("description", ["007", "1e3", "1,000", "3.0", "0x10"])
def test_numeric_looking_descriptions_are_not_reformatted(description):
    assert f"│ {description} " in tasks_table([make(description)], TODAY)


def test_text_columns_are_left_aligned():
    row = tasks_table([make("Walk", pet="Buddy")], TODAY).splitlines()[3]
    assert row.split("│")[5].startswith(" Buddy") and row.split("│")[4].startswith(" Walk")


# --- Plain-text fallback when tabulate is missing ------------------------------------------------------------------


def test_formatting_can_be_imported_when_tabulate_is_not_installed():
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    code = "import sys; sys.modules['tabulate'] = None; import formatting; assert formatting.tabulate is None; print('ok')"
    result = subprocess.run([sys.executable, "-c", code], cwd=root, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0 and result.stdout.strip() == "ok", result.stderr[-300:]


def test_without_tabulate_the_table_falls_back_to_aligned_plain_text(monkeypatch):
    import formatting

    monkeypatch.setattr(formatting, "tabulate", None)
    table = tasks_table([make("Walk", pet="Buddy", duration=5), make("Grooming", "low", pet="Mia", duration=120)], TODAY)
    lines = table.splitlines()
    assert len(lines) == 4  # header, rule, two rows
    assert lines[0].startswith("Date") and " | " in lines[0] and set(lines[1]) <= set("-+")
    assert "Walk" in lines[2] and "Grooming" in lines[3] and "🛁" in lines[3]
    assert "  5 |" in lines[2] and "120 |" in lines[3]  # minutes right-aligned
    assert tasks_table([], TODAY) == "(no tasks)"
    assert "Repeats" in tasks_table([make("Walk")], TODAY, repeats=True).splitlines()[0]


# --- Showing text literally in Streamlit ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Morning walk", "Morning walk"),
        ("Feed (Mia)", r"Feed \(Mia\)"),
        ("[click](http://x)", r"\[click\]\(http://x\)"),
        ("![pixel](http://x/p.png) meds", r"!\[pixel\]\(http://x/p.png\) meds"),
        ("**bold** _it_ `code`", r"\*\*bold\*\* \_it\_ \`code\`"),
        ("# Heading", r"\# Heading"),
        (":red[red text]", r":red\[red text\]"),
        ("$$x^2$$", r"\$\$x^2\$\$"),
        ("<b>x</b> & y", r"\<b\>x\</b\> \& y"),
        (r"back\slash", r"back\\slash"),
        ("a | b", r"a \| b"),
        ("first\nsecond\r\nthird", "first second third"),
        ("", ""),
        (5, "5"),
    ],
)
def test_escape_markdown_makes_text_display_literally(text, expected):
    assert escape_markdown(text) == expected
