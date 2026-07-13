"""計測前 + 計測中の JS アニメーション完結画面（PRE_MEASURE フェーズ）。

JavaScript は以下の **画面表示**だけを担当する:
1. 画面中央で青円のカウントダウン（3秒）
2. 0 でオレンジに変わり「Start!!」表示（0.8秒）
3. 円がヘッダー右端へ移動・縮小（0.7秒）
4. ヘッダー右端でオレンジのタイマー（exercise.demo_duration 秒）
5. 0 でオーバーレイ DOM をクリーンアップ

**フェーズ遷移は Python 側**が担当する（state.PHASE_DURATIONS と
phase_controller の組み合わせで `demo_duration + 4.5s` 経過後に
complete_measurement_phase を呼ぶ）。
"""

import streamlit as st
from streamlit_webrtc import WebRtcMode, webrtc_streamer
from streamlit_webrtc.config import VideoHTMLAttributes

from exercises import Exercise
from logic.measurement import start_measurement
from logic.pose_capture import PoseCaptureProcessor
from state import get_remaining_from_snapshot
from ui.media_blocks import (
    PANEL_MAX_WIDTH_PX,
    render_demo_video_panel,
    render_video_panel,
)
from ui.styles import render_header, speak


# WebRTC の NAT 越え用 STUN サーバ（ローカルでは無くても動くが、
# Streamlit Cloud 等のデプロイ時に接続確立しやすくする）
_RTC_CONFIGURATION = {
    "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
}


# JS カウントダウンアニメーションの総尺（秒）。
# カウントダウン 3s + Start!! 0.8s + ヘッダーへの移動 0.7s = 4.5s。
# 区間再生の動画はこの時間だけ静止してから計測再生を開始する。
PRE_MEASURE_ANIM_SECONDS = 4.5

# 表示時の <video> スタイル。webrtc_streamer コンポーネントは iframe 内に
# 描画されるため、親ページ側から st.markdown() で注入した CSS は内部の
# <video> 要素に届かない。video_html_attrs はコンポーネントへの props として
# iframe 内に直接反映されるため、こちらでサイズを明示する。
_VISIBLE_VIDEO_HTML_ATTRS = VideoHTMLAttributes(
    autoPlay=True,
    muted=True,
    playsInline=True,
    style={
        "width": "100%",
        "height": "auto",
        "maxHeight": "480px",
        "objectFit": "contain",
        "borderRadius": "12px",
    },
)


@st.fragment(run_every=1.0)
def _pre_measure_watcher(
    phase_started_at: float | None,
    phase_duration: float,
) -> None:
    """フェーズ終了を 1 秒ごとに監視する fragment。

    画面には何も描画しない。total duration 経過で full rerun を発火し、
    phase_controller が complete_measurement_phase で次の TRANSITION/FINISHED
    へ進める。
    """
    remaining = max(0.0, get_remaining_from_snapshot(
        started_at=phase_started_at,
        duration=phase_duration,
    ))
    if remaining <= 0:
        st.rerun()


def _ensure_pose_processor() -> PoseCaptureProcessor:
    """PoseCaptureProcessor をセッションにつき1つだけ作成し、種目が変わっても使い回す。

    CAMERA_CHECK・DEMO・PRE_MEASURE すべてから呼ばれる。以前は種目キーが
    変わるたびにインスタンスを破棄・再生成しており、MediaPipe Pose の
    モデルロード（軽くない処理）が1セッションで最大3回発生していた。
    ランドマークバッファは種目ごとに start_capture() が必ずリセットする
    ため、インスタンス自体を使い回しても前の種目のデータが混ざることは
    なく、破棄・再生成する理由がない。
    """
    if "pose_processor" not in st.session_state:
        st.session_state.pose_processor = PoseCaptureProcessor()

    return st.session_state.pose_processor


def render_webrtc_camera(
    exercise: Exercise,
    *,
    visible: bool = True,
):
    """全フェーズ共通の WebRTC カメラ描画。

    CAMERA_CHECK・DEMO・PRE_MEASURE のすべてで同じ key
    (f"pose_capture_{exercise.key}") と同じ processor インスタンスを使うため、
    Streamlit は同一コンポーネント・同一 peer connection として扱う。
    これにより DEMO → PRE_MEASURE 遷移時の接続待ちがなくなる。
    骨格は PoseCaptureProcessor 側で常に描画される。

    Args:
        exercise: 現在の種目
        visible:  False の場合は画面外へ押し出す（接続・推論は継続する）

    Returns:
        webrtc_streamer() が返す WebRtcStreamerContext
    """
    processor = _ensure_pose_processor()

    def _mount():
        """visible/非visible どちらの分岐からも同じ引数で webrtc_streamer を呼ぶための内部ヘルパー。"""
        return webrtc_streamer(
            key=f"pose_capture_{exercise.key}",
            mode=WebRtcMode.SENDRECV,
            rtc_configuration=_RTC_CONFIGURATION,
            video_processor_factory=lambda: processor,
            media_stream_constraints={
                "video": {"width": 720, "height": 960},
                "audio": False,
            },
            video_html_attrs=_VISIBLE_VIDEO_HTML_ATTRS if visible else None,
            async_processing=True,
            desired_playing_state=True,
        )

    if visible:
        webrtc_ctx = _mount()
    else:
        # 接続・推論は維持したまま、高さ1pxのコンテナに閉じ込めて視覚的に隠す。
        # 以前は position:absolute + 汎用CSSセレクタ（[data-testid='stCustomComponentV1']）
        # で画面外に押し出していたが、そのスタイルが rerun をまたいで残留し、
        # 後続フェーズの「表示すべき」コンポーネントまで巻き込んで消してしまう
        # 不具合があった。st.container はコンポーネントごとにスコープが閉じるため
        # 他フェーズへ影響しない。display:none にしないのは iframe 内の JS/映像
        # 処理を止めないため。
        with st.container(height=1, border=False):
            webrtc_ctx = _mount()

    # プロセッサ参照を session_state に保存（stop_measurement から参照する）
    if webrtc_ctx.video_processor:
        st.session_state._webrtc_ctx = webrtc_ctx

    return webrtc_ctx


def _render_measure_webrtc_camera(exercise: Exercise) -> None:
    """PRE_MEASURE 専用: カメラを表示し、計測を開始する。"""
    webrtc_ctx = render_webrtc_camera(exercise, visible=True)

    if webrtc_ctx.video_processor:
        # この PRE_MEASURE 突入につき 1 回だけ計測を開始する。
        # phase_started_at をキーにして二重開始を防ぐ。
        started_key = st.session_state.get("phase_started_at")
        if st.session_state.get("_capture_started_at") != started_key:
            start_measurement(exercise)
            st.session_state._capture_started_at = started_key
            st.session_state.measurement_running = True


def render_pre_measure_view(
    exercise: Exercise,
    *,
    phase_started_at: float | None,
    phase_duration: float,
) -> None:
    """PRE_MEASURE 画面を描画する。

    Args:
        exercise:         現在の種目
        phase_started_at: フェーズ開始時刻
        phase_duration:   demo_duration + 4.5（JS アニメ全体の長さ）
    """
    # 音声案内（種目ごとに 1 回・カウントダウン開始時）
    # 「スタート！」は JS 側でカウントダウン残り 0.5 秒のタイミングで読み上げる
    spoken_key = f"start_display_{st.session_state.get('exercise_index', 0)}"
    if st.session_state.get("last_spoken") != spoken_key:
        speak("つぎは いっしょに やってみよう！")
        st.session_state.last_spoken = spoken_key

    # ヘッダー
    st.markdown(
        render_header("⏱", "じゅんびして　ください！"),
        unsafe_allow_html=True,
    )

    # 動画・カメラの 2 カラム
    left, right = st.columns(2, gap="large")
    with left:
        st.write("おてほんどうが")
        if exercise.uses_segmented_video:
            # 永続 video を canvas に描画。カウントダウン中は DEMO 終了位置
            # （demo_duration 秒）で静止し、アニメーション終了後に 0 秒から
            # 計測区間（〜measure_video_end 秒）を再生する。DEMO から同じ
            # video 要素を使い続けるため、遷移時にリロードされない。
            render_demo_video_panel(
                exercise=exercise,
                phase="pre_measure",
                delay_before_play=PRE_MEASURE_ANIM_SECONDS,
                max_width_px=PANEL_MAX_WIDTH_PX,
            )
        else:
            render_video_panel(
                video_filename=exercise.video_path.name,
                autoplay=True,
                loop=True,
                max_width_px=PANEL_MAX_WIDTH_PX,
            )
    with right:
        st.write("あなたのうごき")
        # CAMERA_CHECK/DEMO から接続を引き継いだ WebRTC カメラを表示し、
        # 骨格描画と計測記録を開始する。
        _render_measure_webrtc_camera(exercise)

    # JS アニメーション注入（多重起動は JS 側のフラグで防止）
    # 計測時間 = exercise.get_measure_duration()（四捨五入）
    measure_duration = max(
        1,
        int(round(exercise.get_measure_duration())),
    )
    st.html(
        _build_animation_html(measure_duration=measure_duration),
        unsafe_allow_javascript=True,
    )

    # Python 側 watcher（1 秒ごとに残り時間チェック・0 で full rerun）
    _pre_measure_watcher(
        phase_started_at=phase_started_at,
        phase_duration=phase_duration,
    )


def _build_animation_html(measure_duration: int) -> str:
    """カウントダウン → 移動アニメ → 計測タイマー の JS+HTML を返す。

    DOM 要素は document.body に直接 append するため画面全体を覆う・移動できる。
    完了時は DOM のクリーンアップだけ行う
    （フェーズ遷移は Python 側 watcher fragment が担当）。
    """
    return f"""
    <script>
    (function() {{
        var parent = window;
        var pdoc = document;

        // 多重起動防止
        if (parent._preMeasureRunning) return;
        parent._preMeasureRunning = true;

        var COUNTDOWN_SEC = 3;
        var MEASURE_SEC = {measure_duration};
        var CIRC = 402.12;  // 2 * Math.PI * 64

        // ── オーバーレイ背景 ──
        var overlay = pdoc.createElement('div');
        overlay.id = '_pmOverlay';
        overlay.style.cssText =
            'position:fixed;top:0;left:0;right:0;bottom:0;' +
            'background:rgba(0,0,0,0.35);z-index:999;' +
            'transition:opacity 0.5s ease;pointer-events:none;';
        pdoc.body.appendChild(overlay);

        // ── タイマーコンテナ ──
        var timer = pdoc.createElement('div');
        timer.id = '_pmTimer';
        timer.style.cssText =
            'position:fixed;z-index:1000;pointer-events:none;' +
            'width:160px;height:160px;';
        timer.innerHTML = (
            '<svg width="100%" height="100%" viewBox="0 0 160 160" ' +
            'xmlns="http://www.w3.org/2000/svg">' +
            '<circle cx="80" cy="80" r="64" fill="none" ' +
            'stroke="rgba(255,255,255,0.2)" stroke-width="10"/>' +
            '<circle id="_pmArc" cx="80" cy="80" r="64" fill="none" ' +
            'stroke="#378ADD" stroke-width="10" ' +
            'stroke-dasharray="402.12" stroke-dashoffset="0" ' +
            'stroke-linecap="round" transform="rotate(-90 80 80)"/>' +
            // 内側円: 移動後にヘッダー色 (#378ADD) に変更する
            '<circle id="_pmInner" cx="80" cy="80" r="54" ' +
            'fill="rgba(0,0,0,0.5)"/>' +
            '<text id="_pmText" x="80" y="96" text-anchor="middle" ' +
            'fill="white" font-size="48" font-weight="700" ' +
            'font-family="sans-serif">3</text>' +
            '</svg>'
        );
        pdoc.body.appendChild(timer);

        var arc = timer.querySelector('#_pmArc');
        var text = timer.querySelector('#_pmText');
        var inner = timer.querySelector('#_pmInner');

        // Web Speech API ヘルパー
        function speakJS(textVal) {{
            var synth = window.speechSynthesis;
            var Utterance = window.SpeechSynthesisUtterance;
            if (!synth || !Utterance) return;
            synth.cancel();
            var u = new Utterance(textVal);
            u.lang = 'ja-JP';
            u.rate = 0.85;
            u.pitch = 1.1;
            u.volume = (window._speechVolume !== undefined) ? window._speechVolume : 0.8;
            synth.speak(u);
        }}

        function centerTimer() {{
            timer.style.left = (parent.innerWidth/2 - 80) + 'px';
            timer.style.top  = (parent.innerHeight/2 - 80) + 'px';
        }}
        centerTimer();

        function setArc(curr, total) {{
            arc.setAttribute('stroke-dashoffset',
                (CIRC * (1 - curr/total)).toFixed(2));
        }}

        function cleanup() {{
            try {{
                if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
                if (timer.parentNode)   timer.parentNode.removeChild(timer);
            }} catch (e) {{}}
            parent._preMeasureRunning = false;
        }}

        // フェーズ1: カウントダウン 3 → 2 → 1
        // 100ms 間隔で減らし、残り 0.5 秒で「スタート！」を発話する
        var remaining = COUNTDOWN_SEC;
        text.textContent = remaining;
        setArc(remaining, COUNTDOWN_SEC);

        var startSpoken = false;
        var cdInterval = setInterval(function() {{
            remaining -= 0.1;

            // 残り 0.5 秒で 1 回だけ「スタート！」を読み上げる
            if (!startSpoken && remaining <= 0.5) {{
                startSpoken = true;
                speakJS('スタート！');
            }}

            if (remaining > 0.05) {{
                // 整数表示は切り上げ（残り 2.7 → "3"、残り 1.0 → "1"）
                var displayed = Math.max(1, Math.ceil(remaining));
                text.textContent = displayed;
                setArc(displayed, COUNTDOWN_SEC);
            }} else {{
                clearInterval(cdInterval);
                showStart();
            }}
        }}, 100);

        // フェーズ2: Start!! 表示
        function showStart() {{
            arc.setAttribute('stroke', '#FF8C00');
            setArc(1, 1);
            text.textContent = 'Start!!';
            text.setAttribute('font-size', '28');
            text.setAttribute('y', '92');
            setTimeout(moveToHeader, 800);
        }}

        // フェーズ3: ヘッダー右端の中央へ移動・縮小（64×64）
        function moveToHeader() {{
            // データ属性で確実にヘッダー要素を取得して bounding rect を測る。
            // 「ヘッダー中央 ＝ タイマー中央」になるよう着地座標を計算する。
            var headerEl = pdoc.querySelector('[data-app-header]');
            var targetLeft, targetTop;

            if (headerEl) {{
                var hRect = headerEl.getBoundingClientRect();
                console.log('[pre_measure] header rect:', hRect);
                var headerCenterY = hRect.top + hRect.height / 2;
                targetTop  = headerCenterY - 32;       // 32 = timer 高さ / 2
                targetLeft = hRect.right - 20 - 64;    // 右 padding(20) + timer 幅(64)
            }} else {{
                // フォールバック: コンテンツ領域から計算
                var mainBlock = pdoc.querySelector(
                    'section[data-testid="stMain"] > div'
                );
                if (mainBlock) {{
                    var mRect = mainBlock.getBoundingClientRect();
                    // ヘッダー center ≒ mRect.top - 16(margin) + 44(高さ半分) = mRect.top + 28
                    var fallbackCenter = mRect.top + 28;
                    targetTop  = fallbackCenter - 32;       // = mRect.top - 4
                    targetLeft = mRect.right + 16 - 20 - 64;
                }} else {{
                    targetTop  = 12;
                    targetLeft = parent.innerWidth - 20 - 64;
                }}
            }}
            console.log('[pre_measure] target:', targetLeft, targetTop);

            timer.style.transition =
                'left 0.7s cubic-bezier(0.4,0,0.2,1),' +
                'top 0.7s cubic-bezier(0.4,0,0.2,1),' +
                'width 0.7s cubic-bezier(0.4,0,0.2,1),' +
                'height 0.7s cubic-bezier(0.4,0,0.2,1)';
            timer.style.left   = targetLeft + 'px';
            timer.style.top    = targetTop + 'px';
            timer.style.width  = '64px';
            timer.style.height = '64px';
            overlay.style.opacity = '0';
            setTimeout(startMeasureTimer, 750);
        }}

        // フェーズ4: 測定タイマー
        function startMeasureTimer() {{
            // 内側円をヘッダーと同じ青に切り替えて一体感を出す
            inner.setAttribute('fill', '#378ADD');
            // 縮小後でも読みやすいよう viewBox 内のフォントサイズ・位置を調整
            text.setAttribute('font-size', '52');
            text.setAttribute('y', '98');

            // ヘッダーのタイトルを計測中のメッセージに切り替える
            var titleEl = pdoc.querySelector('[data-app-header-title]');
            if (titleEl) {{
                titleEl.textContent = 'いっしょに　やってみよう！';
            }}

            var measureRemaining = MEASURE_SEC;
            text.textContent = measureRemaining;
            setArc(measureRemaining, MEASURE_SEC);
            var measureInterval = setInterval(function() {{
                measureRemaining--;
                if (measureRemaining >= 0) {{
                    text.textContent = measureRemaining;
                    setArc(measureRemaining, MEASURE_SEC);
                }}
                if (measureRemaining <= 0) {{
                    clearInterval(measureInterval);
                    cleanup();
                    // フェーズ遷移は Python 側 watcher が同タイミングで発火する
                }}
            }}, 1000);
        }}
    }})();
    </script>
    """
