from datetime import timedelta

import pytest

from goup.data import EXERCISES, MUSCLE_GROUPS, TIERS, test_weight as promotion_weight
from goup.engine import (
    TrainingState, apply_decay, consistency, ranked_group, ranking, recovery_factor, replay,
    weekly_factor, weekly_training,
)
from goup.seed import demo_data, exercise


def workout(now, name, weight, reps, count=1, identifier=1):
    return {"id": identifier, "started_at": now.isoformat(),
            "exercises": [exercise(name, weight, reps, count)]}


def test_catalog_covers_18_muscles_in_six_groups():
    muscles = set()
    for group in MUSCLE_GROUPS.values():
        muscles.update(group)
    assert len(MUSCLE_GROUPS) == 6
    assert len(muscles) == 18
    for credits in EXERCISES.values():
        assert credits.keys() <= muscles


@pytest.mark.parametrize("rank, expected", [(1, 35), (2, 52.5), (3, 67.5), (4, 87.5), (5, 102.5), (6, 120)])
def test_bench_test_matches_slide(rank, expected):
    assert promotion_weight(75, "Chest", rank) == expected


@pytest.mark.parametrize("weight, reps, expected", [
    (90, 3, "Silver"), (92.49, 3, "Silver"), (92.5, 2, "Silver"), (92.5, 3, "Gold"),
])
def test_squat_promotion_boundary(profile, now, weight, reps, expected):
    profile["lifts"]["Squat"] = 90
    state = replay(profile, [workout(now, "Squat", weight, reps)], now)
    assert TIERS[state.ranks["Legs"]] == expected


def test_signup_lifts_set_group_tiers_and_records(profile, now):
    profile["lifts"] = {"Bench Press": 52.5, "Squat": 90}
    state = replay(profile, [], now)
    assert state.stats["Mid chest"] == state.stats["Quads"] == 35
    assert state.stats["Abs"] == 0
    assert state.best_triples == profile["lifts"]


def test_growth_uses_main_helper_and_minor_weights(profile, now):
    state = replay(profile, [workout(now, "Bench Press", 30, 5)], now)
    assert state.stats["Mid chest"] == pytest.approx(0.11)
    assert state.stats["Triceps"] == pytest.approx(0.055)
    assert state.stats["Front delts"] == pytest.approx(0.0275)


@pytest.mark.parametrize("weight, reps, effective", [(36, 5, 1), (35.99, 5, 0), (36, 4, 0), (50, 5, 1)])
def test_effective_set_threshold(profile, now, weight, reps, effective):
    profile["lifts"]["Bench Press"] = 60
    state = replay(profile, [workout(now, "Bench Press", weight, reps)], now)
    assert state.results[1]["effective_sets"] == effective


@pytest.mark.parametrize("sets, factor", [(1, 1), (10, 1), (11, 0.3), (20, 0.3), (21, 0)])
def test_weekly_set_factors(sets, factor):
    assert weekly_factor(sets) == factor


@pytest.mark.parametrize("elapsed, window, expected", [(None, 48, 1), (0, 48, 0.3), (24, 48, 0.65), (48, 48, 1), (72, 72, 1)])
def test_recovery_factors(now, elapsed, window, expected):
    last = None if elapsed is None else now - timedelta(hours=elapsed)
    assert recovery_factor(last, now, window) == pytest.approx(expected)


def test_decay_waits_two_weeks_and_applies_each_week_once(profile, now):
    state = TrainingState(profile)
    state.stats["Quads"] = state.peaks["Quads"] = 50
    state.last_trained["Quads"] = now
    apply_decay(state, now + timedelta(days=14))
    assert state.stats["Quads"] == 50
    apply_decay(state, now + timedelta(days=21))
    assert state.stats["Quads"] == 49
    apply_decay(state, now + timedelta(days=22))
    assert state.stats["Quads"] == 49


def test_decay_has_an_eighty_percent_floor(profile, now):
    state = TrainingState(profile)
    state.stats["Quads"] = state.peaks["Quads"] = 50
    state.last_trained["Quads"] = now
    apply_decay(state, now + timedelta(weeks=99))
    assert state.stats["Quads"] == 40


def test_consistency_counts_unique_days_and_excludes_outside_dates(now):
    today = now.date()
    days = {today, today, today - timedelta(days=27), today - timedelta(days=28), today + timedelta(days=1)}
    assert consistency(days, today) == (2, 17)


def test_consistency_caps_at_hundred(now):
    days = {now.date() - timedelta(days=i) for i in range(13)}
    assert consistency(days, now.date()) == (13, 100)


def test_replay_orders_workouts_and_rebuilds_after_edit(profile, now):
    profile["lifts"]["Squat"] = 90
    first = workout(now - timedelta(days=1), "Squat", 75, 5)
    later = workout(now, "Squat", 92.5, 3, identifier=2)
    state = replay(profile, [later, first], now)
    assert list(state.results) == [1, 2]
    assert state.ranks["Legs"] == 3
    edited = workout(now, "Squat", 90, 3, identifier=2)
    assert replay(profile, [edited, first], now).ranks["Legs"] == 2


def test_weekly_sums_count_each_group_once_and_skip_future(now):
    past = workout(now, "Bench Press", 40, 8, 3)
    future = workout(now + timedelta(days=1), "Bench Press", 100, 5, identifier=2)
    weeks = weekly_training([past, future], now.date())
    assert len(weeks) == 4
    current = list(weeks.values())[-1]
    assert current["Chest"] == current["Arms"] == {"sets": 3, "volume": 960}
    assert current["Legs"] == {"sets": 0, "volume": 0}


def test_ranking_requires_four_training_weeks(profile, now):
    workouts = [workout(now - timedelta(weeks=index), "Squat", 55, 3, identifier=index)
                for index in range(4)]
    for count in (3, 4):
        state = replay(profile, workouts[:count], now)
        rows = ranking(state, "all", "stat", now.date())
        assert any(row.get("self") for row in rows) == (count == 4)


def test_ranking_supports_district_tier_and_consistency_filters(now):
    data = demo_data(now)
    state = replay(data["profile"], data["workouts"], now)
    district = ranking(state, "district", "stat", now.date())
    assert all(row["district"] == "Mapo-gu" for row in district)
    assert district[7]["self"]
    same_tier = ranking(state, "tier", "consistency", now.date())
    assert all(row["tier"] == state.overall_tier() for row in same_tier)
    scores = [row["consistency"] for row in same_tier]
    assert scores == sorted(scores, reverse=True)


def test_presentation_fixture_has_44_workouts_and_a_silver_to_gold_demo(now):
    data = demo_data(now)
    assert len(data["workouts"]) == 44
    before = replay(data["profile"], data["workouts"], now)
    assert ranked_group(before, "Legs") == "Silver II"
    assert round(before.group_stat("Legs"), 1) == 40.8
    new = {"id": 45, "started_at": now.isoformat(), "exercises": [
        exercise("Squat", 92.5, 3, 1), exercise("Squat", 75, 5, 2), exercise("Calf Raise", 40, 8, 1),
    ]}
    after = replay(data["profile"], data["workouts"] + [new], now)
    assert after.results[45]["effective_sets"] == 3
    assert ranked_group(after, "Legs") == "Gold III"
    assert round(after.group_stat("Legs"), 1) == 50.1
