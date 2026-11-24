from contextlib import closing
import sqlite3

import pytest

from goup.seed import main as seed
from goup.storage import DataStore, empty_data


def test_original_sqlite_records_import_once_without_changing_database(tmp_path):
    legacy = tmp_path / "goup.sqlite3"
    with closing(sqlite3.connect(legacy)) as sql, sql:
        sql.execute("CREATE TABLE workouts (id, workout_date, exercise, weight_kg, reps, sets)")
        sql.execute("INSERT INTO workouts VALUES (?, ?, ?, ?, ?, ?)", (1, "2026-11-24", "벤치프레스", 40, 8, 3))
    store = DataStore(tmp_path / "goup_data.json")
    original = legacy.read_bytes()
    data = store.read()
    assert data["workouts"][0]["exercises"][0]["name"] == "Bench Press"
    assert len(data["workouts"][0]["exercises"][0]["sets"]) == 3
    assert store.read() == data
    assert legacy.read_bytes() == original


def test_serialization_failure_preserves_saved_json(tmp_path):
    path = tmp_path / "goup_data.json"
    store = DataStore(path)
    original = empty_data()
    store.write(original)
    with pytest.raises(TypeError):
        store.write({"bad": object()})
    assert store.read() == original
    assert list(tmp_path.iterdir()) == [path]


def test_edit_rolls_back_when_validation_fails(tmp_path):
    store = DataStore(tmp_path / "goup_data.json")
    store.write(empty_data())
    with pytest.raises(ValueError):
        with store.edit() as data:
            data["routines"].append({"name": "Invalid"})
            raise ValueError("Check input.")
    assert store.read() == empty_data()


def test_demo_seed_requires_force_and_keeps_backup(tmp_path, monkeypatch):
    path = tmp_path / "demo.json"
    store = DataStore(path)
    store.write(empty_data())
    monkeypatch.setattr("sys.argv", ["goup.seed", "--path", str(path)])
    with pytest.raises(SystemExit):
        seed()
    assert store.read() == empty_data()
    monkeypatch.setattr("sys.argv", ["goup.seed", "--path", str(path), "--force"])
    seed()
    assert len(store.read()["workouts"]) == 44
    backup = next(tmp_path.glob("demo.backup-*.json"))
    assert DataStore(backup).read() == empty_data()
