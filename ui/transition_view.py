"""次の種目への移行画面（TRANSITION フェーズ）。"""

import streamlit as st

from exercises import Exercise
from state import get_remaining_from_snapshot
from ui.styles import render_header, speak


# 音声読み上げ用の種目名（exercise.name と異なる場合があるため固定）
_EXERCISE_NAMES_FOR_SPEECH = ["バンザイ", "みぎあし上げ", "ひだりあし上げ"]


@st.fragment(run_every=0.8)
def _transition_timer(phase_started_at: float | None, phase_duration: float) -> None:
    """残り時間を0.8秒ごとに更新するfragment。"""
    remaining = max(0.0, get_remaining_from_snapshot(
        started_at=phase_started_at,
        duration=phase_duration,
    ))
    st.metric(label="のこり", value=f"{max(0, int(remaining))} びょう")
    if remaining <= 0:
        st.rerun()  # full rerun で phase_controller が遷移を検出する


def render_transition_view(
    exercise: Exercise,
    *,
    phase_started_at: float | None,
    phase_duration: float,
) -> None:
    """次の種目名とカウントダウンを表示する移行画面を描画する。

    CSS は app.py の main() で注入済みのため、ここでは呼ばない。

    Args:
        exercise:         次に行う種目
        phase_started_at: フェーズ開始時刻
        phase_duration:   フェーズ継続時間（秒）
    """
    exercise_index = st.session_state.get("exercise_index", 0)
    if 0 <= exercise_index < len(_EXERCISE_NAMES_FOR_SPEECH):
        exercise_name_for_speech = _EXERCISE_NAMES_FOR_SPEECH[exercise_index]
    else:
        exercise_name_for_speech = exercise.name

    spoken_key = f"transition_{exercise_index}"
    if st.session_state.get("last_spoken") != spoken_key:
        speak(f"つぎは {exercise_name_for_speech} です。まずは おてほんを かくにんしよう！")
        st.session_state.last_spoken = spoken_key

    st.markdown(
        render_header(
            "",
            "<ruby>次<rt>つぎ</rt></ruby>の　<ruby>運動<rt>うんどう</rt></ruby>へ",
        ),
        unsafe_allow_html=True,
    )

    transition_message = (
        st.session_state.get("transition_message") or f"つぎは　{exercise.name}　だよ！"
    )
    st.info(transition_message)

    st.subheader(exercise.name)

    _transition_timer(phase_started_at=phase_started_at, phase_duration=phase_duration)
