"""お手本動画とカメラを並べて表示する画面（DEMO フェーズ）。"""

import streamlit as st

from exercises import Exercise
from state import get_remaining_from_snapshot
from ui.media_blocks import (
    PANEL_MAX_WIDTH_PX,
    render_demo_video_panel,
    render_video_panel,
)
from ui.pre_measure_view import render_webrtc_camera
from ui.styles import render_header


@st.fragment(run_every=1.0)
def _demo_phase_watcher(phase_started_at: float | None, phase_duration: float) -> None:
    """フェーズ終了を1秒ごとに監視するfragment。

    タイマー表示は不要だが、時間切れを検出して full rerun を起こす必要がある。
    iframe を含むメディアパネルとは独立して動作するため removeChild エラーが起きない。
    """
    remaining = max(0.0, get_remaining_from_snapshot(
        started_at=phase_started_at,
        duration=phase_duration,
    ))
    if remaining <= 0:
        st.rerun()  # full rerun で phase_controller が遷移を検出する


def render_demo_view(
    exercise: Exercise,
    *,
    phase_started_at: float | None,
    phase_duration: float,
) -> None:
    """お手本動画とカメラ映像を2カラムで表示する画面を描画する。

    CSS は app.py の main() で注入済みのため、ここでは呼ばない。
    進行状況は画面下部の progress_indicator.py で表示するため
    画面中央のドット表示は持たない。

    Args:
        exercise:         現在の種目
        phase_started_at: フェーズ開始時刻（インターフェース統一のため受け取る）
        phase_duration:   フェーズ継続時間（同上）
    """
    st.markdown(
        render_header("", "おてほんを　みてみよう"),
        unsafe_allow_html=True,
    )

    left, right = st.columns(2, gap="large")
    with left:
        st.write("おてほんどうが")
        if exercise.uses_segmented_video:
            # 永続 video（parent.document）を canvas に描画。DEMO 区間
            # （0〜demo_duration 秒）を再生して停止する。video 要素は rerun を
            # またいで保持されるため、PRE_MEASURE 遷移時にリロードされない。
            render_demo_video_panel(
                exercise=exercise,
                phase="demo",
                max_width_px=PANEL_MAX_WIDTH_PX,
            )
        else:
            render_video_panel(
                video_filename=exercise.video_path.name,
                autoplay=True,
                loop=False,
                loop_count=exercise.loop_count,
                max_width_px=PANEL_MAX_WIDTH_PX,
            )
    with right:
        st.write("あなたのうごき")
        # CAMERA_CHECK と同じ key で接続を維持したまま表示する
        # （PRE_MEASURE への遷移時に読み込み待ちが発生しない）
        render_webrtc_camera(exercise, visible=True)

    # iframe とは独立した fragment でフェーズ終了を監視する
    _demo_phase_watcher(phase_started_at=phase_started_at, phase_duration=phase_duration)
