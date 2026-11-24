# GoUp

GoUp is a Python app for logging workouts and tracking weekly training by muscle group, exercise tiers, and consistency.

## Getting Started

GoUp was tested with Python 3.13 and Streamlit 1.67.0. Run these commands in PowerShell from the project folder.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open [GoUp](http://localhost:8501) in your browser. The app creates `data/goup.sqlite3` on first launch and stores workouts there.

## Demo Walkthrough

Start with an empty workout history.

1. Log a bench press for today with **40 kg, 8 reps, and 3 sets**.
2. Find the entry under **Workout History** and check that **This Week** shows **3 sets** and **960 kg × reps** for Chest. GoUp also counts these sets toward Triceps.
3. Check that the Bench Press tier advances from **Iron to Bronze**.
4. Check that the consistency score rises to **8 / 100**. Multiple workouts on one date count as one training day.
5. Restart the app and check that your workout is still in the history.
6. Log a bench press at **40 kg** in the earlier of the two completed weeks and at **50 kg** in the latest completed week, with **8 reps and 3 sets** each. Switch the chart from **Sets** to **Volume** and check that **Completed Week Comparison** shows a **+25.0%** change for Chest and Triceps.

## How GoUp Calculates Progress

- **Weekly training** runs from Monday through Sunday. Use **Sets** or **Volume** to chart the current week and the previous three weeks. Training volume is weight × reps × sets. GoUp credits the sets and volume to each muscle group associated with the exercise.
- **Volume change** compares the two most recent completed weeks. Subtract the earlier week's volume from the latest completed week's volume, divide by the earlier week's volume, and multiply by 100. If the earlier week's volume is zero, GoUp shows **No baseline yet**.
- **Exercise tiers** start at Iron and depend on the highest weight logged for that exercise. The table shows GoUp's game thresholds.
- **Consistency** is the number of distinct training days in the last 28 days, including today, divided by the 12-day goal and expressed as a percentage. The score is rounded to the nearest whole number and capped at 100.

| Exercise | Bronze | Silver | Gold | Master |
| --- | ---: | ---: | ---: | ---: |
| Bench Press | 40 kg | 60 kg | 80 kg | 100 kg |
| Squat | 50 kg | 80 kg | 110 kg | 140 kg |
| Deadlift | 60 kg | 100 kg | 130 kg | 160 kg |

## Project Structure

- `app.py` turns the inputs from **Log a Workout** into a `Workout` object and displays the results.
- `storage.py` saves and reads `Workout` objects. `WorkoutStore.save()` commits the new record to the SQLite file.
- `training.py` contains the calculations. `weekly_training()` adds sets and volume by week and muscle group. `exercise_tiers()` checks each exercise's best lift against its tier thresholds. `consistency()` uses a set of dates to count each training day once.

## Libraries

- The browser interface and charts use [Streamlit](https://docs.streamlit.io/).
- The local database uses [Python's sqlite3 module](https://docs.python.org/3/library/sqlite3.html).
