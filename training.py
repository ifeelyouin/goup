from dataclasses import dataclass
from datetime import date, timedelta
from math import isfinite


@dataclass(frozen=True)
class Exercise:
    muscles: tuple[str, ...]
    promotion_weights: tuple[int, ...]


# Tier thresholds are game rules chosen for the demo.
EXERCISES = {
    "Bench Press": Exercise(("Chest", "Triceps"), (40, 60, 80, 100)),
    "Squat": Exercise(("Quadriceps", "Glutes"), (50, 80, 110, 140)),
    "Deadlift": Exercise(("Hamstrings", "Glutes", "Back"), (60, 100, 130, 160)),
}
MUSCLES: list[str] = []
for exercise in EXERCISES.values():
    for muscle in exercise.muscles:
        if muscle not in MUSCLES:
            MUSCLES.append(muscle)

TIER_NAMES = ("Iron", "Bronze", "Silver", "Gold", "Master")
CONSISTENCY_DAYS = 28
CONSISTENCY_GOAL = 12


@dataclass(frozen=True)
class Workout:
    day: date
    exercise: str
    weight_kg: float
    reps: int
    sets: int

    def __post_init__(self) -> None:
        if self.exercise not in EXERCISES:
            raise ValueError("Choose an exercise from the list.")
        if not isfinite(self.weight_kg) or self.weight_kg <= 0:
            raise ValueError("Weight must be greater than zero.")
        if self.reps <= 0 or self.sets <= 0:
            raise ValueError("Enter at least one rep and one set.")

    @property
    def volume(self) -> float:
        return self.weight_kg * self.reps * self.sets


@dataclass
class MuscleTraining:
    sets: int = 0
    volume: float = 0.0


@dataclass
class TrainingWeek:
    start: date
    muscles: dict[str, MuscleTraining]


def week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def weekly_training(workouts: list[Workout], today: date) -> list[TrainingWeek]:
    current_week = week_start(today)
    weeks = {}

    # Start with four weeks of zero totals so the chart also shows weeks without workouts.
    for weeks_ago in range(3, -1, -1):
        start = current_week - timedelta(weeks=weeks_ago)
        muscle_totals = {}
        for muscle in MUSCLES:
            muscle_totals[muscle] = MuscleTraining()
        weeks[start] = TrainingWeek(start, muscle_totals)

    for workout in workouts:
        week = weeks.get(week_start(workout.day))
        if week is None or workout.day > today:
            continue

        volume = workout.volume
        for muscle in EXERCISES[workout.exercise].muscles:
            training = week.muscles[muscle]
            training.sets += workout.sets
            training.volume += volume

    return list(weeks.values())


@dataclass(frozen=True)
class TierProgress:
    name: str
    best_weight: float | None
    next_weight: int | None


def exercise_tiers(workouts: list[Workout]) -> dict[str, TierProgress]:
    best_weights: dict[str, float] = {}
    for workout in workouts:
        previous = best_weights.get(workout.exercise, 0)
        best_weights[workout.exercise] = max(previous, workout.weight_kg)

    tiers = {}
    for name, exercise in EXERCISES.items():
        best_weight = best_weights.get(name)
        tier_index = 0
        next_weight = None

        # Each threshold reached moves the exercise up one tier.
        for threshold in exercise.promotion_weights:
            if best_weight is None or best_weight < threshold:
                next_weight = threshold
                break
            tier_index += 1

        tiers[name] = TierProgress(TIER_NAMES[tier_index], best_weight, next_weight)
    return tiers


@dataclass(frozen=True)
class Consistency:
    active_days: int

    @property
    def score(self) -> int:
        percentage = 100 * self.active_days / CONSISTENCY_GOAL
        return min(100, round(percentage))


def consistency(workouts: list[Workout], today: date) -> Consistency:
    first_day = today - timedelta(days=CONSISTENCY_DAYS - 1)
    days = set()
    for workout in workouts:
        if first_day <= workout.day <= today:
            days.add(workout.day)

    return Consistency(len(days))
