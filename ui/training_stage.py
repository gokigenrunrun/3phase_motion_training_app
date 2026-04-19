import math
import time

import streamlit as st

from exercises import Exercise
from ui.media_blocks import PANEL_MAX_WIDTH_PX, render_video_panel, render_webcam_panel


APP_TITLE = "Motion Training"


def render_compact_page_styles() -> None:
    """全フェーズを1画面に収めるための共通余白調整です。"""

    st.markdown(
        """
        <style>
        .block-container {
            padding-top: clamp(1.8rem, 3vh, 2.4rem);
            padding-bottom: 0.75rem;
            max-width: 1080px;
        }
        h1 {
            margin: 0;
        }
        h2, h3, p {
            margin-top: 0;
        }
        div[data-testid="stVerticalBlock"] {
            gap: 0.5rem;
        }
        div[data-testid="stHorizontalBlock"] {
            gap: 1rem;
        }
        iframe {
            display: block;
        }
        .stage-header {
            display: grid;
            grid-template-columns: 10rem 1fr 8rem;
            align-items: center;
            gap: 1rem;
            min-height: 5.8rem;
        }
        .app-mark {
            color: #222;
            font-size: 0.95rem;
            font-weight: 800;
            letter-spacing: 0;
        }
        .stage-title-block {
            text-align: center;
        }
        .exercise-title {
            color: #111;
            font-size: 2rem;
            font-weight: 800;
            line-height: 1.15;
            margin: 0;
        }
        .phase-pill {
            display: inline-block;
            margin-top: 0.35rem;
            border: 1px solid #cfcfcf;
            border-radius: 999px;
            padding: 0.18rem 0.8rem;
            color: #333;
            background: #fff;
            font-size: 0.9rem;
            font-weight: 700;
        }
        .timer-wrap {
            display: flex;
            justify-content: flex-end;
        }
        .timer-ring {
            --progress: 0%;
            --elapsed: 100%;
            width: 5.35rem;
            height: 5.35rem;
            border-radius: 50%;
            background:
                conic-gradient(from 0deg, #e4e4e4 0 var(--elapsed), #2b7a78 var(--elapsed) 100%);
            display: grid;
            place-items: center;
        }
        .timer-inner {
            width: 4.15rem;
            height: 4.15rem;
            border-radius: 50%;
            background: #fff;
            display: grid;
            place-items: center;
            color: #111;
            font-size: 1.55rem;
            font-weight: 800;
        }
        .stage-copy {
            min-height: 3.9rem;
            text-align: center;
            max-width: 760px;
            margin: 0 auto 0.35rem;
        }
        .stage-kicker {
            color: #555;
            font-size: 0.95rem;
            font-weight: 700;
            margin-bottom: 0.15rem;
        }
        .stage-description {
            color: #222;
            font-size: 1rem;
            line-height: 1.45;
            margin: 0;
            white-space: pre-line;
        }
        .camera-guide {
            min-height: 364px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            gap: 0.75rem;
            padding: 0.4rem 0.7rem;
        }
        .camera-guide-title {
            font-size: 1.1rem;
            font-weight: 800;
            text-align: center;
        }
        .camera-guide ul {
            margin: 0;
            padding-left: 1.2rem;
            line-height: 1.7;
        }
        .media-title {
            font-size: 0.92rem;
            font-weight: 700;
            margin: 0 0 0.25rem;
            text-align: center;
            background: transparent;
        }
        .countdown-overlay {
            position: fixed;
            inset: 0;
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.72);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 5;
            pointer-events: none;
        }
        .countdown-number {
            color: #111;
            font-size: 7.5rem;
            font-weight: 800;
            line-height: 1;
        }
        .ready-wrap {
            max-width: 760px;
            margin: 1.2rem auto 0;
            text-align: center;
        }
        .ready-lead {
            font-size: 1.05rem;
            line-height: 1.65;
            margin: 0.5rem 0 0.9rem;
        }
        .result-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.75rem;
            align-items: start;
        }
        .result-panel {
            border: 1px solid #d7d7d7;
            border-radius: 8px;
            padding: 0.65rem;
            background: #fff;
        }
        .result-panel h3 {
            font-size: 1rem;
            margin-bottom: 0.35rem;
        }
        .metric-row {
            display: grid;
            grid-template-columns: 5.5rem 3rem 1fr;
            gap: 0.45rem;
            align-items: center;
            font-size: 0.9rem;
            margin-bottom: 0.3rem;
        }
        .metric-bar {
            height: 0.5rem;
            background: #e7e7e7;
            border-radius: 8px;
            overflow: hidden;
        }
        .metric-fill {
            height: 100%;
            background: #2b7a78;
        }
        .feedback-item {
            font-size: 0.86rem;
            line-height: 1.35;
            margin-bottom: 0.28rem;
        }
        .transition-screen {
            min-height: calc(100vh - 6rem);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            gap: 0.75rem;
        }
        .transition-kicker {
            color: #555;
            font-size: 1rem;
            font-weight: 700;
        }
        .transition-title {
            color: #111;
            font-size: 3rem;
            font-weight: 900;
            line-height: 1.1;
        }
        .transition-copy {
            color: #444;
            font-size: 1.05rem;
        }
        .transition-timer {
            --progress: 0%;
            --elapsed: 100%;
            width: 4.5rem;
            height: 4.5rem;
            border-radius: 50%;
            background:
                conic-gradient(from 0deg, #e4e4e4 0 var(--elapsed), #2b7a78 var(--elapsed) 100%);
            display: grid;
            place-items: center;
            margin-top: 0.4rem;
        }
        .transition-timer-inner {
            width: 3.45rem;
            height: 3.45rem;
            border-radius: 50%;
            background: #fff;
            display: grid;
            place-items: center;
            color: #111;
            font-size: 1.35rem;
            font-weight: 800;
        }
        @media (max-height: 720px) {
            .block-container {
                padding-top: 1.45rem;
            }
            .stage-header {
                min-height: 5rem;
            }
            .exercise-title {
                font-size: 1.75rem;
            }
            .timer-ring {
                width: 4.75rem;
                height: 4.75rem;
            }
            .timer-inner {
                width: 3.7rem;
                height: 3.7rem;
                font-size: 1.35rem;
            }
            .stage-copy {
                min-height: 3.4rem;
            }
            .transition-screen {
                min-height: calc(100vh - 5rem);
            }
            .transition-title {
                font-size: 2.4rem;
            }
            .transition-timer {
                width: 4rem;
                height: 4rem;
            }
            .transition-timer-inner {
                width: 3.1rem;
                height: 3.1rem;
                font-size: 1.2rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_training_stage(
    *,
    exercise: Exercise,
    phase_label: str,
    description: str,
    phase_started_at: float | None,
    phase_duration: float,
    video_loop: bool,
    overlay_number: int | None = None,
) -> None:
    """お手本・カウントダウン・計測で共通利用する左右2カラム画面です。"""

    render_compact_page_styles()
    _render_training_header_fragment(
        exercise=exercise,
        phase_label=phase_label,
        description=description,
        phase_started_at=phase_started_at,
        phase_duration=phase_duration,
        overlay_number=overlay_number,
    )

    left, right = st.columns(2, gap="large")
    with left:
        st.markdown('<div class="media-title">お手本動画</div>', unsafe_allow_html=True)
        render_video_panel(
            video_path=str(exercise.video_path),
            autoplay=True,
            loop=video_loop,
            max_width_px=PANEL_MAX_WIDTH_PX,
        )
    with right:
        st.markdown('<div class="media-title">あなたの動き</div>', unsafe_allow_html=True)
        render_webcam_panel(max_width_px=PANEL_MAX_WIDTH_PX)


@st.fragment(run_every=1)
def _render_training_header_fragment(
    *,
    exercise: Exercise,
    phase_label: str,
    description: str,
    phase_started_at: float | None,
    phase_duration: float,
    overlay_number: int | None,
) -> None:
    """タイマーを含むヘッダーだけを1秒ごとに再描画します。"""

    remaining_seconds = _get_remaining_seconds(
        phase_started_at=phase_started_at,
        phase_duration=phase_duration,
    )
    progress_percent = _get_remaining_progress(
        remaining_seconds=remaining_seconds,
        phase_duration=phase_duration,
    )
    elapsed_percent = 100 - progress_percent
    current_overlay_number = max(1, remaining_seconds) if overlay_number is not None else None

    st.markdown(
        f"""
        <header class="stage-header">
            <div class="app-mark">{APP_TITLE}</div>
            <div class="stage-title-block">
                <h1 class="exercise-title">{exercise.name}</h1>
                <div class="phase-pill">{phase_label}</div>
            </div>
            <div class="timer-wrap">
                <div class="timer-ring" style="--progress:{progress_percent}%; --elapsed:{elapsed_percent}%;">
                    <div class="timer-inner">{remaining_seconds}</div>
                </div>
            </div>
        </header>
        <div class="stage-copy">
            <p class="stage-description">{description}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if current_overlay_number is not None:
        st.markdown(
            f"""
            <div class="countdown-overlay">
                <div class="countdown-number">{current_overlay_number}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_camera_check_layout(*, on_confirm) -> None:
    """計測前にカメラ画角を確認する画面です。"""

    render_compact_page_styles()
    st.markdown(
        f"""
        <header class="stage-header">
            <div class="app-mark">{APP_TITLE}</div>
            <div class="stage-title-block">
                <h1 class="exercise-title">カメラチェック</h1>
                <div class="phase-pill">撮影範囲を確認しましょう</div>
            </div>
            <div></div>
        </header>
        <div class="stage-copy">
            <p class="stage-description">
                体が画面の中に収まる位置に立ってください。
                手や足を広げても見切れないことを確認してください。
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns(2, gap="large")
    with left:
        st.markdown('<div class="media-title">チェックポイント</div>', unsafe_allow_html=True)
        st.markdown(
            """
            <div class="camera-guide">
                <div class="camera-guide-title">準備ができたら始めます</div>
                <ul>
                    <li>頭から足先まで入る位置に立つ</li>
                    <li>両手を広げても見切れない</li>
                    <li>足を上げても画面内に収まる</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        st.markdown('<div class="media-title">あなたの映像</div>', unsafe_allow_html=True)
        render_webcam_panel(max_width_px=PANEL_MAX_WIDTH_PX)

    st.button("この位置で始める", type="primary", use_container_width=True, on_click=on_confirm)


def _get_remaining_seconds(*, phase_started_at: float | None, phase_duration: float) -> int:
    if phase_started_at is None:
        return max(0, math.ceil(phase_duration))
    elapsed = max(0.0, time.time() - phase_started_at)
    return max(0, math.ceil(phase_duration - elapsed))


def _get_remaining_progress(*, remaining_seconds: int, phase_duration: float) -> int:
    if phase_duration <= 0:
        return 0
    return max(0, min(100, round((remaining_seconds / phase_duration) * 100)))
