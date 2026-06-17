# このファイルは PRE_DEMO オーバーレイに置き換えられました
# 現在は使用されていません（app.py からは import されません）

"""カウントダウン画面（COUNTDOWN フェーズ）。【廃止】

DEPRECATED: COUNTDOWN フェーズは廃止され、PRE_DEMO のオーバーレイ方式に
一本化されました。本ファイルは将来削除予定です。
"""

import streamlit as st

from exercises import Exercise
from state import get_remaining_from_snapshot
from ui.media_blocks import PANEL_MAX_WIDTH_PX, render_video_panel, render_webcam_panel
from ui.styles import render_countdown_overlay, render_header, speak


@st.fragment(run_every=0.8)
def _countdown_overlay_fragment(
    phase_started_at: float | None,
    phase_duration: float,
) -> None:
    """オーバーレイカウントダウンを 0.8 秒ごとに再描画する fragment。

    - 開始直後に「つぎは いっしょに やってみよう！」を 1 回だけ読み上げる
    - 残り 0 になった瞬間に「スタート！」を読み上げ、Start! を見せる
    - 次の fragment 実行（≒0.8 秒後）で st.rerun() を発火し phase 遷移
    """
    remaining_float = max(0.0, get_remaining_from_snapshot(
        started_at=phase_started_at,
        duration=phase_duration,
    ))
    remaining = max(0, int(remaining_float))

    st.markdown(
        render_countdown_overlay(remaining=remaining, duration=phase_duration),
        unsafe_allow_html=True,
    )

    if remaining_float <= 0:
        if st.session_state.get("last_spoken") != "countdown_done":
            # 初回: Start! を見せるために rerun せず speak のみ
            speak("スタート！")
            st.session_state.last_spoken = "countdown_done"
        else:
            # 2 回目以降: phase 遷移を発火
            st.rerun()
    else:
        # 開始直後の最初の fragment 実行で 1 回だけ読み上げる
        if st.session_state.get("last_spoken") != "countdown_intro":
            speak("つぎは いっしょに やってみよう！")
            st.session_state.last_spoken = "countdown_intro"


def render_countdown_view(
    exercise: Exercise,
    *,
    phase_started_at: float | None,
    phase_duration: float,
) -> None:
    """カウントダウン画面を描画する。

    動画とカメラを背景に表示し、上から半透明オーバーレイ +
    青い円形カウントダウンを重ねる。

    Args:
        exercise:         現在の種目
        phase_started_at: フェーズ開始時刻
        phase_duration:   フェーズ継続時間（秒）
    """
    # 1. ヘッダー
    st.markdown(
        render_header("", "<ruby>準備<rt>じゅんび</rt></ruby>は　いいですか？"),
        unsafe_allow_html=True,
    )

    # 2. 動画・カメラの 2 カラム（オーバーレイ越しに薄く見える背景として）
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

    # 3. オーバーレイ + タイマー（fragment で 0.8 秒ごとに自己再描画）
    _countdown_overlay_fragment(
        phase_started_at=phase_started_at,
        phase_duration=phase_duration,
    )
