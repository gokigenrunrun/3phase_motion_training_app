"""被験者番号入力と計測開始の画面（READY フェーズ）。"""

from typing import Callable

import streamlit as st

import database
from ui.styles import get_character_svg, render_header, speak


def render_ready_view(on_start: Callable[[], None]) -> None:
    """被験者番号を入力してセッションを開始する画面を描画する。

    CSS は app.py の main() で注入済みのため、ここでは呼ばない。

    Args:
        on_start: スタートボタン押下後のフェーズ遷移コールバック
    """
    if st.session_state.get("last_spoken") != "ready":
        speak("いっしょに うんどう しよう！ばんごうを いれてね")
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

    st.write("ばんごうを　いれてください")
    subject_id: str = st.text_input(
        label="被験者番号",
        label_visibility="hidden",
        placeholder="例：001",
        max_chars=10,
        key="subject_id_input",
    )

    is_input_valid = bool(subject_id.strip())
    st.button(
        "は　じ　め　る",
        type="primary",
        use_container_width=True,
        disabled=not is_input_valid,
        on_click=_handle_start,
        args=(subject_id.strip(), on_start),
    )


def _handle_start(subject_id: str, on_start: Callable[[], None]) -> None:
    """スタートボタン押下時の処理。

    DB にセッションを作成し、session_state に保存したうえでフェーズを進める。
    """
    if not subject_id:
        return

    session_id = database.create_session(subject_id)
    st.session_state.session_id = session_id
    st.session_state.subject_id = subject_id
    on_start()
