from datetime import date
from sqlite3 import Error as DatabaseError

import streamlit as st

from storage import WorkoutStore
from training import (
    CONSISTENCY_DAYS,
    CONSISTENCY_GOAL,
    EXERCISES,
    MUSCLES,
    Workout,
    consistency,
    exercise_tiers,
    weekly_training,
)


def workout_form(store: WorkoutStore, today: date) -> None:
    st.subheader("Log a Workout")
    with st.form("workout"):
        exercise = st.selectbox("Exercise", list(EXERCISES), index=0)
        day = st.date_input("Workout date", value=today, max_value=today)
        weight = st.number_input(
            "Weight (kg)", min_value=0.01, max_value=1000.0, value=40.0, step=0.5
        )
        reps_column, sets_column = st.columns(2)
        with reps_column:
            reps = st.number_input("Reps", min_value=1, max_value=500, value=8)
        with sets_column:
            sets = st.number_input("Sets", min_value=1, max_value=100, value=3)
        submitted = st.form_submit_button("Save Workout", type="primary", width="stretch")

    if not submitted:
        return

    try:
        store.save(Workout(day, exercise, weight, reps, sets))
    except ValueError as error:
        st.error(str(error))
    except DatabaseError:
        st.error("Could not save the workout. Please try again.")
    else:
        st.success("Workout saved.")


def show_history(workouts: list[Workout]) -> None:
    st.subheader("Workout History")
    if not workouts:
        st.info("Your saved workouts will appear here.")
        return

    history = []
    for workout in workouts:
        row = {
            "Date": workout.day,
            "Exercise": workout.exercise,
            "Weight (kg)": workout.weight_kg,
            "Reps": workout.reps,
            "Sets": workout.sets,
        }
        history.append(row)

    st.dataframe(history, hide_index=True, width="stretch")


def show_weekly_training(workouts: list[Workout], today: date) -> None:
    st.header("Weekly Training by Muscle Group")
    weeks = weekly_training(workouts, today)
    current = weeks[-1]
    chart_data = []
    for week in weeks:
        chart_row: dict[str, date | int] = {"Week Starting": week.start}
        for muscle in MUSCLES:
            chart_row[muscle] = week.muscles[muscle].sets
        chart_data.append(chart_row)

    chart_column, summary_column = st.columns([3, 2], gap="large")
    with chart_column:
        st.subheader("Sets Over the Last 4 Weeks")
        st.line_chart(
            chart_data, x="Week Starting", y=list(MUSCLES), y_label="Sets", height=260
        )
    with summary_column:
        st.subheader("This Week")
        st.caption(f"Week of {current.start:%Y-%m-%d} · Volume = weight × reps × sets")
        summary = []
        for muscle, training in current.muscles.items():
            row = {
                "Muscle Group": muscle,
                "Sets": training.sets,
                "Volume (kg × reps)": training.volume,
            }
            summary.append(row)

        st.dataframe(summary, hide_index=True, width="stretch")


def show_tiers(workouts: list[Workout]) -> None:
    st.subheader("Exercise Tiers")
    st.caption("Your heaviest logged lift determines your tier for each exercise.")
    rows = []
    for exercise, tier in exercise_tiers(workouts).items():
        best_lift = "—"
        if tier.best_weight is not None:
            best_lift = f"{tier.best_weight:g} kg"

        next_milestone = "Master reached"
        if tier.next_weight is not None:
            next_milestone = f"{tier.next_weight} kg"

        row = {
            "Exercise": exercise,
            "Tier": tier.name,
            "Best Lift": best_lift,
            "Next Milestone": next_milestone,
        }
        rows.append(row)

    st.dataframe(rows, hide_index=True, width="stretch")


def show_consistency(workouts: list[Workout], today: date) -> None:
    st.subheader("Consistency Score")
    result = consistency(workouts, today)
    st.metric(f"Last {CONSISTENCY_DAYS} days", f"{result.score} / 100")
    st.progress(result.score)
    st.caption(f"Days trained {result.active_days} · Goal {CONSISTENCY_GOAL}")


def main() -> None:
    st.set_page_config(page_title="GoUp", layout="wide")
    st.title("GoUp")
    try:
        store = WorkoutStore()
    except (OSError, DatabaseError):
        st.error("Could not open the workout database. Check that the project folder is writable.")
        return

    today = date.today()
    form_column, history_column = st.columns([1, 2], gap="large")
    with form_column:
        workout_form(store, today)
    try:
        workouts = store.list_workouts()
    except DatabaseError:
        st.error("Could not load your workouts. Please try again.")
        return
    with history_column:
        show_history(workouts)

    st.divider()
    show_weekly_training(workouts, today)
    st.divider()
    tiers_column, consistency_column = st.columns([3, 2], gap="large")
    with tiers_column:
        show_tiers(workouts)
    with consistency_column:
        show_consistency(workouts, today)


if __name__ == "__main__":
    main()
