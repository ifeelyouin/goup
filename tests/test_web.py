import csv
from datetime import timedelta
from io import StringIO

from goup.seed import demo_data
from goup.storage import DataStore, empty_data
from goup.web import create_app


def signup(client):
    return client.post("/signup", data={
        "name": "Student", "district": "Mapo-gu", "body_weight": "75", "Squat": "90",
    }, follow_redirects=True)


def begin(client, now, exercises):
    return client.post("/plan", data={"day": now.date().isoformat(), "exercises": exercises},
                       follow_redirects=True)


def test_signup_sets_a_starting_tier(client):
    assert client.get("/stats").location.endswith("/signup")
    invalid = client.post("/signup", data={"name": "Student", "district": "Mapo-gu", "body_weight": "bad"})
    assert b"Enter a number for the weight" in invalid.data
    response = signup(client)
    assert "Squat 92.5 kg × 3" in response.text
    assert "Silver III" in response.text


def test_plan_requires_an_exercise_for_every_chosen_group(client, now):
    signup(client)
    response = client.post("/plan", data={
        "day": now.date().isoformat(), "groups": ["Legs", "Core"], "exercises": ["Squat"],
    })
    assert "Choose at least one exercise for Core." in response.text
    assert client.get("/workout").location.endswith("/plan")


def test_saved_routine_and_previous_sets_are_reused(client, now):
    signup(client)
    day = now.date().isoformat()
    start = begin(client, now, ["Squat"])
    assert "Squat" in start.text
    client.post("/workout", data={"action": "check:0:0", "weight_0_0": "75", "reps_0_0": "5"})
    client.post("/workout", data={"action": "finish"})
    client.post("/plan", data={
        "day": day, "exercise": "Squat", "exercises": ["Squat"],
        "action": "save", "routine_name": "Leg Day",
    })
    assert "Leg Day" in client.get("/plan").text
    response = client.post("/plan", data={"day": day, "action": "routine:0"}, follow_redirects=True)
    assert 'name="weight_0_0" value="75.0"' in response.text
    assert 'name="reps_0_0" value="5"' in response.text


def test_workout_controls_add_reorder_uncheck_and_cancel(client, now):
    signup(client)
    begin(client, now, ["Squat", "Crunch"])
    client.post("/workout", data={"action": "add_exercise", "new_exercise": "Leg Press"})
    client.post("/workout", data={"action": "move_up:2"})
    response = client.post("/workout", data={"action": "add_set:1"}, follow_redirects=True)
    assert 'name="weight_1_3"' in response.text
    assert response.text.index("2. Leg Press") < response.text.index("3. Crunch")
    client.post("/workout", data={"action": "remove_set:1"})
    checked = client.post("/workout", data={"action": "check:0:0", "weight_0_0": "75", "reps_0_0": "5"},
                          follow_redirects=True)
    assert 'id="rest-time">2:00</strong>' in checked.text
    assert "Uncheck Squat set 1" in checked.text
    client.post("/workout", data={"action": "uncheck:0:0"})
    refused = client.post("/workout", data={"action": "finish"}, follow_redirects=True)
    assert "Check off at least one set" in refused.text
    client.post("/workout", data={"action": "cancel"})
    assert "Completed workouts will appear here" in client.get("/").text


def test_rest_timer_keeps_its_deadline_across_requests(tmp_path, now):
    current_time = now
    app = create_app(tmp_path / "timer.json", lambda: current_time)
    app.testing = True
    client = app.test_client()
    signup(client)
    ready = begin(client, now, ["Squat"])
    assert "Check off a set to start the rest timer." in ready.text

    started = client.post("/workout", data={"action": "check:0:0", "rest_0": "10"},
                          follow_redirects=True)
    deadline = int((now + timedelta(seconds=10)).timestamp() * 1000)
    assert f'data-rest-until="{deadline}"' in started.text
    assert 'id="rest-time">0:10</strong>' in started.text

    current_time += timedelta(seconds=4)
    retried = client.post("/workout", data={"action": "check:0:0"}, follow_redirects=True)
    assert f'data-rest-until="{deadline}"' in retried.text
    assert 'id="rest-time">0:06</strong>' in retried.text

    current_time += timedelta(seconds=6)
    completed = client.get("/workout")
    assert 'id="rest-time">0:00</strong>' in completed.text
    assert 'id="rest-label">Rest complete</span>' in completed.text

    disabled = client.post("/workout", data={"action": "check:0:1", "rest_0": "0"},
                           follow_redirects=True)
    assert "data-rest-until" not in disabled.text


def test_full_demo_and_edit_rebuild_promotion(now, tmp_path):
    path = tmp_path / "demo.json"
    DataStore(path).write(demo_data(now))
    app = create_app(path, lambda: now)
    app.testing = True
    client = app.test_client()
    client.post("/plan", data={"day": now.date().isoformat(), "action": "routine:0"})
    checked = client.post("/workout", data={"action": "check:0:0", "weight_0_0": "92.5", "reps_0_0": "3"},
                          follow_redirects=True)
    assert "Passed" in checked.text
    for action in ("check:0:1", "check:0:2", "check:2:0"):
        client.post("/workout", data={"action": action})
    result = client.post("/workout", data={"action": "finish"}, follow_redirects=True)
    assert "Legs · Silver → Gold" in result.text
    assert "40.8 → 50.1" in result.text
    assert "92.5 kg × 3" in result.text
    assert len(DataStore(path).read()["workouts"]) == 45

    client.post("/workouts/45/edit")
    edited = client.post("/workout", data={"action": "finish", "weight_0_0": "90"},
                         follow_redirects=True)
    assert "Legs · Silver → Gold" not in edited.text
    assert "Squat 92.5 kg × 3" in client.get("/").text
    assert len(DataStore(path).read()["workouts"]) == 45


def test_stats_show_comparison_and_render_three_png_charts(client):
    signup(client)
    page = client.get("/stats?metric=volume")
    assert "Completed week comparison" in page.text
    assert "/charts/volume.png" in page.text
    assert "No baseline yet" in page.text
    for metric in ("history", "sets", "volume"):
        response = client.get(f"/charts/{metric}.png")
        assert response.mimetype == "image/png"
        assert response.data.startswith(b"\x89PNG")


def test_ranking_page_filters_use_sample_profiles(client):
    signup(client)
    district = client.get("/ranking")
    assert "sample lifters" in district.text
    assert "Jiho" in district.text
    assert "Alex" not in district.text
    everyone = client.get("/ranking?scope=all&metric=consistency")
    assert "Alex" in everyone.text
    assert "Consistency" in everyone.text


def test_export_contains_only_completed_sets(client, now):
    signup(client)
    begin(client, now, ["Squat"])
    client.post("/workout", data={"action": "check:0:0", "weight_0_0": "75", "reps_0_0": "5"})
    client.post("/workout", data={"action": "finish"})
    response = client.get("/workouts.csv")
    rows = list(csv.DictReader(StringIO(response.text)))
    assert response.mimetype == "text/csv"
    assert len(rows) == 1
    assert rows[0]["exercise"] == "Squat"
    assert rows[0]["weight_kg"] == "75.0"


def test_reset_requires_explicit_confirmation_and_opens_signup(now, tmp_path):
    path = tmp_path / "reset.json"
    store = DataStore(path)
    original = demo_data(now)
    original["active_workout"] = {"exercises": []}
    store.write(original)
    app = create_app(path, lambda: now)
    app.testing = True
    client = app.test_client()

    rejected = client.post("/reset", data={"confirm": "no"}, follow_redirects=True)
    assert rejected.history[0].location.endswith("#reset-local-data")
    assert 'id="reset-local-data" open' in rejected.text
    assert "Enter RESET in this field" in rejected.text
    assert store.read() == original

    accepted = client.post("/reset", data={"confirm": " reset "}, follow_redirects=True)
    assert accepted.request.path == "/signup"
    assert "Local data reset." in accepted.text
    assert "Set up your profile" in accepted.text
    assert store.read() == empty_data()
