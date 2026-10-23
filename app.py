import json
import os
from datetime import time
from pathlib import Path

import streamlit as st

from formatting import LEGEND, escape_markdown, summary_counts, task_icon, task_rows
from pawpal_system import Owner, Pet, Scheduler, Task

# Pets and tasks are saved here between runs. PAWPAL_DATA_FILE overrides the location (the tests use it).
DATA_FILE = Path(os.environ.get("PAWPAL_DATA_FILE") or Path(__file__).with_name("data.json"))

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

# Everything the app remembers in st.session_state; deleting or reloading the saved data clears all of it.
SESSION_KEYS = ("owner", "owner_name", "available_minutes", "saved", "load_notice", "disk_sig", "autosave")


def disk_signature():
    """Return (modified time, size) of the data file, or None if it does not exist.

    Comparing it with the value from our last load or save tells us whether another window or program wrote the file.
    """
    try:
        info = DATA_FILE.stat()
    except OSError:
        return None
    return (info.st_mtime_ns, info.st_size)


def quarantine(path):
    """Move an unreadable data file aside without overwriting an earlier backup; return where it went."""
    target = path.with_name(path.name + ".corrupt")
    number = 1
    while target.exists():
        number += 1
        target = path.with_name(f"{path.name}.corrupt{number}")
    os.replace(path, target)
    return target


# Streamlit reruns this whole script on every click, so a bare `Owner(...)` here would be
# recreated empty each time. st.session_state is a per-session dict that survives reruns:
# load the saved Owner (or start a new one) only the first time, then reuse the stored one.
if "owner" not in st.session_state:
    try:
        loaded = Owner.load_from_json(DATA_FILE)
    except ValueError as err:
        loaded = None
        try:  # keep the unreadable file instead of overwriting it with the next save
            kept = f" It was kept as {quarantine(DATA_FILE).name}."
        except OSError:
            kept = " It could not be moved aside, so nothing will be saved until it is fixed."
            st.session_state.autosave = False  # never overwrite a file we could neither read nor set aside
        st.session_state.load_notice = f"Could not load {DATA_FILE.name} ({err}), so PawPal+ started empty.{kept}"
    st.session_state.owner = loaded or Owner("Jordan")
    st.session_state.saved = json.dumps(st.session_state.owner.to_dict(), sort_keys=True)  # what is on disk now
    st.session_state.disk_sig = disk_signature()
owner = st.session_state.owner
scheduler = Scheduler(owner)

st.title("🐾 PawPal+")
if "load_notice" in st.session_state:
    st.warning(escape_markdown(st.session_state.load_notice))

st.markdown(
    """
PawPal+ helps a busy pet owner plan the day: add your pets, give each one care tasks,
and generate a plan that fits your available time and explains its choices.
"""
)

with st.expander("Scenario", expanded=False):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.
"""
    )

st.divider()

st.subheader("Owner")
# The widgets start from the loaded Owner's values (setdefault only runs the first time), so a saved name and
# time budget are not overwritten by the widgets' own defaults.
st.session_state.setdefault("owner_name", owner.name)
st.session_state.setdefault("available_minutes", owner.available_minutes)
owner.name = st.text_input("Owner name", key="owner_name")  # keep the stored Owner in step with the text box
owner.available_minutes = int(
    st.number_input("Minutes available today", min_value=0, max_value=1440, step=5, key="available_minutes")
)

# --- Pets -------------------------------------------------------------------
# Submitting the form calls Owner.add_pet(Pet(...)). Streamlit then reruns the script, and the
# table below reads owner.pets again, so the new pet appears without any extra UI code.
st.subheader("Pets")
with st.form("add_pet_form", clear_on_submit=True):
    pet_name = st.text_input("Pet name")
    species = st.selectbox("Species", ["dog", "cat", "other"])
    age = st.number_input("Age (years)", min_value=0, max_value=40, value=1)
    if st.form_submit_button("Add pet"):
        if not pet_name.strip():
            st.error("Give your pet a name.")
        else:
            try:
                owner.add_pet(Pet(pet_name.strip(), species, int(age)))
                st.success(f"Added {escape_markdown(pet_name.strip())}.")
            except ValueError as err:  # Owner.add_pet rejects a duplicate name
                st.error(escape_markdown(str(err)))

pets_table = st.container()  # filled in after the Tasks section, so its task counts are never a click behind

# --- Tasks ------------------------------------------------------------------
# Submitting calls Pet.add_task(Task(...)) on the chosen pet; Task validates its own fields.
st.subheader("Tasks")
if not owner.pets:
    st.info("Add a pet first, then you can give it tasks.")
else:
    with st.form("add_task_form", clear_on_submit=True):
        pet_choice = st.selectbox("Pet", [p.name for p in owner.pets])
        description = st.text_input("Task description", value="Morning walk")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            task_time = st.time_input("Time", value=time(8, 0))
        with col2:
            duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
        with col3:
            priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)
        with col4:
            frequency = st.selectbox("Repeats", ["once", "daily", "weekly"])
        if st.form_submit_button("Add task"):
            if not description.strip():
                st.error("Describe the task.")
            else:
                pet = next(p for p in owner.pets if p.name == pet_choice)
                try:
                    new_task = Task(description.strip(), task_time.strftime("%H:%M"), int(duration), priority, frequency)
                    before = set(scheduler.detect_conflicts())
                    pet.add_task(new_task)
                    st.success(f"Added '{escape_markdown(description.strip())}' for {escape_markdown(pet.name)}.")
                    caused = [w for w in scheduler.detect_conflicts() if w not in before]  # warnings this task created
                    for warning in caused:
                        st.warning(escape_markdown(warning), icon="⚠️")
                    if caused:
                        free = scheduler.suggest_free_time(
                            new_task.duration, new_task.due_date, earliest=new_task.time, ignore=new_task
                        )
                        if free:
                            st.info(f"Next free slot for {new_task.duration} min after {new_task.time}: **{free}**.")
                        else:
                            st.info("No free slot is left today after that time. Try an earlier time or a shorter task.")
                except ValueError as err:  # Task rejects a bad time, duration, priority or frequency
                    st.error(escape_markdown(str(err)))

    all_tasks = scheduler.sort_by_time()  # reads every pet's tasks through Owner.get_all_tasks()
    if all_tasks:
        if "flash" in st.session_state:
            st.success(escape_markdown(st.session_state.pop("flash")))

        # Conflicts come first and cover every pending task, whatever the filters below hide, so a clash is never out of sight.
        conflicts = scheduler.detect_conflicts()
        if conflicts:
            st.warning(
                f"**{len(conflicts)} scheduling conflict{'s' if len(conflicts) > 1 else ''}.** "
                "You can't be in two places at once. Change the time of one task listed below, or make it shorter."
            )
            for conflict in conflicts:
                st.warning(escape_markdown(conflict), icon="⚠️")
        else:
            st.success("No scheduling conflicts.")

        filter_pet, filter_status, order_by = st.columns(3)
        with filter_pet:
            pet_filter = st.selectbox("Show pet", ["All pets"] + [p.name for p in owner.pets])
        with filter_status:
            status_filter = st.radio("Show tasks", ["All", "Pending", "Completed"], horizontal=True)
        with order_by:
            order_choice = st.radio("Order by", ["Time", "Priority first"], horizontal=True)
        ordered = scheduler.sort_by_priority() if order_choice == "Priority first" else all_tasks
        matches = scheduler.filter_tasks(
            pet_name=None if pet_filter == "All pets" else pet_filter,
            status={"All": None, "Pending": False, "Completed": True}[status_filter],
        )
        match_ids = {id(t) for t in matches}
        shown = [t for t in ordered if id(t) in match_ids]  # filter, then keep the chosen order

        counts = summary_counts(all_tasks)  # tallies cover every task, whatever the filters hide
        tally = st.columns(4)
        tally[0].metric("📋 Tasks", counts["total"])
        tally[1].metric("⏳ Pending", counts["pending"])
        tally[2].metric("🚨 Overdue", counts["overdue"])
        tally[3].metric("✅ Done", counts["done"])

        if shown:
            st.dataframe(task_rows(shown), hide_index=True)  # a dataframe shows text literally; st.table would render Markdown
            st.caption(LEGEND)
        else:
            st.info("No tasks match these filters.")

        pending = [t for t in all_tasks if not t.completed]
        if pending:
            choice = st.selectbox(
                "Mark a task done",
                range(len(pending)),
                format_func=lambda i: f"{task_icon(pending[i].description)} {pending[i].due_date:%b %d} {pending[i].time}  {pending[i].description} ({pending[i].pet_name})",
            )
            if st.button("Mark complete"):
                done = pending[choice]
                follow_up = scheduler.complete_task(done)
                st.session_state.flash = f"Completed '{done.description}'." + (
                    "" if follow_up is None else f" Next {follow_up.frequency} one is due {follow_up.due_date:%b %d}."
                )
                st.rerun()  # redraw the table above with the new status; the message survives in session_state
    else:
        st.info("No tasks yet. Add one above.")

with pets_table:
    if owner.pets:
        st.dataframe(
            [{"Name": p.name, "Species": p.species, "Age": p.age, "Tasks": len(p.tasks)} for p in owner.pets], hide_index=True
        )
    else:
        st.info("No pets yet. Add one above.")

st.divider()

st.subheader("Build Schedule")
st.caption("Fits today's tasks into your available minutes.")
planning_style = st.radio(
    "Planning style",
    ["Strict priority", "Priority with aging"],
    horizontal=True,
    help="Strict priority always picks high before medium before low. With aging, each day a task is overdue adds "
    "a point to its score (high 10, medium 5, low 2), so a task that keeps getting skipped eventually wins a slot.",
)
weighted = planning_style == "Priority with aging"

if st.button("Generate schedule"):
    plan = scheduler.generate_plan(weighted=weighted)
    if not plan:
        if scheduler.filter_tasks(status=False):  # pending tasks exist, so the budget (or the due date) is the problem
            st.warning("No pending task fits in your available minutes (or none are due today).")
            with st.expander("Why this plan?", expanded=True):
                st.text(scheduler.explain_plan(weighted=weighted))
        else:
            st.info("Nothing to schedule today. Add some tasks first.")
    else:
        used = sum(t.duration for t in plan)
        st.success(f"{len(plan)} task(s), {used} of {owner.available_minutes} minutes used.")
        if owner.available_minutes > 0:
            st.progress(min(used / owner.available_minutes, 1.0), text=f"Time budget: {used} of {owner.available_minutes} minutes")
        st.dataframe(
            [
                {
                    **{key: row[key] for key in ("Time", "Type", "Task", "Pet", "Min", "Priority")},
                    **({"Score": scheduler.task_score(t)} if weighted else {}),
                }
                for t, row in zip(plan, task_rows(plan))
            ],
            hide_index=True,
        )
        with st.expander("Why this plan?", expanded=True):
            st.text(scheduler.explain_plan(weighted=weighted))

# --- Saved data -------------------------------------------------------------
st.divider()
with st.expander("Saved data"):
    st.caption(f"Pets, tasks and your time budget are saved automatically to {DATA_FILE.name} and reloaded next time.")
    confirm = st.checkbox("I want to delete all pets and tasks")
    if st.button("Delete all saved data", disabled=not confirm):
        try:
            DATA_FILE.unlink(missing_ok=True)
        except OSError as err:
            st.error(f"Could not delete {DATA_FILE.name}: {err}")
        else:
            for key in SESSION_KEYS:
                st.session_state.pop(key, None)
            st.rerun()  # the next run finds no file and starts with an empty owner

# Autosave: write the file whenever anything changed since the last save. The rerun after "Mark complete"
# ends its pass early, so that change is written by the pass that follows it. If another window or program
# changed the file since this page loaded or saved it, writing would silently erase that work, so ask first.
snapshot = json.dumps(owner.to_dict(), sort_keys=True)
if snapshot != st.session_state.saved and st.session_state.get("autosave", True):
    if disk_signature() != st.session_state.disk_sig:
        st.warning(
            f"**{DATA_FILE.name} was changed by another window or program after this page loaded**, so your latest "
            "changes were not saved. Choose which version to keep."
        )
        keep_this, keep_saved = st.columns(2)
        if keep_this.button("Overwrite the file with this window"):
            st.session_state.disk_sig = disk_signature()  # accept the other change as replaced; the next run saves
            st.rerun()
        if keep_saved.button("Reload the saved file (discard this window's changes)"):
            for key in SESSION_KEYS:
                st.session_state.pop(key, None)
            st.rerun()
    else:
        try:
            owner.save_to_json(DATA_FILE)
            st.session_state.saved = snapshot
            st.session_state.disk_sig = disk_signature()
        except OSError as err:
            st.warning(f"Could not save to {DATA_FILE.name}: {err}")
