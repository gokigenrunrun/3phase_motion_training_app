from exercises import Exercise
from ui.training_stage import render_training_stage


def render_countdown_view(
    exercise: Exercise,
    *,
    phase_started_at: float | None,
    phase_duration: float,
) -> None:
    """左右2カラムを保ったまま中央にカウントダウンを重ねます。"""

    render_training_stage(
        exercise=exercise,
        phase_label="まねしてみよう",
        description="姿勢を整えて、カウントが終わったら同じ動きを始めてください。",
        phase_started_at=phase_started_at,
        phase_duration=phase_duration,
        video_loop=True,
        overlay_number=1,
    )
