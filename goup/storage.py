"""Read and save the local JSON file. Import the original SQLite logs once."""

from contextlib import closing, contextmanager
import json
import os
from pathlib import Path
import sqlite3
from tempfile import NamedTemporaryFile
from threading import RLock

from .data import EXERCISES


DEFAULT_PATH = Path(__file__).resolve().parents[1] / "data" / "goup_data.json"
LEGACY_EXERCISES = {
    "벤치프레스": "Bench Press",
    "스쿼트": "Squat",
    "데드리프트": "Deadlift",
}


def empty_data():
    return {"profile": None, "workouts": [], "routines": [], "active_workout": None}


def import_sqlite(path):
    workouts = []
    uri = path.resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as database:
        rows = database.execute(
            "SELECT id, workout_date, exercise, weight_kg, reps, sets FROM workouts ORDER BY id"
        ).fetchall()
    for identifier, day, name, weight, reps, count in rows:
        exercise = LEGACY_EXERCISES.get(name, name)
        if exercise not in EXERCISES:
            raise ValueError(f"The original database contains an unknown exercise: {exercise}")
        sets = []
        for _ in range(count):
            sets.append({"weight": weight, "reps": reps})
        workouts.append({
            "id": identifier, "started_at": day + "T00:00:00",
            "exercises": [{"name": exercise, "rest_seconds": 120, "sets": sets}],
        })
    return workouts


class DataStore:
    def __init__(self, path=DEFAULT_PATH):
        self.path = Path(path)
        self.lock = RLock()

    def read(self):
        with self.lock:
            if self.path.exists():
                with self.path.open(encoding="utf-8") as file:
                    return json.load(file)
            data = empty_data()
            legacy_path = self.path.with_name("goup.sqlite3")
            if legacy_path.exists():
                data["workouts"] = import_sqlite(legacy_path)
                self.write(data)
            return data

    def write(self, data):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.lock:
            temporary_path = None
            try:
                # Write the whole JSON file before replacing the previous copy.
                with NamedTemporaryFile(
                    mode="w", encoding="utf-8", dir=self.path.parent, delete=False
                ) as file:
                    temporary_path = Path(file.name)
                    json.dump(data, file, ensure_ascii=False, indent=2)
                os.replace(temporary_path, self.path)
            finally:
                if temporary_path is not None:
                    temporary_path.unlink(missing_ok=True)

    @contextmanager
    def edit(self):
        with self.lock:
            data = self.read()
            yield data
            self.write(data)
