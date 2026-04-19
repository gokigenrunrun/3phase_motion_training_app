from exercises import Exercise
from ui.training_stage import render_training_stage


def render_demo_view(
    exercise: Exercise,
    *,
    phase_started_at: float | None,
    phase_duration: float,
) -> None:
    """お手本とカメラを同じ枠で表示します。"""

    render_training_stage(
        exercise=exercise,
        phase_label="お手本",
        description=exercise.description,
        phase_started_at=phase_started_at,
        phase_duration=phase_duration,
        video_loop=False,
    )
