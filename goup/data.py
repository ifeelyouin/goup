"""Exercise catalog and game rules used by the presentation build."""

from math import ceil


MUSCLE_GROUPS = {
    "Chest": ("Upper chest", "Mid chest", "Lower chest"),
    "Shoulders": ("Front delts", "Side delts", "Rear delts"),
    "Arms": ("Biceps", "Triceps", "Forearms"),
    "Back": ("Lats", "Upper back", "Lower back"),
    "Core": ("Abs", "Obliques"),
    "Legs": ("Quads", "Hamstrings", "Glutes", "Calves"),
}

EXERCISES_BY_GROUP = {
    "Chest": ("Bench Press", "Incline Press", "Push-up"),
    "Shoulders": ("Overhead Press", "Lateral Raise"),
    "Arms": ("Barbell Curl", "Triceps Extension"),
    "Back": ("Pull-up", "Barbell Row", "Deadlift"),
    "Core": ("Crunch", "Side Bend"),
    "Legs": ("Squat", "Leg Press", "Leg Curl", "Calf Raise"),
}

# Each value is the exercise's relative credit for one muscle.
EXERCISES = {
    "Bench Press": {"Mid chest": 1.0, "Upper chest": 0.5, "Lower chest": 0.25,
                    "Triceps": 0.5, "Front delts": 0.25},
    "Incline Press": {"Upper chest": 1.0, "Mid chest": 0.5, "Front delts": 0.5, "Triceps": 0.25},
    "Push-up": {"Lower chest": 1.0, "Mid chest": 0.5, "Triceps": 0.5, "Front delts": 0.25},
    "Overhead Press": {"Front delts": 1.0, "Side delts": 0.5, "Triceps": 0.5},
    "Lateral Raise": {"Side delts": 1.0, "Rear delts": 0.25},
    "Barbell Curl": {"Biceps": 1.0, "Forearms": 0.5},
    "Triceps Extension": {"Triceps": 1.0},
    "Pull-up": {"Lats": 1.0, "Upper back": 0.5, "Biceps": 0.5, "Forearms": 0.25},
    "Barbell Row": {"Upper back": 1.0, "Lats": 0.5, "Rear delts": 0.5, "Biceps": 0.25},
    "Deadlift": {"Lower back": 1.0, "Glutes": 1.0, "Hamstrings": 0.5, "Forearms": 0.25},
    "Crunch": {"Abs": 1.0, "Obliques": 0.25},
    "Side Bend": {"Obliques": 1.0, "Abs": 0.25},
    "Squat": {"Quads": 1.0, "Glutes": 0.5, "Hamstrings": 0.25, "Lower back": 0.25},
    "Leg Press": {"Quads": 1.0, "Glutes": 0.5},
    "Leg Curl": {"Hamstrings": 1.0},
    "Calf Raise": {"Calves": 1.0},
}

TIERS = ("Iron", "Bronze", "Silver", "Gold", "Platinum", "Diamond", "Master")
TIER_STARTS = (0, 20, 35, 50, 65, 80, 95)
BODY_WEIGHT_RATIOS = (0, 0.45, 0.70, 0.90, 1.15, 1.35, 1.60)
PROMOTION_TESTS = {
    "Chest": ("Bench Press", 1.0),
    "Shoulders": ("Overhead Press", 0.65),
    "Arms": ("Barbell Curl", 0.40),
    "Back": ("Pull-up", 1.20),
    "Legs": ("Squat", 1.35),
}


def test_weight(body_weight, group, tier_index):
    """Round the test load up to the next 2.5 kg increment."""
    _, multiplier = PROMOTION_TESTS[group]
    load = body_weight * BODY_WEIGHT_RATIOS[tier_index] * multiplier
    # Ignore tiny floating-point errors at exact plate increments.
    return ceil(round(load / 2.5, 10)) * 2.5


def starting_tier(body_weight, group, lift):
    tier_index = 0
    for index in range(1, len(TIERS)):
        if lift < test_weight(body_weight, group, index):
            break
        tier_index = index
    return tier_index


SAMPLE_LIFTERS = (
    {"name": "Jiho", "district": "Mapo-gu", "tier": "Gold", "stat": 64.5, "consistency": 92},
    {"name": "Seojun", "district": "Mapo-gu", "tier": "Gold", "stat": 60.1, "consistency": 88},
    {"name": "Minseo", "district": "Mapo-gu", "tier": "Gold", "stat": 57.2, "consistency": 84},
    {"name": "Eunji", "district": "Mapo-gu", "tier": "Gold", "stat": 51.8, "consistency": 83},
    {"name": "Nari", "district": "Mapo-gu", "tier": "Silver", "stat": 49.1, "consistency": 75},
    {"name": "Kai", "district": "Mapo-gu", "tier": "Silver", "stat": 45.1, "consistency": 71},
    {"name": "Mason", "district": "Mapo-gu", "tier": "Silver", "stat": 43.0, "consistency": 67},
    {"name": "Sora", "district": "Mapo-gu", "tier": "Bronze", "stat": 31.8, "consistency": 62},
    {"name": "Yuna", "district": "Mapo-gu", "tier": "Bronze", "stat": 30.4, "consistency": 58},
    {"name": "Hana", "district": "Seongbuk-gu", "tier": "Silver", "stat": 39.5, "consistency": 75},
    {"name": "Alex", "district": "Seongbuk-gu", "tier": "Bronze", "stat": 30.2, "consistency": 50},
)
