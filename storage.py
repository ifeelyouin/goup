import sqlite3
from contextlib import closing
from datetime import date
from pathlib import Path

from training import Workout


DEFAULT_DB_PATH = Path(__file__).resolve().parent / "data" / "goup.sqlite3"
# Earlier versions stored the Korean labels as exercise names.
LEGACY_EXERCISE_NAMES = {
    "벤치프레스": "Bench Press",
    "스쿼트": "Squat",
    "데드리프트": "Deadlift",
}


class WorkoutStore:
    def __init__(self, path: Path | None = None) -> None:
        if path is None:
            path = DEFAULT_DB_PATH
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS workouts (
                    id INTEGER PRIMARY KEY,
                    workout_date TEXT NOT NULL,
                    exercise TEXT NOT NULL,
                    weight_kg REAL NOT NULL CHECK (weight_kg > 0),
                    reps INTEGER NOT NULL CHECK (reps > 0),
                    sets INTEGER NOT NULL CHECK (sets > 0)
                )
                """
            )
            connection.commit()

    def save(self, workout: Workout) -> None:
        values = (
            workout.day.isoformat(),
            workout.exercise,
            workout.weight_kg,
            workout.reps,
            workout.sets,
        )
        with closing(sqlite3.connect(self.path)) as connection:
            connection.execute(
                """
                INSERT INTO workouts (workout_date, exercise, weight_kg, reps, sets)
                VALUES (?, ?, ?, ?, ?)
                """,
                values,
            )
            connection.commit()

    def list_workouts(self) -> list[Workout]:
        with closing(sqlite3.connect(self.path)) as connection:
            rows = connection.execute(
                """
                SELECT workout_date, exercise, weight_kg, reps, sets
                FROM workouts
                ORDER BY workout_date DESC, id DESC
                """
            ).fetchall()
        workouts = []
        for day, exercise, weight, reps, sets in rows:
            exercise_name = LEGACY_EXERCISE_NAMES.get(exercise, exercise)
            workout = Workout(date.fromisoformat(day), exercise_name, weight, reps, sets)
            workouts.append(workout)
        return workouts
