"""Validate the profile and the numbers entered in the forms."""

from datetime import date, datetime
from math import isfinite

from .data import EXERCISES, PROMOTION_TESTS


def weight_value(value, minimum=0.01, maximum=1000):
    try:
        weight = float(value)
    except (ValueError, TypeError):
        raise ValueError("Enter a number for the weight.") from None
    if not isfinite(weight) or not minimum <= weight <= maximum:
        raise ValueError(f"Weight must be between {minimum:g} and {maximum:g} kg.")
    return weight


def integer_value(value, minimum, maximum, label):
    try:
        number = int(value)
    except (ValueError, TypeError):
        raise ValueError(f"Enter a whole number for {label}.") from None
    if not minimum <= number <= maximum:
        raise ValueError(f"{label} must be between {minimum} and {maximum}.")
    return number


def profile_from_form(form, now, workouts):
    name = form.get("name", "").strip()
    district = form.get("district", "").strip()
    if not name or not district or len(name) > 40 or len(district) > 40:
        raise ValueError("Enter a name and district of up to 40 characters each.")

    lifts = {}
    for exercise, _ in PROMOTION_TESTS.values():
        lifts[exercise] = weight_value(form.get(exercise) or "0", minimum=0)

    joined_at = now
    for workout in workouts:
        recorded_at = datetime.fromisoformat(workout["started_at"])
        joined_at = min(joined_at, recorded_at)

    return {
        "name": name, "district": district,
        "body_weight": weight_value(form.get("body_weight"), minimum=20, maximum=350),
        "lifts": lifts, "joined_at": joined_at.isoformat(),
    }


def selected_exercises(names):
    selected = []
    for name in names:
        if name not in EXERCISES:
            raise ValueError("Choose an exercise from the list.")
        if name not in selected:
            selected.append(name)
    if not selected:
        raise ValueError("Choose at least one exercise.")
    return selected


def workout_time(day_text, now):
    try:
        day = date.fromisoformat(day_text)
    except (ValueError, TypeError):
        raise ValueError("Enter a workout date.") from None
    if day > now.date():
        raise ValueError("Choose today or an earlier date.")
    return datetime.combine(day, now.time()).isoformat()
