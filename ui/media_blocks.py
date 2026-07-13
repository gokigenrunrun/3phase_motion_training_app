"""お手本動画・カメラ映像パネルを描画する共通コンポーネント群。

すべて st.iframe()/st.html() 経由で HTML+JS を注入する方式で実装されている。
render_camera_once()/render_webcam_panel() は旧 JS カメラ（getUserMedia）用の
関数。CAMERA_CHECK/DEMO/PRE_MEASURE は streamlit-webrtc
（ui/pre_measure_view.render_webrtc_camera）に置き換わっており、app.py の
実行経路からは呼ばれない。ただし旧フロー用の countdown_view.py 等
（実行時には到達しない phase 分岐からのみ import される）が引き続き
呼び出しているため、関数定義自体は残している。
"""

import json

import streamlit as st


PANEL_MAX_WIDTH_PX = 420
PANEL_HEIGHT_PX = int(PANEL_MAX_WIDTH_PX * 4 / 3)


def render_video_panel(
    *,
    video_filename: str,
    autoplay: bool,
    loop: bool = False,
    loop_count: int = 1,
    max_width_px: int = PANEL_MAX_WIDTH_PX,
    seek_to: float = 0.0,
    stop_at: float | None = None,
    delay_before_play: float = 0.0,
    play_from: float | None = None,
) -> None:
    """お手本動画を st.iframe() で表示します。

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

    動画は static/ から HTTP 配信する（/app/static/{video_filename}）。
    base64 埋め込みをやめたことでブラウザキャッシュが効き、画面遷移ごとの
    再転送がなくなる。
    """
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

    st.iframe(
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
                <source src="/app/static/{video_filename}" type="video/mp4">
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
    """カメラ video 要素を document.body に一度だけ作成し getUserMedia を一度だけ実行する。

    main() の冒頭で呼び出すことで、Streamlit の rerun があっても
    カメラストリームが破棄されない（永続化）。
    描画ループは render_webcam_panel() 側で都度起動する（排他管理）。
    """
    st.html(
        """
        <script>
        (function() {
            // 既に初期化済みならスキップ（rerun 時の重複防止）
            if (window._cameraInitialized) return;
            window._cameraInitialized = true;

            // 隠し container と video を document.body に追加
            var container = document.createElement('div');
            container.id = 'persistentCamera';
            container.style.cssText =
                'position:absolute;left:-9999px;top:-9999px;' +
                'width:1px;height:1px;visibility:hidden;';

            var video = document.createElement('video');
            video.id = 'persistentCameraVideo';
            video.autoplay = true;
            video.muted = true;
            video.playsInline = true;
            video.setAttribute('playsinline', '');

            container.appendChild(video);
            document.body.appendChild(container);

            // getUserMedia で起動
            var md = navigator.mediaDevices;

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
                        window._cameraStream = stream;
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
        unsafe_allow_javascript=True,
    )


def render_webcam_panel(*, max_width_px: int = PANEL_MAX_WIDTH_PX) -> None:
    """3:4 の領域にカメラ映像を表示する。

    canvas プレースホルダーを描画したあと、st.html() で
    requestAnimationFrame ループを起動し、永続 video 要素から
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

    # 2. 描画ループを起動する JS（st.html で確実にスクリプト実行）
    st.html(
        """
        <script>
        (function() {
            // 前回のアニメーションフレームをキャンセル（多重ループ防止）
            if (window._cameraDrawCancel) {
                try {
                    cancelAnimationFrame(window._cameraDrawCancel);
                } catch (e) {}
                window._cameraDrawCancel = null;
            }

            function tryDraw() {
                var canvas = document.getElementById('cameraCanvas');
                var loading = document.getElementById('cameraLoading');
                var video = document.getElementById('persistentCameraVideo');

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
                var placeholder = document.getElementById('cameraPlaceholder');

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
                    window._cameraDrawCancel = requestAnimationFrame(frame);
                }
                window._cameraDrawCancel = requestAnimationFrame(frame);
            }

            // DOM 安定待ち
            setTimeout(tryDraw, 300);
        })();
        </script>
        """,
        unsafe_allow_javascript=True,
    )


def render_demo_video_once(*, video_filename: str, exercise_key: str) -> None:
    """お手本動画の <video> を parent.document に一度だけ作成して永続化する。

    Streamlit の rerun では parent.document.body は破棄されないため、ここで
    作った video 要素と再生位置（currentTime）は rerun をまたいで保持される。
    （カメラの render_camera_once と同じ永続化テクニック。）

    st.html() の呼び出しごとにスクリプトが再実行されるが、video 本体は
    parent 側にあるので、DEMO→PRE_MEASURE の遷移で st.rerun() が走っても
    動画が最初から読み込み直されることがない。

    動画は static/ から HTTP 配信する（/app/static/{video_filename}）。
    base64 埋め込みをやめたことでブラウザキャッシュが効き、同じ種目なら
    2 回目以降は瞬時に読み込まれる。読み込み済みの種目キーを
    session_state で管理し、同じ種目なら src を再設定しない。
    """
    already_loaded = (
        st.session_state.get("_demo_video_loaded_key") == exercise_key
    )

    if already_loaded:
        # src 再設定なし（既に parent に読み込み済み）
        src_js = ""
    else:
        video_src = f"/app/static/{video_filename}"
        src_js = (
            "if (video.dataset.exerciseKey !== KEY) {"
            "  video.dataset.exerciseKey = KEY;"
            "  video.pause();"
            f"  video.src = {json.dumps(video_src)};"
            "  try { video.load(); } catch (e) {}"
            "  video.addEventListener('loadedmetadata', function() {"
            "    try { video.currentTime = 0; } catch (e) {}"
            "  }, { once: true });"
            "}"
        )
        st.session_state["_demo_video_loaded_key"] = exercise_key

    st.html(
        f"""
        <script>
        (function() {{
            var KEY = {json.dumps(exercise_key)};

            var video = document.getElementById('persistentDemoVideo');
            if (!video) {{
                // document.body に隠し video を一度だけ作成（rerun で破棄されない）
                var container = document.createElement('div');
                container.id = 'persistentDemoContainer';
                container.style.cssText =
                    'position:absolute;left:-9999px;top:-9999px;' +
                    'width:1px;height:1px;visibility:hidden;';
                video = document.createElement('video');
                video.id = 'persistentDemoVideo';
                video.muted = true;
                video.defaultMuted = true;
                video.playsInline = true;
                video.setAttribute('playsinline', '');
                video.setAttribute('muted', '');
                video.preload = 'auto';
                container.appendChild(video);
                document.body.appendChild(container);
            }}
            {src_js}
        }})();
        </script>
        """,
        unsafe_allow_javascript=True,
    )


def _build_demo_control_js(phase: str, exercise, delay_ms: int) -> str:
    """フェーズ別に永続 video の currentTime / play / pause を制御する JS を返す。

    DEMO        : 0 秒から再生し demo_duration 秒で停止
    PRE_MEASURE : demo_duration 秒で静止 → delay_ms 後に 0 秒から再生し
                  measure_video_end 秒で停止
    MEASURE     : 0 秒から再生し measure_video_end 秒で停止
    JS は単一波括弧で書く（呼び出し側の f-string にはプレースホルダ置換で
    埋め込むため、ここでブレースをエスケープする必要はない）。
    """
    if phase == "pre_measure":
        return (
            "var DEMO_END=%f, V_END=%f, DELAY=%d;"
            "function holdAt(){ try{video.currentTime=DEMO_END;}catch(e){} video.pause(); }"
            "if (video.readyState>=1) holdAt();"
            "else video.addEventListener('loadedmetadata', holdAt, {once:true});"
            "setTimeout(function(){"
            "  try{video.currentTime=0;}catch(e){}"
            "  var pr=video.play(); if(pr&&pr.catch) pr.catch(function(){});"
            "}, DELAY);"
            "function chkM(){ if(video.currentTime>=V_END){ video.pause(); return; }"
            "  requestAnimationFrame(chkM); }"
            "requestAnimationFrame(chkM);"
        ) % (exercise.demo_duration, exercise.get_measure_video_end(), delay_ms)

    if phase == "measure":
        return (
            "var V_END=%f;"
            "function startM(){ try{video.currentTime=0;}catch(e){}"
            "  var pr=video.play(); if(pr&&pr.catch) pr.catch(function(){}); }"
            "if (video.readyState>=1) startM();"
            "else video.addEventListener('loadedmetadata', startM, {once:true});"
            "function chkM(){ if(video.currentTime>=V_END){ video.pause(); return; }"
            "  requestAnimationFrame(chkM); }"
            "requestAnimationFrame(chkM);"
        ) % (exercise.get_measure_video_end(),)

    # 既定: DEMO
    return (
        "var STOP=%f;"
        "function startDemo(){ try{video.currentTime=0;}catch(e){}"
        "  var pr=video.play(); if(pr&&pr.catch) pr.catch(function(){}); }"
        "if (video.readyState>=1) startDemo();"
        "else video.addEventListener('loadedmetadata', startDemo, {once:true});"
        "function chkD(){ if(video.currentTime>=STOP){ video.pause(); return; }"
        "  requestAnimationFrame(chkD); }"
        "requestAnimationFrame(chkD);"
    ) % (exercise.demo_duration,)


def render_demo_video_panel(
    *,
    exercise,
    phase: str,
    delay_before_play: float = 0.0,
    max_width_px: int = PANEL_MAX_WIDTH_PX,
) -> None:
    """永続 video を canvas に描画しつつ、フェーズ別に再生位置を制御する。

    video 要素そのものは render_demo_video_once() で parent.document に
    永続化されているため、このパネルが rerun で作り直されても動画は
    リロードされない（canvas に現在フレームを描き続けるだけ）。

    Args:
        exercise:          現在の種目（uses_segmented_video=True 前提）
        phase:             'demo' / 'pre_measure' / 'measure'
        delay_before_play: PRE_MEASURE でカウントダウン終了まで待つ秒数
        max_width_px:      パネル最大幅
    """
    # 1. 永続 video を用意（src は種目変更時のみ送る）
    render_demo_video_once(
        video_filename=exercise.video_path.name,
        exercise_key=exercise.key,
    )

    # 2. 3:4 の canvas プレースホルダー（main DOM）
    st.markdown(
        f'<div id="demoVideoPlaceholder" '
        f'style="width:min(100%, {max_width_px}px);aspect-ratio:3/4;'
        f'margin:0 auto;background:#111;border-radius:8px;overflow:hidden;'
        f'position:relative;">'
        f'<canvas id="demoVideoCanvas" '
        f'style="width:100%;height:100%;display:block;"></canvas>'
        f'<div id="demoVideoLoading" style="position:absolute;top:50%;left:50%;'
        f'transform:translate(-50%,-50%);color:#B5D4F4;font-size:14px;">'
        f'どうが　よみこみちゅう...</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # 3. フェーズ別の再生制御 + canvas 描画ループ
    control_js = _build_demo_control_js(
        phase=phase,
        exercise=exercise,
        delay_ms=max(0, int(round(delay_before_play * 1000))),
    )

    panel_js = """
        <script>
        (function() {
            // 永続 video が生成されるまで待ってから制御・描画を始める
            function waitForVideo(attempt) {
                var video = document.getElementById('persistentDemoVideo');
                if (!video) {
                    if (attempt > 60) return;  // 約6秒で諦める
                    setTimeout(function() { waitForVideo(attempt + 1); }, 100);
                    return;
                }
                start(video);
            }

            function start(video) {
            // ── フェーズ別 再生制御 ──
            // __CONTROL_JS__

            // ── 前回の描画ループを停止（多重ループ防止） ──
            if (window._demoDrawCancel) {
                try { cancelAnimationFrame(window._demoDrawCancel); } catch (e) {}
                window._demoDrawCancel = null;
            }

            function tryDraw() {
                var canvas = document.getElementById('demoVideoCanvas');
                var loading = document.getElementById('demoVideoLoading');
                if (!canvas) { setTimeout(tryDraw, 150); return; }
                if (video.readyState < 2) {
                    setTimeout(tryDraw, 150);
                    return;
                }
                startDraw(canvas, loading);
            }

            function startDraw(canvas, loading) {
                if (loading) loading.style.display = 'none';
                var ctx = canvas.getContext('2d');
                var ph = document.getElementById('demoVideoPlaceholder');
                function frame() {
                    var w = ph ? ph.offsetWidth : canvas.offsetWidth;
                    var h = ph ? ph.offsetHeight : canvas.offsetHeight;
                    if (w > 0 && h > 0) {
                        if (canvas.width !== w) canvas.width = w;
                        if (canvas.height !== h) canvas.height = h;
                        var vw = video.videoWidth || 0;
                        var vh = video.videoHeight || 0;
                        if (vw > 0 && vh > 0) {
                            // object-fit: cover 相当（中央クロップ・反転なし）
                            var ca = w / h, va = vw / vh, sx, sy, sw, sh;
                            if (va > ca) { sh = vh; sw = vh * ca; sx = (vw - sw) / 2; sy = 0; }
                            else { sw = vw; sh = vw / ca; sx = 0; sy = (vh - sh) / 2; }
                            ctx.drawImage(video, sx, sy, sw, sh, 0, 0, w, h);
                        }
                    }
                    window._demoDrawCancel = requestAnimationFrame(frame);
                }
                window._demoDrawCancel = requestAnimationFrame(frame);
            }

            setTimeout(tryDraw, 100);
            }  // end start()

            waitForVideo(0);
        })();
        </script>
    """.replace("// __CONTROL_JS__", control_js)

    st.html(panel_js, unsafe_allow_javascript=True)


def get_panel_height(max_width_px: int = PANEL_MAX_WIDTH_PX) -> int:
    """3:4 パネルを iframe に収めるための共通高さです。"""
    return int(max_width_px * 4 / 3)
