"""コース選択画面（READY フェーズ）。"""

from typing import Callable

import streamlit as st

import database
from ui.styles import get_character_svg, render_header, speak


def render_ready_view(on_start: Callable[[], None]) -> None:
    """コースを選択して計測を開始する画面を描画する。

    CSS は app.py の main() で注入済みのため、ここでは呼ばない。

    Args:
        on_start: コース選択ボタン押下後のフェーズ遷移コールバック
    """
    if st.session_state.get("last_spoken") != "ready":
        speak("いっしょに うんどう しよう！コースを えらんでね")
        st.session_state.last_spoken = "ready"

    st.markdown(
        render_header("", "うんどう　そくてい　アプリ"),
        unsafe_allow_html=True,
    )

    # キャラクター（棒人間SVG）を st.image() で中央表示
    col = st.columns([1, 1, 1])[1]
    with col:
        st.image(get_character_svg(), width=80)

    st.info("いっしょに　うんどう　しよう！")

    st.write("コースを　えらんでね")

    # ノーマルコースのボタンだけオレンジ（primary）にする
    st.markdown(
        """
        <style>
        div[data-testid="stButton"] > button[kind="primary"] {
            background-color: #FF8C00 !important;
            border-color: #FF8C00 !important;
            color: white !important;
            font-size: 20px !important;
            font-weight: bold !important;
            padding: 16px !important;
        }
        div[data-testid="stButton"] > button[kind="primary"]:hover {
            background-color: #E07B00 !important;
            border-color: #E07B00 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.button(
        "ノーマル",
        type="primary",
        use_container_width=True,
        on_click=_handle_start,
        args=("normal", on_start),
    )

    # チャレンジ・ダンスモードは準備中のため押せない
    st.button(
        "チャレンジ（じゅんびちゅう）",
        use_container_width=True,
        disabled=True,
    )
    st.button(
        "ダンスモード（じゅんびちゅう）",
        use_container_width=True,
        disabled=True,
    )


def _handle_start(course: str, on_start: Callable[[], None]) -> None:
    """コース選択ボタン押下時の処理。

    DB にセッションを作成し、session_state に保存したうえでフェーズを進める。
    被験者番号の入力は廃止したため subject_id は空文字で保存する。
    """
    session_id = database.create_session(subject_id="")
    st.session_state.session_id = session_id
    st.session_state.subject_id = ""
    # 選択したコース名を保存する（現状は "normal" のみ選択可能で、
    # 他の画面ではまだ参照されていない）
    st.session_state.course = course
    on_start()
