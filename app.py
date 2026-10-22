from datetime import time

import streamlit as st

from pawpal_system import Owner, Pet, Scheduler, Task

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

# Streamlit reruns this whole script on every click, so a bare `Owner(...)` here would be
# recreated empty each time. st.session_state is a per-session dict that survives reruns:
# create the Owner only the first time, then reuse the stored one.
if "owner" not in st.session_state:
    st.session_state.owner = Owner("Jordan")
owner = st.session_state.owner
scheduler = Scheduler(owner)

st.title("🐾 PawPal+")

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
owner_name = st.text_input("Owner name", value="Jordan")
owner.name = owner_name  # keep the stored Owner in step with the text box
owner.available_minutes = int(
    st.number_input("Minutes available today", min_value=0, max_value=1440, value=480, step=5, key="available_minutes")
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
                    pet.add_task(
                        Task(description.strip(), task_time.strftime("%H:%M"), int(duration), priority, frequency)
                    )
                    st.success(f"Added '{description.strip()}' for {pet.name}.")
                except ValueError as err:  # Task rejects a bad time, duration, priority or frequency
                    st.error(str(err))

    all_tasks = scheduler.sort_by_time()  # reads every pet's tasks through Owner.get_all_tasks()
    if all_tasks:
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
                for t in all_tasks
            ]
        )
        for warning in scheduler.detect_conflicts():
            st.warning(warning)
    else:
        st.info("No tasks yet. Add one above.")

with pets_table:
    if owner.pets:
        st.table([{"Name": p.name, "Species": p.species, "Age": p.age, "Tasks": len(p.tasks)} for p in owner.pets])
    else:
        st.info("No pets yet. Add one above.")

st.divider()

st.subheader("Build Schedule")
st.caption("Fits today's tasks into your available minutes, highest priority first.")

if st.button("Generate schedule"):
    plan = scheduler.generate_plan()
    if not plan:
        if scheduler.filter_tasks(status=False):  # pending tasks exist, so the budget (or the due date) is the problem
            st.warning("No pending task fits in your available minutes (or none are due today).")
            with st.expander("Why this plan?", expanded=True):
                st.text(scheduler.explain_plan())
        else:
            st.info("Nothing to schedule today. Add some tasks first.")
    else:
        st.success(
            f"{len(plan)} task(s), {sum(t.duration for t in plan)} of {owner.available_minutes} minutes used."
        )
        st.table(
            [
                {"Time": t.time, "Task": t.description, "Pet": t.pet_name, "Min": t.duration, "Priority": t.priority}
                for t in plan
            ]
        )
        with st.expander("Why this plan?", expanded=True):
            st.text(scheduler.explain_plan())
