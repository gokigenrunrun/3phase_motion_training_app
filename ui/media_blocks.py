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
    loop: bool = False,
    loop_count: int = 1,
    max_width_px: int = PANEL_MAX_WIDTH_PX,
    seek_to: float = 0.0,
    stop_at: float | None = None,
    delay_before_play: float = 0.0,
    play_from: float | None = None,
) -> None:
    """お手本動画を components.html() の iframe 内で表示します。

    再生回数の制御:
    - loop=True: HTML の loop 属性で**無限ループ**（PRE_MEASURE 等での背景再生用）
    - loop=False, loop_count=N: JS の 'ended' イベントで **N 回再生して停止**

    区間再生モード（stop_at を指定した場合・loop/loop_count より優先）:
    - 最初に seek_to の位置へシークする
    - delay_before_play 秒だけ静止してから play_from（既定 seek_to）へ
      シークして再生を開始する
    - currentTime が stop_at に達したら一時停止する
    （バンザイの「DEMO=0〜16 秒」「計測=16 秒で静止→0 秒から 34 秒まで」用）

    Chrome の自動再生ポリシーをかいくぐるために以下を全て満たす:
    - autoplay 属性 + muted 属性 + playsinline 属性
    - JS で .play() を強制 + ユーザー操作でアンロック
    """
    p = Path(video_path)
    video_b64 = _load_video_base64(str(p), p.stat().st_mtime_ns)

    segmented = stop_at is not None

    if segmented:
        # 区間再生モード: HTML 属性では制御せず、すべて JS で行う
        autoplay_attr = ""
        loop_attr = ""
        resolved_play_from = play_from if play_from is not None else seek_to
        delay_ms = max(0, int(round(delay_before_play * 1000)))
        loop_js = f"""
                var SEEK_TO = {float(seek_to)};
                var STOP_AT = {float(stop_at)};
                var PLAY_FROM = {float(resolved_play_from)};
                var DELAY_MS = {delay_ms};

                function seekInit() {{
                    try {{ v.currentTime = SEEK_TO; }} catch (e) {{}}
                }}
                // currentTime のセットにはメタデータ読み込みが必要
                if (v.readyState >= 1) {{ seekInit(); }}
                else {{ v.addEventListener('loadedmetadata', seekInit, {{ once: true }}); }}

                // 停止位置の監視（stop_at に達したら一時停止）
                v.addEventListener('timeupdate', function() {{
                    if (v.currentTime >= STOP_AT) {{ v.pause(); }}
                }});

                function beginSegmentPlay() {{
                    try {{ v.currentTime = PLAY_FROM; }} catch (e) {{}}
                    var pr = v.play();
                    if (pr && pr.catch) {{
                        pr.catch(function(e) {{
                            console.log('segment play blocked:', e);
                        }});
                    }}
                }}

                if (DELAY_MS > 0) {{
                    // 遅延中は SEEK_TO の位置で静止（カウントダウン中の 16 秒静止）
                    v.pause();
                    setTimeout(beginSegmentPlay, DELAY_MS);
                }} else {{
                    beginSegmentPlay();
                }}
                // 自動再生がブロックされても、遅延後の再生はユーザー操作後なので
                // 通常は play() が通る。muted のため大半の環境で即時再生可。
        """
    elif loop:
        # 無限ループモード: HTML loop 属性のみ
        autoplay_attr = "autoplay" if autoplay else ""
        loop_attr = "loop"
        loop_js = ""
    else:
        # 回数指定モード: JS で正確に N 回再生
        autoplay_attr = "autoplay" if autoplay else ""
        loop_attr = ""
        loop_js = f"""
                var loopCount = {max(1, int(loop_count))};
                var playCount = 0;
                v.addEventListener('ended', function() {{
                    playCount++;
                    if (playCount < loopCount) {{
                        v.currentTime = 0;
                        v.play();
                    }}
                }});
        """

    # 区間再生モードでは再生タイミングを loop_js 側が完全に制御するため、
    # 汎用の即時 .play() ブロックは挿入しない（カウントダウン中に
    # 動画が再生開始してしまうのを防ぐ）。
    if segmented:
        autoplay_js = ""
    else:
        autoplay_js = """
                function tryPlay() {
                    var p = v.play();
                    if (p && p.catch) {
                        p.catch(function(e) {
                            console.log('otehon video autoplay blocked:', e);
                        });
                    }
                }

                // 即時 + 500ms 後に再試行（DOM 確定待ち）
                tryPlay();
                setTimeout(tryPlay, 500);

                // 自動再生がブロックされた場合は最初のユーザー操作で再生
                var unlock = function() {
                    if (v.paused) tryPlay();
                };
                try {
                    window.parent.document.addEventListener('click', unlock, { once: true, capture: true });
                    window.parent.document.addEventListener('keydown', unlock, { once: true, capture: true });
                } catch (e) {
                    document.addEventListener('click', unlock, { once: true, capture: true });
                }
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
                border-radius: 8px;
                overflow: hidden;
            }}
            video {{
                width: 100%;
                height: 100%;
                aspect-ratio: 3 / 4;
                object-fit: cover;
                display: block;
                background: #111;
                border: 0;
                border-radius: 8px;
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
                v.muted = true;
                {autoplay_js}
                {loop_js}
            }})();
        </script>
        """,
        height=get_panel_height(max_width_px),
    )


def render_camera_once() -> None:
    """カメラ video 要素を parent.body に一度だけ作成し getUserMedia を一度だけ実行する。

    main() の冒頭で呼び出すことで、Streamlit の rerun があっても
    カメラストリームが破棄されない（永続化）。
    描画ループは render_webcam_panel() 側で都度起動する（排他管理）。
    """
    components.html(
        """
        <script>
        (function() {
            var parent = window.parent;
            var pdoc = parent.document;

            // 既に初期化済みならスキップ（rerun 時の重複防止）
            if (parent._cameraInitialized) return;
            parent._cameraInitialized = true;

            // 隠し container と video を parent.body に追加
            var container = pdoc.createElement('div');
            container.id = 'persistentCamera';
            container.style.cssText =
                'position:absolute;left:-9999px;top:-9999px;' +
                'width:1px;height:1px;visibility:hidden;';

            var video = pdoc.createElement('video');
            video.id = 'persistentCameraVideo';
            video.autoplay = true;
            video.muted = true;
            video.playsInline = true;
            video.setAttribute('playsinline', '');

            container.appendChild(video);
            pdoc.body.appendChild(container);

            // getUserMedia で起動
            var md = null;
            try {
                md = (parent.navigator && parent.navigator.mediaDevices)
                    || navigator.mediaDevices;
            } catch (e) { md = navigator.mediaDevices; }

            if (!md || !md.getUserMedia) {
                console.error('[camera] mediaDevices 不在');
                return;
            }

            // 段階的に制約を緩めて再試行（3:4 縦長を優先・カメラが対応しなければ広い解像度にフォールバック）
            var constraintsList = [
                { video: { width: { ideal: 720 }, height: { ideal: 960 },
                           aspectRatio: { ideal: 3/4 },
                           facingMode: 'user' }, audio: false },
                { video: { facingMode: 'user' }, audio: false },
                { video: true, audio: false },
            ];

            (async function tryStart() {
                for (var i = 0; i < constraintsList.length; i++) {
                    try {
                        var stream = await md.getUserMedia(constraintsList[i]);
                        video.srcObject = stream;
                        parent._cameraStream = stream;
                        // メタデータ読み込み完了後に明示的に play()
                        video.onloadedmetadata = function() {
                            video.play().then(function() {
                                console.log('[camera] video playing');
                            }).catch(function(e) {
                                console.log('[camera] play error:', e);
                            });
                        };
                        console.log('[camera] started successfully');
                        return;
                    } catch (err) {
                        console.warn('[camera] constraints[' + i + '] failed:',
                                     err.name, err.message);
                    }
                }
            })();
        })();
        </script>
        """,
        height=0,
    )


def render_webcam_panel(*, max_width_px: int = PANEL_MAX_WIDTH_PX) -> None:
    """3:4 の領域にカメラ映像を表示する。

    canvas プレースホルダーを描画したあと、components.html() で
    requestAnimationFrame ループを起動し、parent の永続 video 要素から
    フレームを描画する。前回ループは `_cameraDrawCancel` でキャンセルする
    ことで多重起動を防ぐ。
    """
    # 1. 3:4 のプレースホルダー + canvas + ローディング表示（main DOM 上）
    # aspect-ratio:3/4 で高さがウィンドウ幅から自動計算される
    st.markdown(
        f'<div id="cameraPlaceholder" '
        f'style="width:min(100%, {max_width_px}px);aspect-ratio:3/4;'
        f'margin:0 auto;background:#1a1a1a;border-radius:8px;overflow:hidden;'
        f'position:relative;">'
        f'<canvas id="cameraCanvas" data-camera-canvas="1" '
        f'style="width:100%;height:100%;display:block;"></canvas>'
        f'<div id="cameraLoading" style="position:absolute;top:50%;left:50%;'
        f'transform:translate(-50%,-50%);color:#B5D4F4;font-size:14px;">'
        f'カメラ　じゅんびちゅう...</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # 2. 描画ループを起動する JS（components.html で確実にスクリプト実行）
    components.html(
        """
        <script>
        (function() {
            var parent = window.parent;
            var pdoc = parent.document;

            // 前回のアニメーションフレームをキャンセル（多重ループ防止）
            if (parent._cameraDrawCancel) {
                try {
                    parent.cancelAnimationFrame(parent._cameraDrawCancel);
                } catch (e) {}
                parent._cameraDrawCancel = null;
            }

            function tryDraw() {
                var canvas = pdoc.getElementById('cameraCanvas');
                var loading = pdoc.getElementById('cameraLoading');
                var video = pdoc.getElementById('persistentCameraVideo');

                // 必要な要素が揃うまでリトライ
                if (!canvas || !video || !video.srcObject) {
                    setTimeout(tryDraw, 200);
                    return;
                }

                // メタデータ読み込み待ち
                if (video.readyState < 2) {
                    video.addEventListener('canplay', function() {
                        startDrawing(canvas, video, loading);
                    }, { once: true });
                    return;
                }

                startDrawing(canvas, video, loading);
            }

            function startDrawing(canvas, video, loading) {
                if (loading) loading.style.display = 'none';
                var ctx = canvas.getContext('2d');
                var placeholder = pdoc.getElementById('cameraPlaceholder');

                function frame() {
                    var w = placeholder ? placeholder.offsetWidth : canvas.offsetWidth;
                    var h = placeholder ? placeholder.offsetHeight : canvas.offsetHeight;

                    if (w > 0 && h > 0) {
                        if (canvas.width !== w) canvas.width = w;
                        if (canvas.height !== h) canvas.height = h;

                        var vw = video.videoWidth || 0;
                        var vh = video.videoHeight || 0;

                        if (vw > 0 && vh > 0) {
                            // object-fit: cover 相当: video のアスペクト比を保ちつつ canvas を埋める
                            // canvas より video が横長なら左右をクロップ、縦長なら上下をクロップ
                            var canvasAspect = w / h;
                            var videoAspect = vw / vh;
                            var sx, sy, sw, sh;
                            if (videoAspect > canvasAspect) {
                                sh = vh;
                                sw = vh * canvasAspect;
                                sx = (vw - sw) / 2;
                                sy = 0;
                            } else {
                                sw = vw;
                                sh = vw / canvasAspect;
                                sx = 0;
                                sy = (vh - sh) / 2;
                            }

                            // 左右反転して描画（鏡像）
                            ctx.save();
                            ctx.translate(w, 0);
                            ctx.scale(-1, 1);
                            ctx.drawImage(video, sx, sy, sw, sh, 0, 0, w, h);
                            ctx.restore();
                        }
                    }
                    parent._cameraDrawCancel =
                        parent.requestAnimationFrame(frame);
                }
                parent._cameraDrawCancel =
                    parent.requestAnimationFrame(frame);
            }

            // DOM 安定待ち
            setTimeout(tryDraw, 300);
        })();
        </script>
        """,
        height=0,
    )


def get_panel_height(max_width_px: int = PANEL_MAX_WIDTH_PX) -> int:
    """3:4 パネルを iframe に収めるための共通高さです。"""
    return int(max_width_px * 4 / 3)
