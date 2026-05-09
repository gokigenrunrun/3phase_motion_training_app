"""カメラ画角の確認画面（CAMERA_CHECK フェーズ）。"""

from typing import Callable

import streamlit as st

from ui.media_blocks import PANEL_MAX_WIDTH_PX, render_webcam_panel
from ui.styles import render_header, speak


def render_camera_check_view(on_confirm: Callable[[], None]) -> None:
    """計測前にカメラの画角を確認する画面を描画する。

    CSS は app.py の main() で注入済みのため、ここでは呼ばない。

    Args:
        on_confirm: 「だいじょうぶ！」ボタン押下後のフェーズ遷移コールバック
    """
    if st.session_state.get("last_spoken") != "camera_check":
        speak("カメラを かくにん しよう。からだ ぜんぶ うつっていますか？")
        st.session_state.last_spoken = "camera_check"

    st.markdown(
        render_header("", "カメラを　かくにん　しよう"),
        unsafe_allow_html=True,
    )

    st.info("からだ　ぜんぶ　うつっていますか？")

    left, right = st.columns(2, gap="large")
    with left:
        st.markdown("**チェックポイント**")
        st.markdown(
            "- あたまから　あしのさきまで　うつっているか\n"
            "- りょうてを　ひろげても　きれないか\n"
            "- あしをあげても　がめんに　おさまるか"
        )
    with right:
        render_webcam_panel(max_width_px=PANEL_MAX_WIDTH_PX)

    st.button(
        "だいじょうぶ！",
        type="primary",
        use_container_width=True,
        on_click=on_confirm,
    )
