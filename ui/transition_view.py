"""次の種目への移行画面（TRANSITION フェーズ・6 秒）。

動画・カメラは表示せず、画面中央に種目名（32px）と
360×360 の青い円形カウントダウンチャートを大きく表示する。
オーバーレイは使わない（背景は通常の白いまま）。
"""

import streamlit as st

from exercises import Exercise
from state import get_remaining_from_snapshot
from ui.styles import COLOR_BLUE_BASE, COLOR_BLUE_DARK, render_header, speak


# 表示用・読み上げ用の種目名（exercise_index でルックアップ）
_EXERCISE_DISPLAY_NAMES = ["バンザイ", "みぎあし　あげ", "ひだりあし　あげ"]


@st.fragment(run_every=0.8)
def _transition_countdown_fragment(
    phase_started_at: float | None,
    phase_duration: float,
    exercise_name: str,
) -> None:
    """種目名 + 360×360 の円形カウントダウンを 0.8 秒ごとに再描画する fragment。

    画面中央に縦並びで表示し、円弧（青）が時間経過で減っていく。
    残り 0 で full rerun → phase_controller が DEMO 遷移を検出。
    """
    remaining_float = max(0.0, get_remaining_from_snapshot(
        started_at=phase_started_at,
        duration=phase_duration,
    ))
    # remaining は整数に切り捨て。fragment が 0.8 秒ごとに走っても
    # 同じ秒の間は値が変わらないので、円弧の段階的更新が保証される。
    remaining = max(0, int(remaining_float))

    r = 140
    circumference = 2 * 3.14159 * r  # ≈ 879.65
    # 円弧 offset も remaining（整数）から計算する。これにより同じ
    # remaining の間は offset が完全に同一になり、円弧がカクッと段階的に減る。
    progress = max(0.0, min(1.0, remaining / phase_duration)) if phase_duration > 0 else 0.0
    offset = circumference * (1.0 - progress)

    st.markdown(
        # 画面中央に縦並びで配置（行頭空白なしで連結）
        f'<div style="display:flex;flex-direction:column;'
        f'align-items:center;justify-content:center;min-height:60vh;">'
        # 種目名
        f'<div style="font-size:32px;font-weight:500;color:{COLOR_BLUE_DARK};'
        f'margin-bottom:16px;">{exercise_name}</div>'
        # 360×360 円形カウントダウン
        f'<svg width="360" height="360" viewBox="0 0 360 360" '
        f'xmlns="http://www.w3.org/2000/svg">'
        # 背景の薄い青円
        f'<circle cx="180" cy="180" r="{r}" fill="none" '
        f'stroke="#E6F1FB" stroke-width="14"/>'
        # 進捗円弧（濃い青・12時方向起点で時計回りに減少）
        f'<circle cx="180" cy="180" r="{r}" fill="none" '
        f'stroke="{COLOR_BLUE_BASE}" stroke-width="14" '
        f'stroke-dasharray="{circumference:.2f}" '
        f'stroke-dashoffset="{offset:.2f}" '
        f'stroke-linecap="round" '
        f'transform="rotate(-90 180 180)"/>'
        # 内側の白円（数字の可読性向上）
        f'<circle cx="180" cy="180" r="122" fill="white"/>'
        # 残り秒数（青文字・110px）
        f'<text x="180" y="218" text-anchor="middle" '
        f'fill="{COLOR_BLUE_BASE}" font-size="110" font-weight="700" '
        f'font-family="sans-serif">{remaining}</text>'
        f'</svg>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if remaining_float <= 0:
        st.rerun()


def render_transition_view(
    exercise: Exercise,
    *,
    phase_started_at: float | None,
    phase_duration: float,
) -> None:
    """次の種目への移行画面を描画する。

    動画・カメラは出さず、ヘッダー + 種目名 + 360px 円形カウントダウンのみ。

    Args:
        exercise:         次に行う種目（インターフェース統一のため受け取る）
        phase_started_at: フェーズ開始時刻
        phase_duration:   フェーズ継続時間（秒・TRANSITION_SECONDS=6）
    """
    exercise_index = st.session_state.get("exercise_index", 0)
    if 0 <= exercise_index < len(_EXERCISE_DISPLAY_NAMES):
        exercise_name = _EXERCISE_DISPLAY_NAMES[exercise_index]
    else:
        exercise_name = exercise.name

    # 音声案内（種目ごとに 1 回）
    spoken_key = f"transition_{exercise_index}"
    if st.session_state.get("last_spoken") != spoken_key:
        speak(f"つぎは {exercise_name} です。まずは おてほんを かくにんしよう！")
        st.session_state.last_spoken = spoken_key

    # ヘッダー
    st.markdown(
        render_header("", "つぎの　うんどうへ"),
        unsafe_allow_html=True,
    )

    # 種目名 + 円形カウントダウン（fragment で 0.8 秒ごとに更新）
    _transition_countdown_fragment(
        phase_started_at=phase_started_at,
        phase_duration=phase_duration,
        exercise_name=exercise_name,
    )
