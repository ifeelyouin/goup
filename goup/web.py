"""Flask pages for planning, logging, and reviewing workouts."""

import csv
from datetime import datetime, timedelta
from io import StringIO
from json import JSONDecodeError
from math import ceil
from secrets import token_hex
import sqlite3

from flask import Flask, abort, flash, g, redirect, render_template, request, send_file, url_for

from .charts import chart_image
from .data import EXERCISES, EXERCISES_BY_GROUP, MUSCLE_GROUPS, PROMOTION_TESTS
from .engine import (
    consistency, next_test, ranked_group, ranking, recovery_factor, replay, weekly_training,
)
from .models import integer_value, profile_from_form, selected_exercises, weight_value, workout_time
from .storage import DEFAULT_PATH, DataStore, empty_data


def exercise_plan(name, workouts, started_at):
    for workout in sorted(workouts, key=lambda row: (row["started_at"], row["id"]), reverse=True):
        if workout["started_at"] > started_at:
            continue
        for entry in workout["exercises"]:
            if entry["name"] == name:
                sets = [dict(lift, checked=False) for lift in entry["sets"]]
                return {"name": name, "rest_seconds": entry["rest_seconds"], "sets": sets}
    return {
        "name": name, "rest_seconds": 120,
        "sets": [{"weight": 20, "reps": 8, "checked": False} for _ in range(3)],
    }


def next_workout_id(workouts):
    return max((workout["id"] for workout in workouts), default=0) + 1


def saved_workout(draft, identifier):
    exercises = []
    for entry in draft["exercises"]:
        sets = []
        for lift in entry["sets"]:
            if lift["checked"]:
                sets.append({"weight": lift["weight"], "reps": lift["reps"]})
        if sets:
            exercises.append({"name": entry["name"], "rest_seconds": entry["rest_seconds"], "sets": sets})
    return {"id": identifier, "started_at": draft["started_at"], "exercises": exercises}


def read_set_inputs(draft, form):
    for exercise_index, entry in enumerate(draft["exercises"]):
        rest = form.get(f"rest_{exercise_index}", entry["rest_seconds"])
        entry["rest_seconds"] = integer_value(rest, 0, 3600, "rest seconds")
        for set_index, lift in enumerate(entry["sets"]):
            suffix = f"{exercise_index}_{set_index}"
            lift["weight"] = weight_value(form.get(f"weight_{suffix}", lift["weight"]))
            reps = form.get(f"reps_{suffix}", lift["reps"])
            lift["reps"] = integer_value(reps, 1, 500, "reps")


def set_feedback(data, draft, now):
    identifier = draft.get("edit_id") or next_workout_id(data["workouts"])
    pending = saved_workout(draft, identifier)
    if not pending["exercises"]:
        return {}

    workouts = [workout for workout in data["workouts"] if workout["id"] != identifier]
    state = replay(data["profile"], workouts + [pending], now)
    outcomes = iter(state.results[identifier]["statuses"])
    feedback = {}
    for exercise_index, entry in enumerate(draft["exercises"]):
        checked = [index for index, lift in enumerate(entry["sets"]) if lift["checked"]]
        if checked:
            for set_index, label in zip(checked, next(outcomes)):
                feedback[(exercise_index, set_index)] = label
    return feedback


def create_app(data_path=DEFAULT_PATH, clock=datetime.now):
    app = Flask(__name__)
    app.secret_key = token_hex(32)
    store = DataStore(data_path)

    @app.before_request
    def load_workouts():
        if request.endpoint in (None, "static"):
            return None
        g.data = store.read()
        g.now = clock()
        if g.data["profile"] is None and request.endpoint not in ("home", "signup", "reset"):
            return redirect(url_for("signup"))
        return None

    @app.errorhandler(OSError)
    @app.errorhandler(sqlite3.Error)
    @app.errorhandler(JSONDecodeError)
    def storage_error(error):
        app.logger.error("Could not read or save workout data: %s", error)
        return render_template("error.html"), 500

    @app.get("/")
    def home():
        data = g.data
        profile = data["profile"]
        if profile is None:
            return render_template("home.html", profile=None)
        state = replay(profile, data["workouts"], g.now)
        days, score = consistency(state.days, g.now.date())
        tests = []
        groups = []
        for group, muscles in MUSCLE_GROUPS.items():
            hours = 72 if group in ("Back", "Legs") else 48
            recovery = min(recovery_factor(state.last_trained.get(muscle), g.now, hours) for muscle in muscles)
            groups.append({"name": group, "stat": state.group_stat(group),
                           "tier": ranked_group(state, group), "recovery": recovery})
            test = next_test(state, group)
            if test:
                test["best"] = state.best_triples.get(test["exercise"], 0)
                tests.append(test)
        tests.sort(key=lambda test: test["load"] - test["best"])
        records = sorted(data["workouts"], key=lambda row: (row["started_at"], row["id"]), reverse=True)
        return render_template("home.html", profile=profile, state=state, days=days, score=score,
                               tests=tests, groups=groups, workouts=records,
                               active=data["active_workout"] is not None,
                               reset_error=request.args.get("reset_error") == "1")

    @app.route("/signup", methods=["GET", "POST"])
    def signup():
        if g.data["profile"] is not None:
            return redirect(url_for("home"))
        if request.method == "POST":
            try:
                with store.edit() as data:
                    if data["profile"] is None:
                        data["profile"] = profile_from_form(request.form, g.now, data["workouts"])
                return redirect(url_for("home"))
            except ValueError as error:
                flash(str(error))
        return render_template("signup.html", tests=PROMOTION_TESTS, values=request.form)

    @app.route("/plan", methods=["GET", "POST"])
    def plan():
        if g.data["active_workout"] is not None:
            return redirect(url_for("workout"))
        if request.method == "POST":
            try:
                action = request.form.get("action", "start")
                with store.edit() as data:
                    if data["active_workout"] is not None:
                        return redirect(url_for("workout"))
                    if action.startswith("routine:"):
                        index = integer_value(action.split(":")[1], 0, len(data["routines"]) - 1, "routine")
                        names = data["routines"][index]["exercises"]
                    else:
                        names = selected_exercises(request.form.getlist("exercises"))
                        for group in request.form.getlist("groups"):
                            exercises = EXERCISES_BY_GROUP.get(group, ())
                            if not any(name in exercises for name in names):
                                raise ValueError(f"Choose at least one exercise for {group}.")
                    if action == "save":
                        name = request.form.get("routine_name", "").strip()
                        if not name or len(name) > 40:
                            raise ValueError("Enter a routine name of up to 40 characters.")
                        if any(routine["name"].casefold() == name.casefold() for routine in data["routines"]):
                            raise ValueError("A routine with that name already exists.")
                        data["routines"].append({"name": name, "exercises": names})
                        flash("Routine saved.")
                        return redirect(url_for("plan"))
                    started = workout_time(request.form.get("day"), g.now)
                    data["active_workout"] = {
                        "started_at": started, "current": 0, "rest_until": None,
                        "exercises": [exercise_plan(name, data["workouts"], started) for name in names],
                    }
                return redirect(url_for("workout"))
            except ValueError as error:
                flash(str(error))
        return render_template("plan.html", catalog=EXERCISES_BY_GROUP,
                               routines=g.data["routines"], today=g.now.date().isoformat())

    @app.get("/workout")
    def workout():
        draft = g.data["active_workout"]
        if draft is None:
            return redirect(url_for("plan"))
        rest = 0
        rest_until_ms = None
        if draft["rest_until"]:
            end = datetime.fromisoformat(draft["rest_until"])
            rest = max(0, ceil((end - g.now).total_seconds()))
            rest_until_ms = int(end.timestamp() * 1000)
        identifier = draft.get("edit_id") or next_workout_id(g.data["workouts"])
        draft_order = (draft["started_at"], identifier)
        previous = [row for row in g.data["workouts"] if (row["started_at"], row["id"]) < draft_order]
        state = replay(g.data["profile"], previous, g.now)
        tests = {}
        for group in PROMOTION_TESTS:
            test = next_test(state, group)
            if test:
                test["best"] = state.best_triples.get(test["exercise"], 0)
                tests[test["exercise"]] = test
        return render_template("workout.html", draft=draft, rest=rest, rest_until_ms=rest_until_ms,
                               catalog=EXERCISES_BY_GROUP, tests=tests,
                               feedback=set_feedback(g.data, draft, g.now),
                               available=[name for name in EXERCISES if name not in {
                                   entry["name"] for entry in draft["exercises"]
                               }])

    @app.post("/workout")
    def workout_action():
        parts = request.form.get("action", "").split(":")
        action = parts[0]
        try:
            with store.edit() as data:
                draft = data["active_workout"]
                if draft is None:
                    return redirect(url_for("plan"))
                if action == "cancel":
                    data["active_workout"] = None
                    flash("Workout draft cancelled.")
                    return redirect(url_for("home"))

                read_set_inputs(draft, request.form)
                entries = draft["exercises"]
                if action == "finish":
                    identifier = draft.get("edit_id") or next_workout_id(data["workouts"])
                    record = saved_workout(draft, identifier)
                    if not record["exercises"]:
                        raise ValueError("Check off at least one set before saving.")
                    data["workouts"] = [row for row in data["workouts"] if row["id"] != identifier]
                    data["workouts"].append(record)
                    data["active_workout"] = None
                    return redirect(url_for("result", identifier=identifier))
                if action == "add_exercise":
                    name = request.form.get("new_exercise")
                    if name not in EXERCISES or any(entry["name"] == name for entry in entries):
                        raise ValueError("Choose an exercise that is not already in this workout.")
                    entries.append(exercise_plan(name, data["workouts"], draft["started_at"]))
                    draft["current"] = len(entries) - 1
                    return redirect(url_for("workout"))

                index = integer_value(parts[1] if len(parts) > 1 else None, 0, len(entries) - 1, "exercise")
                sets = entries[index]["sets"]
                draft["current"] = index
                if action in ("check", "uncheck"):
                    set_index = integer_value(parts[2] if len(parts) > 2 else None, 0, len(sets) - 1, "set")
                    lift = sets[set_index]
                    if action == "check" and not lift["checked"]:
                        rest_seconds = entries[index]["rest_seconds"]
                        draft["rest_until"] = None
                        if rest_seconds > 0:
                            end = g.now + timedelta(seconds=rest_seconds)
                            draft["rest_until"] = end.isoformat()
                    lift["checked"] = action == "check"
                elif action == "add_set":
                    sets.append(dict(sets[-1], checked=False))
                elif action == "remove_set" and len(sets) > 1:
                    sets.pop()
                elif action == "move_up" and index > 0:
                    entries[index - 1], entries[index] = entries[index], entries[index - 1]
                    draft["current"] = index - 1
                elif action == "move_down" and index + 1 < len(entries):
                    entries[index + 1], entries[index] = entries[index], entries[index + 1]
                    draft["current"] = index + 1
                elif action == "next":
                    draft["current"] = min(index + 1, len(entries) - 1)
        except ValueError as error:
            flash(str(error))
        return redirect(url_for("workout"))

    @app.post("/workouts/<int:identifier>/edit")
    def edit_workout(identifier):
        with store.edit() as data:
            if data["active_workout"] is not None:
                flash("Finish or cancel the active workout first.")
                return redirect(url_for("workout"))
            original = next((row for row in data["workouts"] if row["id"] == identifier), None)
            if original is None:
                abort(404)
            entries = []
            for entry in original["exercises"]:
                sets = [dict(lift, checked=True) for lift in entry["sets"]]
                entries.append(dict(entry, sets=sets))
            data["active_workout"] = {
                "edit_id": identifier, "started_at": original["started_at"],
                "current": 0, "rest_until": None, "exercises": entries,
            }
        return redirect(url_for("workout"))

    @app.get("/workouts/<int:identifier>/result")
    def result(identifier):
        state = replay(g.data["profile"], g.data["workouts"], g.now)
        outcome = state.results.get(identifier)
        if outcome is None:
            abort(404)
        groups = []
        for group, muscles in MUSCLE_GROUPS.items():
            changes = []
            for muscle in muscles:
                before, after = outcome["before"][muscle], outcome["after"][muscle]
                if before != after:
                    changes.append({"name": muscle, "before": before, "after": after})
            if changes:
                groups.append({
                    "name": group, "tier": outcome["groups"][group], "changes": changes,
                    "before": sum(outcome["before"][muscle] for muscle in muscles) / len(muscles),
                    "after": sum(outcome["after"][muscle] for muscle in muscles) / len(muscles),
                })
        return render_template("result.html", outcome=outcome, groups=groups, identifier=identifier)

    @app.get("/stats")
    def stats():
        metric = request.args.get("metric", "sets")
        if metric not in ("sets", "volume"):
            abort(404)
        data = g.data
        state = replay(data["profile"], data["workouts"], g.now)
        weeks = weekly_training(data["workouts"], g.now.date())
        dates = list(weeks)
        previous, latest = dates[-3], dates[-2]
        comparison = []
        for group in MUSCLE_GROUPS:
            older = weeks[previous][group]["volume"]
            newer = weeks[latest][group]["volume"]
            change = "No baseline yet"
            if older > 0:
                change = f"{(newer - older) / older * 100:+.1f}%"
            comparison.append((group, older, newer, change))
        return render_template("stats.html", state=state, metric=metric, previous=previous,
                               latest=latest, comparison=comparison, groups=MUSCLE_GROUPS)

    @app.get("/charts/<metric>.png")
    def chart(metric):
        if metric not in ("history", "sets", "volume"):
            abort(404)
        data = g.data
        state = replay(data["profile"], data["workouts"], g.now)
        image = chart_image(state, data["workouts"], g.now.date(), metric)
        return send_file(image, mimetype="image/png", max_age=0)

    @app.get("/ranking")
    def ranks():
        scope = request.args.get("scope", "district")
        metric = request.args.get("metric", "stat")
        if scope not in ("district", "all", "tier") or metric not in ("stat", "consistency"):
            abort(404)
        state = replay(g.data["profile"], g.data["workouts"], g.now)
        rows = ranking(state, scope, metric, g.now.date())
        return render_template("ranking.html", rows=rows, scope=scope, metric=metric,
                               district=g.data["profile"]["district"])

    @app.get("/workouts.csv")
    def export():
        output = StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(["workout_id", "started_at", "exercise", "set", "weight_kg", "reps"])
        for record in sorted(g.data["workouts"], key=lambda row: (row["started_at"], row["id"])):
            for entry in record["exercises"]:
                for index, lift in enumerate(entry["sets"], start=1):
                    writer.writerow([record["id"], record["started_at"], entry["name"],
                                     index, lift["weight"], lift["reps"]])
        return app.response_class(output.getvalue(), mimetype="text/csv", headers={
            "Content-Disposition": 'attachment; filename="goup-workouts.csv"',
        })

    @app.post("/reset")
    def reset():
        confirmation = request.form.get("confirm", "").strip().upper()
        if confirmation != "RESET":
            return redirect(url_for("home", reset_error="1", _anchor="reset-local-data"))
        store.write(empty_data())
        flash("Local data reset.")
        return redirect(url_for("signup"))

    return app
