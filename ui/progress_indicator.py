"""画面下部の進行状況インジケーター（種目ドットのみ）。

DEMO・PRE_MEASURE・START_DISPLAY・MEASURE・TRANSITION フェーズで表示する。
position:fixed で常に画面下部に固定される。

注意: st.markdown(unsafe_allow_html=True) で渡す HTML は、
Markdown のコードブロック判定（4文字以上の字下げ）を避けるため
**行頭に空白を入れない**こと。本ファイル内の f-string 連結は
すべてインデントなしで書く。
"""

import streamlit as st

from state import (
    PHASE_DEMO,
    PHASE_MEASURE,
    PHASE_PRE_MEASURE,
    PHASE_START_DISPLAY,
    PHASE_TRANSITION,
)


_EXERCISE_LABELS = ["バンザイ", "みぎあし", "ひだりあし"]

# 配色（アプリ全体で統一）
_COLOR_DONE = "#378ADD"     # 完了：青
_COLOR_ACTIVE = "#FF8C00"   # 現在：オレンジ
_COLOR_TODO = "#B5D4F4"     # 未実施：薄い青
_COLOR_BG = "#FFFFFF"       # 背景：白
_COLOR_BORDER = "#E0E0E0"   # 上端の薄いボーダー

_VISIBLE_PHASES = {
    PHASE_DEMO,
    PHASE_PRE_MEASURE,
    PHASE_START_DISPLAY,
    PHASE_MEASURE,
    PHASE_TRANSITION,
}


def render_progress_indicator() -> None:
    """画面下部に種目進行状況（3 ドット）を表示する。"""
    phase = st.session_state.get("phase", "")
    if phase not in _VISIBLE_PHASES:
        return

    exercise_index = st.session_state.get("exercise_index", 0)

    st.markdown(
        _build_indicator_html(exercise_index=exercise_index),
        unsafe_allow_html=True,
    )


def _build_indicator_html(*, exercise_index: int) -> str:
    """インジケーターのHTMLを生成する（行頭空白なし）。"""
    items_html = ""
    for i, label in enumerate(_EXERCISE_LABELS):
        items_html += _build_exercise_item_html(
            i=i,
            label=label,
            exercise_index=exercise_index,
        )
        # 種目間の接続ライン（最後以外）
        if i < len(_EXERCISE_LABELS) - 1:
            line_color = _COLOR_DONE if i < exercise_index else _COLOR_TODO
            line_opacity = "1" if i < exercise_index else "0.5"
            items_html += (
                f'<div style="flex:1;height:3px;background:{line_color};'
                f'margin:0 -2px 20px;opacity:{line_opacity};"></div>'
            )

    return (
        f'<div style="position:fixed;bottom:0;left:0;right:0;'
        f'background:{_COLOR_BG};border-top:1px solid {_COLOR_BORDER};'
        f'padding:12px 24px 16px;'
        f'display:flex;align-items:center;justify-content:center;'
        f'z-index:999;">'
        f'<div style="display:flex;align-items:center;justify-content:center;'
        f'max-width:480px;width:100%;">'
        f'{items_html}'
        f'</div>'
        f'</div>'
        # インジケーター分の余白（フェーズドット撤去で短くなった）
        f'<div style="height:80px;"></div>'
    )


def _build_exercise_item_html(
    *,
    i: int,
    label: str,
    exercise_index: int,
) -> str:
    """1種目分（メインドット＋ラベル）の HTML を生成する。

    - 完了: 青背景に白チェックマーク（✓）
    - 現在: オレンジ枠 + 内側にオレンジ小円
    - 未実施: 薄い青で半透明
    """
    if i < exercise_index:
        # 完了済み: 青背景 + 白チェック
        main_dot = (
            f'<div style="width:36px;height:36px;border-radius:50%;'
            f'background:{_COLOR_DONE};display:flex;align-items:center;'
            f'justify-content:center;color:white;font-size:16px;'
            f'font-weight:700;flex-shrink:0;">✓</div>'
        )
        label_color = _COLOR_DONE
        label_opacity = "1"
    elif i == exercise_index:
        # 現在: オレンジ枠 + 内側にオレンジ小円
        main_dot = (
            f'<div style="width:36px;height:36px;border-radius:50%;'
            f'background:transparent;border:3px solid {_COLOR_ACTIVE};'
            f'display:flex;align-items:center;justify-content:center;'
            f'flex-shrink:0;box-sizing:border-box;">'
            f'<div style="width:14px;height:14px;border-radius:50%;'
            f'background:{_COLOR_ACTIVE};"></div>'
            f'</div>'
        )
        label_color = _COLOR_ACTIVE
        label_opacity = "1"
    else:
        # 未実施: 薄い青・半透明
        main_dot = (
            f'<div style="width:36px;height:36px;border-radius:50%;'
            f'background:{_COLOR_TODO};opacity:0.5;flex-shrink:0;"></div>'
        )
        label_color = _COLOR_TODO
        label_opacity = "0.6"

    return (
        f'<div style="display:flex;flex-direction:column;align-items:center;gap:4px;">'
        f'{main_dot}'
        f'<div style="font-size:12px;color:{label_color};opacity:{label_opacity};'
        f'text-align:center;">{label}</div>'
        f'</div>'
    )
