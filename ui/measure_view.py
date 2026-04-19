from exercises import Exercise
from ui.training_stage import render_training_stage


def render_measure_view(
    exercise: Exercise,
    *,
    phase_started_at: float | None,
    phase_duration: float,
) -> None:
    """左右2カラムで参考映像とカメラ枠を表示します。"""

    render_training_stage(
        exercise=exercise,
        phase_label="計測中",
        description="お手本を見ながら同じ動きをしてください。",
        phase_started_at=phase_started_at,
        phase_duration=phase_duration,
        video_loop=True,
    )
