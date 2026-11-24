"""Draw PNGs for workout history and weekly training."""

from io import BytesIO

from matplotlib.figure import Figure

from .data import MUSCLE_GROUPS
from .engine import weekly_training


def chart_image(state, workouts, today, metric):
    figure = Figure(figsize=(7.6, 3.3), layout="constrained")
    axis = figure.subplots()

    if metric == "history":
        dates = [day for day, _ in state.history]
        for group in MUSCLE_GROUPS:
            values = [stats[group] for _, stats in state.history]
            axis.plot(dates, values, label=group)
        axis.set_ylabel("Game stat")
        axis.set_ylim(0, 100)
        if not dates:
            axis.text(0.5, 0.5, "Complete a workout to see your history",
                      ha="center", transform=axis.transAxes)
    else:
        weeks = weekly_training(workouts, today)
        labels = [monday.strftime("%m-%d") for monday in weeks]
        for group in MUSCLE_GROUPS:
            values = [week[group][metric] for week in weeks.values()]
            axis.plot(labels, values, marker="o", label=group)
        axis.set_ylabel("Sets" if metric == "sets" else "Volume (kg × reps)")
        axis.set_xlabel("Week starting")
        axis.set_ylim(bottom=0)

    axis.grid(axis="y", alpha=0.2)
    axis.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=3, frameon=False)
    image = BytesIO()
    figure.savefig(image, format="png", dpi=120)
    image.seek(0)
    return image
