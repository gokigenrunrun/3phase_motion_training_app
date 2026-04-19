import math

import streamlit as st

from exercises import Exercise
from state import get_remaining_from_snapshot
from ui.training_stage import render_compact_page_styles


def render_transition_view(
    exercise: Exercise,
    *,
    phase_started_at: float | None,
    phase_duration: float,
) -> None:
    """次の動作を短く知らせる中間画面です。"""

    render_compact_page_styles()
    _render_transition_body(
        exercise=exercise,
        phase_started_at=phase_started_at,
        phase_duration=phase_duration,
    )


@st.fragment(run_every=1)
def _render_transition_body(
    exercise: Exercise,
    *,
    phase_started_at: float | None,
    phase_duration: float,
) -> None:
    """transition 画面の残り時間を1秒ごとに再描画します。"""

    remaining = max(0, math.ceil(get_remaining_from_snapshot(
        started_at=phase_started_at,
        duration=phase_duration,
    )))
    progress_percent = _get_remaining_progress(
        remaining_seconds=remaining,
        phase_duration=phase_duration,
    )
    elapsed_percent = 100 - progress_percent
    transition_message = st.session_state.get("transition_message") or f"次は{exercise.name}"

    st.markdown(
        f"""
        <div class="transition-screen">
            <div class="transition-kicker">次の動作を確認しましょう</div>
            <div class="transition-title">{transition_message}</div>
            <div class="transition-copy">このあとお手本が表示されます</div>
            <div class="transition-timer" style="--progress:{progress_percent}%; --elapsed:{elapsed_percent}%;">
                <div class="transition-timer-inner">{remaining}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _get_remaining_progress(*, remaining_seconds: int, phase_duration: float) -> int:
    if phase_duration <= 0:
        return 0
    return max(0, min(100, round((remaining_seconds / phase_duration) * 100)))
