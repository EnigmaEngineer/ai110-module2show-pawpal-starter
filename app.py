import json
import os
from datetime import time
from pathlib import Path

import streamlit as st

from pawpal_system import Owner, Pet, Scheduler, Task

# Pets and tasks are saved here between runs. PAWPAL_DATA_FILE overrides the location (the tests use it).
DATA_FILE = Path(os.environ.get("PAWPAL_DATA_FILE") or Path(__file__).with_name("data.json"))

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

# Streamlit reruns this whole script on every click, so a bare `Owner(...)` here would be
# recreated empty each time. st.session_state is a per-session dict that survives reruns:
# load the saved Owner (or start a new one) only the first time, then reuse the stored one.
if "owner" not in st.session_state:
    try:
        loaded = Owner.load(DATA_FILE)
    except ValueError as err:
        loaded = None
        try:  # keep the unreadable file instead of overwriting it with the next save
            os.replace(DATA_FILE, DATA_FILE.with_name(DATA_FILE.name + ".corrupt"))
            kept = f" It was kept as {DATA_FILE.name}.corrupt."
        except OSError:
            kept = ""
        st.session_state.load_notice = f"Could not load {DATA_FILE.name} ({err}), so PawPal+ started empty.{kept}"
    st.session_state.owner = loaded or Owner("Jordan")
    st.session_state.saved = json.dumps(st.session_state.owner.to_dict(), sort_keys=True)  # what is on disk now
owner = st.session_state.owner
scheduler = Scheduler(owner)

st.title("🐾 PawPal+")
if "load_notice" in st.session_state:
    st.warning(st.session_state.load_notice)

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
                st.success(f"Added {pet_name.strip()}.")
            except ValueError as err:  # Owner.add_pet rejects a duplicate name
                st.error(str(err))

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
                    st.success(f"Added '{description.strip()}' for {pet.name}.")
                    caused = [w for w in scheduler.detect_conflicts() if w not in before]  # warnings this task created
                    for warning in caused:
                        st.warning(warning, icon="⚠️")
                    if caused:
                        free = scheduler.suggest_free_time(
                            new_task.duration, new_task.due_date, earliest=new_task.time, ignore=new_task
                        )
                        if free:
                            st.info(f"Next free slot for {new_task.duration} min after {new_task.time}: **{free}**.")
                        else:
                            st.info("No free slot is left today after that time. Try an earlier time or a shorter task.")
                except ValueError as err:  # Task rejects a bad time, duration, priority or frequency
                    st.error(str(err))

    all_tasks = scheduler.sort_by_time()  # reads every pet's tasks through Owner.get_all_tasks()
    if all_tasks:
        if "flash" in st.session_state:
            st.success(st.session_state.pop("flash"))

        # Conflicts come first and cover every pending task, whatever the filters below hide, so a clash is never out of sight.
        conflicts = scheduler.detect_conflicts()
        if conflicts:
            st.warning(
                f"**{len(conflicts)} scheduling conflict{'s' if len(conflicts) > 1 else ''}.** "
                "You can't be in two places at once. Change the time of one task listed below, or make it shorter."
            )
            for conflict in conflicts:
                st.warning(conflict, icon="⚠️")
        else:
            st.success("No scheduling conflicts.")

        filter_pet, filter_status = st.columns(2)
        with filter_pet:
            pet_filter = st.selectbox("Show pet", ["All pets"] + [p.name for p in owner.pets])
        with filter_status:
            status_filter = st.radio("Show tasks", ["All", "Pending", "Completed"], horizontal=True)
        matches = scheduler.filter_tasks(
            pet_name=None if pet_filter == "All pets" else pet_filter,
            status={"All": None, "Pending": False, "Completed": True}[status_filter],
        )
        match_ids = {id(t) for t in matches}
        shown = [t for t in all_tasks if id(t) in match_ids]  # filter, then keep the chronological order

        if shown:
            st.table(
                [
                    {
                        "Date": f"{t.due_date:%b %d}",
                        "Time": t.time,
                        "Task": t.description,
                        "Pet": t.pet_name,
                        "Min": t.duration,
                        "Priority": t.priority,
                        "Repeats": t.frequency,
                        "Done": "yes" if t.completed else "no",
                    }
                    for t in shown
                ]
            )
        else:
            st.info("No tasks match these filters.")

        pending = [t for t in all_tasks if not t.completed]
        if pending:
            choice = st.selectbox(
                "Mark a task done",
                range(len(pending)),
                format_func=lambda i: f"{pending[i].due_date:%b %d} {pending[i].time}  {pending[i].description} ({pending[i].pet_name})",
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
        st.table([{"Name": p.name, "Species": p.species, "Age": p.age, "Tasks": len(p.tasks)} for p in owner.pets])
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
        st.success(
            f"{len(plan)} task(s), {sum(t.duration for t in plan)} of {owner.available_minutes} minutes used."
        )
        st.table(
            [
                {
                    "Time": t.time,
                    "Task": t.description,
                    "Pet": t.pet_name,
                    "Min": t.duration,
                    "Priority": t.priority,
                    **({"Score": scheduler.task_score(t)} if weighted else {}),
                }
                for t in plan
            ]
        )
        with st.expander("Why this plan?", expanded=True):
            st.text(scheduler.explain_plan(weighted=weighted))

# --- Saved data -------------------------------------------------------------
st.divider()
with st.expander("Saved data"):
    st.caption(f"Pets, tasks and your time budget are saved automatically to {DATA_FILE.name} and reloaded next time.")
    confirm = st.checkbox("I want to delete all pets and tasks")
    if st.button("Delete all saved data", disabled=not confirm):
        DATA_FILE.unlink(missing_ok=True)
        for key in ("owner", "owner_name", "available_minutes", "saved", "load_notice"):
            st.session_state.pop(key, None)
        st.rerun()  # the next run finds no file and starts with an empty owner

# Autosave: write the file whenever anything changed since the last save. The rerun after "Mark complete"
# ends its pass early, so that change is written by the pass that follows it.
snapshot = json.dumps(owner.to_dict(), sort_keys=True)
if snapshot != st.session_state.saved:
    try:
        owner.save(DATA_FILE)
        st.session_state.saved = snapshot
    except OSError as err:
        st.warning(f"Could not save to {DATA_FILE.name}: {err}")
