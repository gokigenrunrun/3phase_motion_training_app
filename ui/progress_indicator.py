"""画面下部の進行状況インジケーター（種目＋フェーズ）。

DEMO・COUNTDOWN・MEASURE・TRANSITION フェーズでのみ表示する。
position:fixed で常に画面下部に固定される。

注意: st.markdown(unsafe_allow_html=True) で渡す HTML は、
Markdown のコードブロック判定（4文字以上の字下げ）を避けるため
**行頭に空白を入れない**こと。本ファイル内の f-string 連結は
すべてインデントなしで書く。
"""

import streamlit as st

from state import PHASE_COUNTDOWN, PHASE_DEMO, PHASE_MEASURE, PHASE_TRANSITION


# 種目内のフェーズ進行順
_PHASE_ORDER = [PHASE_DEMO, PHASE_COUNTDOWN, PHASE_MEASURE]
_PHASE_LABELS = ["おてほん", "じゅんび", "そくてい"]
_EXERCISE_LABELS = ["バンザイ", "みぎあし", "ひだりあし"]

# 配色
_COLOR_DONE = "#2ecc71"     # 完了：緑
_COLOR_ACTIVE = "#FF8C00"   # 現在：オレンジ
_COLOR_TODO = "#4a5568"     # 未実施：グレー
_COLOR_BG = "#1a2340"       # 背景：濃い紺

_VISIBLE_PHASES = {PHASE_DEMO, PHASE_COUNTDOWN, PHASE_MEASURE, PHASE_TRANSITION}


def render_progress_indicator() -> None:
    """画面下部に種目＋フェーズの進行状況を表示する。

    表示対象外のフェーズ（READY・CAMERA_CHECK・FINISHED）では何もしない。
    """
    phase = st.session_state.get("phase", "")
    if phase not in _VISIBLE_PHASES:
        return

    exercise_index = st.session_state.get("exercise_index", 0)

    # 現在のフェーズインデックス（TRANSITION 中は全フェーズ完了とみなす）
    if phase == PHASE_TRANSITION:
        current_phase_index = len(_PHASE_ORDER)
    else:
        current_phase_index = _PHASE_ORDER.index(phase) if phase in _PHASE_ORDER else 0

    st.markdown(
        _build_indicator_html(
            exercise_index=exercise_index,
            current_phase_index=current_phase_index,
            phase=phase,
        ),
        unsafe_allow_html=True,
    )


def _build_indicator_html(
    *,
    exercise_index: int,
    current_phase_index: int,
    phase: str,
) -> str:
    """インジケーターのHTMLを生成する。

    Markdown のコードブロック化を避けるため、すべての文字列断片は
    行頭に空白を入れず連結する（先頭が < で始まることを保証）。
    """
    items_html = ""
    for i, label in enumerate(_EXERCISE_LABELS):
        items_html += _build_exercise_item_html(
            i=i,
            label=label,
            exercise_index=exercise_index,
            current_phase_index=current_phase_index,
            phase=phase,
        )
        # 種目間の接続ライン（最後以外）
        if i < len(_EXERCISE_LABELS) - 1:
            line_color = _COLOR_DONE if i < exercise_index else _COLOR_TODO
            items_html += (
                f'<div style="flex:1;height:3px;background:{line_color};'
                f'margin:0 -2px 32px;opacity:0.8;"></div>'
            )

    # 行頭空白なし・改行なしで連結（Markdown コードブロック化を回避）
    return (
        f'<div style="position:fixed;bottom:0;left:0;right:0;'
        f'background:{_COLOR_BG};padding:12px 24px 16px;'
        f'display:flex;align-items:flex-start;justify-content:center;'
        f'gap:0;z-index:999;border-top:1px solid rgba(255,255,255,0.1);">'
        f'<div style="display:flex;align-items:center;justify-content:center;'
        f'gap:0;max-width:480px;width:100%;">'
        f'{items_html}'
        f'</div>'
        f'</div>'
        # インジケーター分の余白
        f'<div style="height:100px;"></div>'
    )


def _build_exercise_item_html(
    *,
    i: int,
    label: str,
    exercise_index: int,
    current_phase_index: int,
    phase: str,
) -> str:
    """1種目分（メインドット＋ラベル＋フェーズドット）のHTMLを生成する。"""
    if i < exercise_index:
        # 完了済み種目
        dot_style = f"background:{_COLOR_DONE};"
        check = "✓"
        label_color = _COLOR_DONE
    elif i == exercise_index:
        # 現在の種目（緑のリングで進行中を表現）
        dot_style = f"background:transparent;border:3px solid {_COLOR_DONE};"
        check = ""
        label_color = _COLOR_DONE
    else:
        # 未実施
        dot_style = f"background:{_COLOR_TODO};"
        check = ""
        label_color = _COLOR_TODO

    # フェーズドットは現在の種目のみ・TRANSITION 以外で表示
    phase_dots_html = ""
    if i == exercise_index and phase != PHASE_TRANSITION:
        phase_items = ""
        for j in range(len(_PHASE_LABELS)):
            if j < current_phase_index:
                color = _COLOR_DONE
            elif j == current_phase_index:
                color = _COLOR_ACTIVE
            else:
                color = _COLOR_TODO
            phase_items += (
                f'<div style="width:8px;height:8px;border-radius:50%;'
                f'background:{color};flex-shrink:0;"></div>'
            )
        current_phase_label = (
            _PHASE_LABELS[current_phase_index]
            if current_phase_index < len(_PHASE_LABELS) else ""
        )
        phase_dots_html = (
            f'<div style="display:flex;gap:4px;justify-content:center;margin-top:4px;">'
            f'{phase_items}'
            f'</div>'
            f'<div style="font-size:10px;color:{_COLOR_ACTIVE};'
            f'text-align:center;margin-top:2px;">{current_phase_label}</div>'
        )

    return (
        f'<div style="display:flex;flex-direction:column;align-items:center;gap:4px;">'
        f'<div style="width:36px;height:36px;border-radius:50%;{dot_style}'
        f'display:flex;align-items:center;justify-content:center;'
        f'color:white;font-size:16px;font-weight:700;flex-shrink:0;">'
        f'{check}'
        f'</div>'
        f'<div style="font-size:12px;color:{label_color};text-align:center;">{label}</div>'
        f'{phase_dots_html}'
        f'</div>'
    )
