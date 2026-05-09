"""カウントダウン画面（COUNTDOWN フェーズ）。

動画・カメラを背景に表示し、その上に半透明オーバーレイで
青い円形カウントダウン（200×200）を重ねる。
"""

import streamlit as st

from exercises import Exercise
from state import get_remaining_from_snapshot
from ui.media_blocks import PANEL_MAX_WIDTH_PX, render_video_panel, render_webcam_panel
from ui.styles import render_header, speak


def _render_countdown_overlay(remaining: int, duration: float) -> str:
    """半透明オーバーレイ + 円形カウントダウン SVG の HTML を返す。

    position:fixed で全画面を覆い、background は rgba(0,0,0,0.35) の薄暗幕。
    pointer-events:none なので背後の操作はブロックしない。
    Markdown のコードブロック化を避けるため、行頭空白なしの 1 行 HTML として返す。
    """
    r = 80
    circumference = 2 * 3.14159 * r  # ≒ 502.65
    progress = max(0.0, min(1.0, remaining / duration)) if duration > 0 else 0.0
    offset = circumference * (1 - progress)
    display_text = str(remaining) if remaining > 0 else "Start!"
    # "Start!" は文字数が多いのでフォントを小さくして円内に収める
    font_size = 64 if remaining > 0 else 48

    return (
        f'<div style="position:fixed;top:0;left:0;right:0;bottom:0;'
        f'background:rgba(0,0,0,0.35);display:flex;flex-direction:column;'
        f'align-items:center;justify-content:center;z-index:1000;'
        f'pointer-events:none;">'
        f'<svg width="200" height="200" viewBox="0 0 200 200" '
        f'xmlns="http://www.w3.org/2000/svg">'
        # 背景の薄い円
        f'<circle cx="100" cy="100" r="{r}" fill="none" '
        f'stroke="rgba(255,255,255,0.2)" stroke-width="10"/>'
        # 進捗を示す青い円弧（12時方向起点・時計回りに減る）
        f'<circle cx="100" cy="100" r="{r}" fill="none" '
        f'stroke="#378ADD" stroke-width="10" '
        f'stroke-dasharray="{circumference:.2f}" '
        f'stroke-dashoffset="{offset:.2f}" '
        f'stroke-linecap="round" '
        f'transform="rotate(-90 100 100)"/>'
        # 内側の半透明黒円（数字の可読性向上）
        f'<circle cx="100" cy="100" r="68" fill="rgba(0,0,0,0.4)"/>'
        # 残り秒数 / GO!
        f'<text x="100" y="118" text-anchor="middle" fill="white" '
        f'font-size="{font_size}" font-weight="700" '
        f'font-family="sans-serif">'
        f'{display_text}</text>'
        f'</svg>'
        f'</div>'
    )


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
        _render_countdown_overlay(remaining=remaining, duration=phase_duration),
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
        st.write("お手本どうが")
        render_video_panel(
            video_path=str(exercise.video_path),
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
