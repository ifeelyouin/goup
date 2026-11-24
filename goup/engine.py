"""Rebuild GoUp's game stats from sign-up lifts and completed workout records."""

from datetime import datetime, timedelta

from .data import (
    EXERCISES, MUSCLE_GROUPS, PROMOTION_TESTS, SAMPLE_LIFTERS, TIER_STARTS, TIERS,
    starting_tier, test_weight,
)


class TrainingState:
    def __init__(self, profile):
        self.profile = profile
        self.stats = {}
        self.ranks = {}
        self.muscle_groups = {}
        self.peaks = {}
        self.last_trained = {}
        self.decay_weeks = {}
        self.weekly_sets = {}
        self.best_weights = {}
        self.best_triples = {}
        self.days = set()
        self.history = []
        self.results = {}

        for group, muscles in MUSCLE_GROUPS.items():
            rank = 0
            if group in PROMOTION_TESTS:
                exercise, _ = PROMOTION_TESTS[group]
                lift = profile["lifts"].get(exercise, 0)
                rank = starting_tier(profile["body_weight"], group, lift)
                if lift > 0:
                    self.best_weights[exercise] = lift
                    self.best_triples[exercise] = lift
            self.ranks[group] = rank
            for muscle in muscles:
                self.stats[muscle] = float(TIER_STARTS[rank])
                self.peaks[muscle] = self.stats[muscle]
                self.muscle_groups[muscle] = group

    def group_stat(self, group):
        muscles = MUSCLE_GROUPS[group]
        return sum(self.stats[muscle] for muscle in muscles) / len(muscles)

    def overall_stat(self):
        return sum(self.stats.values()) / len(self.stats)

    def overall_tier(self):
        return TIERS[rank_from_stat(self.overall_stat())]


def week_start(day):
    return day - timedelta(days=day.weekday())


def rank_from_stat(stat):
    rank = 0
    for index, start in enumerate(TIER_STARTS):
        if stat >= start:
            rank = index
    return rank


def ranked_group(state, group):
    stat = state.group_stat(group)
    rank = state.ranks[group]
    if group == "Core":
        rank = rank_from_stat(stat)

    band_end = 100
    if rank < len(TIERS) - 1:
        band_end = TIER_STARTS[rank + 1]
    step = (band_end - TIER_STARTS[rank]) / 3
    division = "III"
    if stat >= TIER_STARTS[rank] + 2 * step:
        division = "I"
    elif stat >= TIER_STARTS[rank] + step:
        division = "II"
    return f"{TIERS[rank]} {division}"


def consistency(days, today):
    first_day = today - timedelta(days=27)
    active_days = 0
    for day in days:
        if first_day <= day <= today:
            active_days += 1
    return active_days, min(100, round(active_days / 12 * 100))


def recovery_factor(last_trained, when, hours):
    if last_trained is None:
        return 1.0
    elapsed = max(0, (when - last_trained).total_seconds() / 3600)
    return 0.3 + 0.7 * min(1, elapsed / hours)


def weekly_factor(set_number):
    if set_number <= 10:
        return 1.0
    if set_number <= 20:
        return 0.3
    return 0.0


def apply_decay(state, when):
    for muscle, last in state.last_trained.items():
        inactive_days = (when - last).days
        weeks = max(0, (inactive_days - 14) // 7)
        applied = state.decay_weeks.get(muscle, 0)
        if weeks > applied:
            decayed = state.stats[muscle] * 0.98 ** (weeks - applied)
            state.stats[muscle] = max(state.peaks[muscle] * 0.8, decayed)
            state.decay_weeks[muscle] = weeks


def next_test(state, group):
    if group not in PROMOTION_TESTS or state.ranks[group] == len(TIERS) - 1:
        return None
    rank = state.ranks[group] + 1
    exercise, _ = PROMOTION_TESTS[group]
    return {
        "group": group, "exercise": exercise, "tier": TIERS[rank],
        "load": test_weight(state.profile["body_weight"], group, rank),
    }


def try_promotion(state, exercise, weight, reps):
    if reps < 3:
        return None
    for group, rule in PROMOTION_TESTS.items():
        if rule[0] != exercise:
            continue
        old_rank = state.ranks[group]
        new_rank = starting_tier(state.profile["body_weight"], group, weight)
        if new_rank > old_rank:
            state.ranks[group] = new_rank
            for muscle in MUSCLE_GROUPS[group]:
                state.stats[muscle] = max(state.stats[muscle], TIER_STARTS[new_rank])
                state.peaks[muscle] = max(state.peaks[muscle], state.stats[muscle])
            return {"group": group, "from": TIERS[old_rank], "to": TIERS[new_rank]}
    return None


def add_growth(state, exercise, when, bonus, trained_muscles):
    start = week_start(when.date())
    week = state.weekly_sets.setdefault(start, {})
    joined = datetime.fromisoformat(state.profile["joined_at"])
    training_years = max(0, (when - joined).days // 365)
    speed = 1.0
    age = 0.5 ** training_years
    for muscle, stimulus in EXERCISES[exercise].items():
        group = state.muscle_groups[muscle]
        week[muscle] = week.get(muscle, 0) + 1
        weekly = weekly_factor(week[muscle])
        if weekly == 0:
            continue
        hours = 72 if group in ("Back", "Legs") else 48
        recovery = recovery_factor(state.last_trained.get(muscle), when, hours)
        stat = state.stats[muscle]
        gain = (100 - stat) * 0.0011 * stimulus * speed * age * recovery * weekly * (1 + bonus)
        limit = 100.0
        next_rank = state.ranks[group] + 1
        if group in PROMOTION_TESTS and next_rank < len(TIERS):
            limit = TIER_STARTS[next_rank] - 0.1
        state.stats[muscle] = min(limit, stat + gain)
        state.peaks[muscle] = max(state.peaks[muscle], state.stats[muscle])
        trained_muscles.add(muscle)


def apply_workout(state, workout):
    when = datetime.fromisoformat(workout["started_at"])
    apply_decay(state, when)
    _, score = consistency(state.days, when.date())
    bonus = score / 500
    before = state.stats.copy()
    result = {
        "date": when, "promotions": [], "records": [], "statuses": [],
        "effective_sets": 0, "bonus": bonus,
    }
    trained_muscles = set()

    for entry in workout["exercises"]:
        exercise = entry["name"]
        labels = []
        for lift in entry["sets"]:
            weight = lift["weight"]
            reps = lift["reps"]
            best = max(weight, state.best_weights.get(exercise, 0))
            state.best_weights[exercise] = best
            record = reps >= 3 and weight > state.best_triples.get(exercise, 0)
            if record:
                state.best_triples[exercise] = weight
                result["records"].append({"exercise": exercise, "weight": weight, "reps": reps})

            promotion = try_promotion(state, exercise, weight, reps)
            if promotion:
                result["promotions"].append(promotion)
                trained_muscles.update(MUSCLE_GROUPS[promotion["group"]])

            effective = reps >= 5 and weight >= 0.6 * best
            if effective:
                result["effective_sets"] += 1
                add_growth(state, exercise, when, bonus, trained_muscles)

            label = "Too light"
            if effective:
                label = "Counts"
            if record:
                label = "Record"
            if promotion:
                label = "Passed"
            labels.append(label)
        result["statuses"].append(labels)

    for muscle in trained_muscles:
        state.last_trained[muscle] = when
        state.decay_weeks[muscle] = 0
    state.days.add(when.date())

    result["overall"] = state.overall_stat()
    result["change"] = result["overall"] - sum(before.values()) / len(before)
    result["before"] = before
    result["after"] = state.stats.copy()
    result["groups"] = {group: ranked_group(state, group) for group in MUSCLE_GROUPS}
    return result


def replay(profile, workouts, now=None):
    if now is None:
        now = datetime.now()
    state = TrainingState(profile)
    ordered = sorted(workouts, key=lambda row: (row["started_at"], row["id"]))
    for workout in ordered:
        when = datetime.fromisoformat(workout["started_at"])
        if when > now:
            continue
        result = apply_workout(state, workout)
        state.results[workout["id"]] = result
        groups = {group: state.group_stat(group) for group in MUSCLE_GROUPS}
        state.history.append((when.date(), groups))
    apply_decay(state, now)
    return state


def weekly_training(workouts, today):
    weeks = {}
    current = week_start(today)
    for offset in range(3, -1, -1):
        monday = current - timedelta(weeks=offset)
        weeks[monday] = {group: {"sets": 0, "volume": 0.0} for group in MUSCLE_GROUPS}
    for workout in workouts:
        day = datetime.fromisoformat(workout["started_at"]).date()
        monday = week_start(day)
        if day > today or monday not in weeks:
            continue
        for entry in workout["exercises"]:
            groups = set()
            for group, muscles in MUSCLE_GROUPS.items():
                for muscle in muscles:
                    if muscle in EXERCISES[entry["name"]]:
                        groups.add(group)
            for group in groups:
                totals = weeks[monday][group]
                for lift in entry["sets"]:
                    totals["sets"] += 1
                    totals["volume"] += lift["weight"] * lift["reps"]
    return weeks


def ranking(state, scope, metric, today):
    weeks = {week_start(day) for day in state.days}
    rows = [dict(lifter) for lifter in SAMPLE_LIFTERS]
    if len(weeks) >= 4:
        _, score = consistency(state.days, today)
        rows.append({
            "name": state.profile["name"], "district": state.profile["district"],
            "tier": state.overall_tier(), "stat": state.overall_stat(),
            "consistency": score, "self": True,
        })
    if scope == "district":
        district = state.profile["district"]
        rows = [row for row in rows if row["district"] == district]
    if scope == "tier":
        tier = state.overall_tier()
        rows = [row for row in rows if row["tier"] == tier]
    rows.sort(key=lambda row: (-row[metric], row["name"].casefold()))
    return rows
