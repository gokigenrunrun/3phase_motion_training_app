"""計測画面（MEASURE フェーズ）。

注意: 現在の app.py の phase_controller() は PRE_MEASURE から直接
TRANSITION/FINISHED へ遷移させるため、MEASURE フェーズには実行時には
到達しない（PRE_MEASURE が JS 側でカウントダウンと計測を一体化して
担当するようになったため）。
"""

import streamlit as st

from exercises import Exercise
from state import get_remaining_from_snapshot
from ui.media_blocks import PANEL_MAX_WIDTH_PX, render_video_panel, render_webcam_panel
from ui.styles import render_header_with_timer, speak


# 種目ごとの動作説明（計測開始時に1回だけ読み上げる）
_MEASURE_SPEECHES: dict[str, str] = {
    "banzai": "ちいさくなって　うでを のばす！",
    "right_leg_raise": "うでを よこに ひろげて、みぎあしを ゆっくり うえに あげよう！",
    "left_leg_raise": "うでを よこに ひろげて、ひだりあしを ゆっくり うえに あげよう！",
}


@st.fragment(run_every=0.8)
def _measure_header_fragment(phase_started_at: float | None, phase_duration: float) -> None:
    """ヘッダー（右端に円形タイマー）を 0.8 秒ごとに再描画する fragment。

    iframe/script を含まない静的HTMLのみのため、頻繁に再描画しても
    removeChild エラーは発生しない。
    """
    remaining_float = max(0.0, get_remaining_from_snapshot(
        started_at=phase_started_at,
        duration=phase_duration,
    ))
    remaining = max(0, int(remaining_float))

    st.markdown(
        render_header_with_timer(
            icon="",
            title_html="そくていちゅう！",
            remaining=remaining,
            duration=phase_duration,
        ),
        unsafe_allow_html=True,
    )

    if remaining_float <= 0:
        st.rerun()  # full rerun で phase_controller が遷移を検出する


def render_measure_view(
    exercise: Exercise,
    *,
    phase_started_at: float | None,
    phase_duration: float,
) -> None:
    """計測中の2カラム画面を描画する。

    CSS は app.py の main() で注入済みのため、ここでは呼ばない。

    Args:
        exercise:         現在の種目
        phase_started_at: フェーズ開始時刻
        phase_duration:   フェーズ継続時間（秒）
    """
    # 種目ごとの動作説明を計測開始時に1回だけ読み上げる
    spoken_key = f"measure_{exercise.key}"
    if st.session_state.get("last_spoken") != spoken_key:
        speech_text = _MEASURE_SPEECHES.get(exercise.key, "")
        if speech_text:
            speak(speech_text)
        st.session_state.last_spoken = spoken_key

    # タイマー付きヘッダー（fragment で 0.8 秒ごとに自己再描画）
    _measure_header_fragment(
        phase_started_at=phase_started_at,
        phase_duration=phase_duration,
    )

    # ヘッダー直下に動画とカメラを並べる
    left, right = st.columns(2, gap="large")
    with left:
        st.write("おてほんどうが")
        if exercise.uses_segmented_video:
            # 計測区間（0〜measure_video_end 秒）を 1 回再生して停止する
            render_video_panel(
                video_filename=exercise.video_path.name,
                autoplay=True,
                seek_to=0.0,
                stop_at=exercise.get_measure_video_end(),
                play_from=0.0,
                max_width_px=PANEL_MAX_WIDTH_PX,
            )
        else:
            render_video_panel(
                video_filename=exercise.video_path.name,
                autoplay=True,
                loop=True,
                max_width_px=PANEL_MAX_WIDTH_PX,
            )
    with right:
        st.write("あなたのうごき")
        render_webcam_panel(max_width_px=PANEL_MAX_WIDTH_PX)
