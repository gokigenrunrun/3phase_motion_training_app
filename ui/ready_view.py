from typing import Callable

import streamlit as st

from ui.training_stage import render_compact_page_styles


def render_ready_view(on_start: Callable[[], None]) -> None:
    """開始前の画面です。"""

    render_compact_page_styles()
    st.title("運動計測トレーニング")
    st.markdown(
        """
        <div class="ready-wrap">
            <p class="ready-lead">
                このアプリでは、お手本の動きを見たあとに、同じ動きをしてもらいます。
                計測が終わると、結果を確認できます。
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("**流れ:** カメラチェック → バンザイ → 右足あげ → 左足あげ → 結果発表")
    st.button("スタート", type="primary", use_container_width=True, on_click=on_start)
