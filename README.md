# GoUp

GoUp is a local Python app for logging workouts and tracking game-style training stats. It calculates 18 muscle stats across six groups, tracks completed workouts, and unlocks tiers through lift tests.

## Run the app

Run these commands in PowerShell from the project folder. Python 3.13 was used for development and testing.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Open [GoUp](http://127.0.0.1:5000) in your browser. Create a profile and enter the loads you have lifted for at least three reps. The app saves your profile, workouts, routines, and current draft in `data/goup_data.json`. If the JSON file is missing, the app imports the earlier SQLite workout history once and leaves the SQLite file intact.

## Presentation demo

Use a separate demo file so the sample workouts stay separate from your own records.

```powershell
.\.venv\Scripts\python.exe -m goup.seed --path data/goup_demo.json
.\.venv\Scripts\python.exe app.py --data data/goup_demo.json
```

For a rebuild of the same demo file, add `--force` to the seed command. It keeps a timestamped copy of the previous file.

1. Open **Home**. The seeded lifter is **75 kg**, has **44 workouts across 16 weeks**, and starts the demo with **Legs 40.8, Silver II** and a previous squat record of **90 kg**.
2. Open **Workout** and start the **Legs and Core** routine. Set the first squat to **92.5 kg × 3** and check it off. GoUp displays **Passed** and starts the rest timer.
3. Check off the two remaining squat sets and one calf raise set. Finish the workout. The result shows **Legs promoted from Silver to Gold**, a new personal record, and **40.8 to 50.1** for the Legs stat.
4. Open **Stats** to see the stat history and the four-week **Sets** or **Volume** chart. Open **Ranking** to show the local demo ranking with sample lifters.

## How the rules work

- **Growth** applies to sets with at least five reps and at least 60% of the best logged weight for that exercise. Main, helper, and minor muscles receive credit factors of 1.0, 0.5, and 0.25. The rule multiplies the remaining gap to 100 by 0.0011 and the remaining factors shown on the slides.
- **Recovery** starts at 30% and reaches 100% in 48 hours for Chest, Shoulders, Arms, and Core or in 72 hours for Back and Legs. Speed is 1.0 in this version, and the training-age factor halves per complete year since sign-up. The first ten effective sets per muscle per week get full credit, sets 11–20 get 30%, and later sets get zero growth credit.
- **Time off** begins to reduce a muscle's stat after a 14-day grace period. Each full week beyond that point multiplies the stat by 0.98, down to a floor of 80% of its peak.
- **Promotion** uses a body-weight multiplier and rounds the target up to the next 2.5 kg increment. A set of at least three reps at the target unlocks the next tier and raises each muscle in the group to at least that tier's starting stat. Core advances through game stats.
- **Consistency** counts distinct training days in the last 28 days and caps a 12-day goal at 100 points. The growth factor is `1 + score / 500`, using the score before the workout.
- **Volume** adds weight × reps across the logged sets. **Completed week comparison** uses the two most recent full Monday–Sunday weeks. An earlier volume of zero displays **No baseline yet**.
- **Ranking** uses sample profiles in the local app. Your profile joins after four distinct training weeks, and the screen supports district, everyone, same tier, and consistency views.

The growth figures are simulated game stats computed from workout records. A physiological validation study would require its own measurements and evaluation.

## Project structure

- `app.py` starts the local server. `goup/web.py` handles the Flask pages and forms.
- `goup/models.py` validates inputs. `goup/storage.py` reads and writes the local JSON file.
- `goup/data.py` defines the exercise catalog, tier thresholds, and sample lifters. `goup/engine.py` replays the raw workouts in order and calculates the stats.
- `goup/charts.py` makes PNG charts with Matplotlib. `goup/seed.py` creates the presentation demo data.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

The tests cover the promotion and growth boundaries, JSON and SQLite compatibility, the workout screens, chart output, and the complete presentation demo.

All 49 tests passed. Replaying the 44 sample workouts took a median of 7.13 ms over 20 runs on the development computer. This measures the Python engine without chart rendering.

## Libraries

- [Flask](https://flask.palletsprojects.com/) serves the local web pages.
- [Matplotlib](https://matplotlib.org/) creates the charts.
- [pytest](https://docs.pytest.org/) runs the project tests.
