"""Create a local demo profile with 16 weeks of sample workouts."""

import argparse
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
from shutil import copy2

from .engine import week_start
from .storage import DEFAULT_PATH, DataStore, empty_data


def exercise(name, weight, reps, sets):
    return {
        "name": name, "rest_seconds": 120,
        "sets": [{"weight": weight, "reps": reps} for _ in range(sets)],
    }


def demo_data(now):
    first_monday = week_start(now.date()) - timedelta(weeks=16)
    data = empty_data()
    data["profile"] = {
        "name": "Demo", "district": "Mapo-gu", "body_weight": 75,
        "joined_at": datetime.combine(first_monday, now.time()).isoformat(),
        "lifts": {"Bench Press": 55, "Overhead Press": 35, "Barbell Curl": 22.5,
                  "Pull-up": 67.5, "Squat": 90},
    }
    upper = [
        exercise("Bench Press", 50, 8, 4), exercise("Incline Press", 35, 8, 3),
        exercise("Overhead Press", 30, 8, 3), exercise("Barbell Curl", 20, 8, 3),
    ]
    back = [
        exercise("Barbell Row", 40, 8, 4), exercise("Deadlift", 70, 5, 3),
        exercise("Lateral Raise", 10, 10, 3), exercise("Triceps Extension", 15, 10, 3),
    ]
    legs = [
        exercise("Squat", 75, 5, 3), exercise("Leg Press", 75, 8, 4),
        exercise("Leg Curl", 35, 8, 2), exercise("Calf Raise", 40, 8, 3),
        exercise("Crunch", 5, 12, 3),
    ]
    for week in range(16):
        sessions = [(0, upper), (4, legs)]
        if week < 12:
            sessions.insert(1, (2, back))
        for day_offset, exercises in sessions:
            day = first_monday + timedelta(weeks=week, days=day_offset)
            data["workouts"].append({
                "id": len(data["workouts"]) + 1,
                "started_at": datetime.combine(day, now.time()).isoformat(),
                "exercises": deepcopy(exercises),
            })
    data["routines"] = [{"name": "Legs and Core", "exercises": [
        "Squat", "Leg Press", "Calf Raise", "Crunch",
    ]}]
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=DEFAULT_PATH, help="JSON file to write")
    parser.add_argument("--force", action="store_true", help="back up and replace existing demo data")
    args = parser.parse_args()
    if args.path.exists():
        if not args.force:
            parser.error("The file already exists. Choose another path or use --force to back it up.")
        suffix = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        backup = args.path.with_name(f"{args.path.stem}.backup-{suffix}.json")
        copy2(args.path, backup)
        print(f"Backup saved to {backup}")
    DataStore(args.path).write(demo_data(datetime.now()))
    print(f"Demo profile and 44 sample workouts saved to {args.path}")


if __name__ == "__main__":
    main()
