"""「Start!!」表示画面（START_DISPLAY フェーズ・2 秒）。

PRE_MEASURE のカウントダウン終了後、計測開始前に
動画・カメラの上に「Start!!」の大きな文字を 2 秒間オーバーレイ表示する。
開始時に「つぎは いっしょに やってみよう！スタート！」を読み上げる。
"""

import streamlit as st

from exercises import Exercise
from state import get_remaining_from_snapshot
from ui.media_blocks import PANEL_MAX_WIDTH_PX, render_video_panel, render_webcam_panel
from ui.styles import render_header, render_start_display_overlay, speak


@st.fragment(run_every=0.5)
def _start_display_watcher(
    phase_started_at: float | None,
    phase_duration: float,
) -> None:
    """フェーズ終了を 0.5 秒ごとに監視する fragment。

    画面表示は呼び出し側の view 本体で行うため、ここでは描画しない。
    残り 0 で full rerun を発火 → phase_controller が MEASURE 遷移を検出。
    """
    remaining = max(0.0, get_remaining_from_snapshot(
        started_at=phase_started_at,
        duration=phase_duration,
    ))
    if remaining <= 0:
        st.rerun()


def render_start_display_view(
    exercise: Exercise,
    *,
    phase_started_at: float | None,
    phase_duration: float,
) -> None:
    """START_DISPLAY 画面を描画する。

    動画・カメラを背景表示しながら、上から「Start!!」のオーバーレイを表示する。
    フェーズ開始時に「つぎは いっしょに やってみよう！スタート！」を 1 回読み上げる。

    Args:
        exercise:         現在の種目（動画パスを参照）
        phase_started_at: フェーズ開始時刻
        phase_duration:   フェーズ継続時間（秒・START_DISPLAY_SECONDS=2）
    """
    # 音声案内（種目ごとに 1 回）
    spoken_key = f"start_display_{st.session_state.get('exercise_index', 0)}"
    if st.session_state.get("last_spoken") != spoken_key:
        speak("つぎは いっしょに やってみよう！スタート！")
        st.session_state.last_spoken = spoken_key

    # ヘッダー
    st.markdown(
        render_header("", "そくていちゅう！"),
        unsafe_allow_html=True,
    )

    # 動画・カメラの 2 カラム（背景に表示続ける）
    left, right = st.columns(2, gap="large")
    with left:
        st.write("おてほんどうが")
        render_video_panel(
            video_filename=exercise.video_path.name,
            autoplay=True,
            loop=True,
            max_width_px=PANEL_MAX_WIDTH_PX,
        )
    with right:
        st.write("あなたのうごき")
        render_webcam_panel(max_width_px=PANEL_MAX_WIDTH_PX)

    # 「Start!!」オーバーレイ
    st.markdown(render_start_display_overlay(), unsafe_allow_html=True)

    # フェーズ終了監視（裏で動かすだけ）
    _start_display_watcher(
        phase_started_at=phase_started_at,
        phase_duration=phase_duration,
    )
