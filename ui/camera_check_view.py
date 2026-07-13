"""カメラ画角の確認画面（CAMERA_CHECK フェーズ）。"""

from typing import Callable

import streamlit as st

from exercises import Exercise
from ui.pre_measure_view import render_webrtc_camera
from ui.styles import render_header, speak


def render_camera_check_view(
    on_confirm: Callable[[], None],
    exercise: Exercise,
) -> None:
    """計測前にカメラの画角を確認する画面を描画する。

    CSS は app.py の main() で注入済みのため、ここでは呼ばない。
    ここで WebRTC 接続を確立し、以降 DEMO → PRE_MEASURE まで同じ
    peer connection を維持することで接続待ちをなくす。

    Args:
        on_confirm: 「だいじょうぶ！」ボタン押下後のフェーズ遷移コールバック
        exercise:   最初の種目（WebRTC の key に使用）
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
        # DEMO・PRE_MEASURE でも同じ key で接続を維持する。
        render_webrtc_camera(exercise, visible=True)

    st.button(
        "だいじょうぶ！",
        type="primary",
        use_container_width=True,
        on_click=on_confirm,
    )
