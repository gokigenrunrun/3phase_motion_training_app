import base64
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components


PANEL_MAX_WIDTH_PX = 270
PANEL_HEIGHT_PX = int(PANEL_MAX_WIDTH_PX * 4 / 3)


@st.cache_data(show_spinner=False)
def load_video_base64(video_path: str) -> str:
    """ローカル動画を HTML 埋め込み用の base64 に変換します。"""

    video_bytes = Path(video_path).read_bytes()
    return base64.b64encode(video_bytes).decode("utf-8")


def render_video_panel(
    *,
    video_path: str,
    autoplay: bool,
    loop: bool,
    max_width_px: int = PANEL_MAX_WIDTH_PX,
) -> None:
    """3:4 の固定領域に動画を収めて表示します。"""

    autoplay_attr = "autoplay" if autoplay else ""
    loop_attr = "loop" if loop else ""
    video_base64 = load_video_base64(video_path)
    html = f"""
    <style>
        html, body {{
            margin: 0;
            padding: 0;
            overflow: hidden;
            background: transparent;
        }}
        .media-root {{
            width: min(100%, {max_width_px}px);
            aspect-ratio: 3 / 4;
            margin: 0 auto;
            padding: 0;
            background: transparent;
        }}
    </style>
    <div class="media-root">
        <video
            {autoplay_attr}
            {loop_attr}
            muted
            playsinline
            style="
                width: 100%;
                height: 100%;
                object-fit: cover;
                display: block;
                background: #111;
                border: 0;
            "
        >
            <source src="data:video/mp4;base64,{video_base64}" type="video/mp4">
        </video>
    </div>
    """
    components.html(html, height=get_panel_height(max_width_px))


def render_webcam_panel(*, max_width_px: int = PANEL_MAX_WIDTH_PX) -> None:
    """3:4 の固定領域に Web カメラ映像だけを表示します。"""

    components.html(
        f"""
        <style>
            html, body {{
                margin: 0;
                padding: 0;
                overflow: hidden;
                background: transparent;
            }}
            .media-root {{
                width: min(100%, {max_width_px}px);
                aspect-ratio: 3 / 4;
                margin: 0 auto;
                padding: 0;
                background: transparent;
                position: relative;
            }}
        </style>
        <div class="media-root">
            <video
                id="camera-preview"
                autoplay
                muted
                playsinline
                style="
                    width: 100%;
                    height: 100%;
                    object-fit: cover;
                    display: block;
                    background: #111;
                    border: 0;
                "
            ></video>
        </div>
        <script>
            const video = document.getElementById("camera-preview");
            async function startCamera() {{
                try {{
                    const stream = await navigator.mediaDevices.getUserMedia({{
                        video: {{
                            facingMode: "user",
                            aspectRatio: 0.75
                        }},
                        audio: false
                    }});
                    video.srcObject = stream;
                }} catch (error) {{
                    console.error("camera error", error);
                }}
            }}
            startCamera();
        </script>
        """,
        height=get_panel_height(max_width_px),
    )


def get_panel_height(max_width_px: int = PANEL_MAX_WIDTH_PX) -> int:
    """3:4 パネルを iframe に収めるための共通高さです。"""

    return int(max_width_px * 4 / 3)
