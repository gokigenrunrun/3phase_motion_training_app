import base64
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components


PANEL_MAX_WIDTH_PX = 420
PANEL_HEIGHT_PX = int(PANEL_MAX_WIDTH_PX * 4 / 3)


@st.cache_data(show_spinner=False)
def _load_video_base64(video_path: str, mtime_ns: int) -> str:
    """ローカル動画を base64 文字列として返す（components.html 埋め込み用）。

    mtime_ns をキャッシュキーに含めることで、ファイル差し替え時に
    自動でキャッシュを無効化する。
    """
    return base64.b64encode(Path(video_path).read_bytes()).decode("utf-8")


def render_video_panel(
    *,
    video_path: str,
    autoplay: bool,
    loop: bool,
    max_width_px: int = PANEL_MAX_WIDTH_PX,
) -> None:
    """お手本動画を components.html() の iframe 内で表示します。

    Chrome の自動再生ポリシーをかいくぐるために以下を全て満たす：
    - autoplay 属性
    - muted 属性（muted でない video は自動再生不可）
    - playsinline 属性（iOS Safari 対応）
    属性のみで反映されない場合のフォールバックとして
    setTimeout 経由で .play() を強制呼び出しする。
    自動再生がブロックされた場合は最初のユーザー操作で再試行する。
    """
    p = Path(video_path)
    video_b64 = _load_video_base64(str(p), p.stat().st_mtime_ns)
    autoplay_attr = "autoplay" if autoplay else ""
    loop_attr = "loop" if loop else ""

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
            }}
            video {{
                width: 100%;
                height: 100%;
                object-fit: cover;
                display: block;
                background: #111;
                border: 0;
            }}
        </style>
        <div class="media-root">
            <video
                id="otehon-video"
                {autoplay_attr}
                {loop_attr}
                muted
                playsinline
                preload="auto"
            >
                <source src="data:video/mp4;base64,{video_b64}" type="video/mp4">
            </video>
        </div>
        <script>
            (function() {{
                var v = document.getElementById('otehon-video');
                if (!v) return;
                v.muted = true;  // 念のため JS でも muted を強制

                function tryPlay() {{
                    var p = v.play();
                    if (p && p.catch) {{
                        p.catch(function(e) {{
                            console.log('otehon video autoplay blocked:', e);
                        }});
                    }}
                }}

                // 即時 + 500ms 後に再試行（DOM 確定待ち）
                tryPlay();
                setTimeout(tryPlay, 500);

                // 自動再生がブロックされた場合は最初のユーザー操作で再生
                var unlock = function() {{
                    if (v.paused) tryPlay();
                }};
                try {{
                    window.parent.document.addEventListener('click', unlock, {{ once: true, capture: true }});
                    window.parent.document.addEventListener('keydown', unlock, {{ once: true, capture: true }});
                }} catch (e) {{
                    document.addEventListener('click', unlock, {{ once: true, capture: true }});
                }}
            }})();
        </script>
        """,
        height=get_panel_height(max_width_px),
    )


def render_webcam_panel(*, max_width_px: int = PANEL_MAX_WIDTH_PX) -> None:
    """3:4 の固定領域に Web カメラ映像だけを表示します。

    カメラのライブプレビューは getUserMedia API が必要なため、
    やむを得ず components.html()（iframe）を使用する。
    """
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
                    transform: scaleX(-1);
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
