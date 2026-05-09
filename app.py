import streamlit as st

from database import init_db
from logic.measurement import start_measurement, stop_measurement
from ui.styles import (
    cleanup_measure_dom,
    get_common_css,
    play_bgm,
    render_settings_button,
    render_settings_panel,
)
from state import (
    PHASE_CAMERA_CHECK,
    PHASE_DEMO,
    PHASE_FINISHED,
    PHASE_MEASURE,
    PHASE_PRE_MEASURE,
    PHASE_READY,
    PHASE_START_DISPLAY,
    PHASE_TRANSITION,
    begin_measurement_phase,
    complete_measurement_phase,
    get_current_exercise,
    get_duration_for_phase,
    init_session_state,
    render_debug_sidebar,
    should_advance_phase,
    start_training_after_camera_check,
    start_flow,
    transition_to_demo,
    transition_to_pre_measure,
    transition_to_start_display,
)
from ui.camera_check_view import render_camera_check_view
from ui.demo_view import render_demo_view
from ui.finished_view import render_finished_view
from ui.measure_view import render_measure_view
from ui.media_blocks import render_camera_once
from ui.pre_measure_view import render_pre_measure_view
from ui.progress_indicator import render_progress_indicator
from ui.ready_view import render_ready_view
from ui.start_display_view import render_start_display_view
from ui.transition_view import render_transition_view


st.set_page_config(page_title="motion_training_app", layout="wide")


def handle_start() -> None:
    """ready から camera_check に入ります。"""

    start_flow()


def handle_camera_confirm() -> None:
    """画角確認後に最初の demo に入ります。"""

    start_training_after_camera_check()


def route_view() -> None:
    """現在の phase に応じて画面を切り替えます。"""

    phase = st.session_state.phase
    exercise = get_current_exercise()
    phase_started_at = st.session_state.phase_started_at
    phase_duration = get_duration_for_phase(phase=phase, exercise=exercise)

    render_context = {
        "phase": phase,
        "exercise_name": exercise.name if exercise else None,
        "phase_started_at": phase_started_at,
        "phase_duration": round(phase_duration, 2),
    }
    render_debug_sidebar(render_context=render_context)

    if phase == PHASE_READY:
        render_ready_view(on_start=handle_start)
        return

    if phase == PHASE_CAMERA_CHECK:
        render_camera_check_view(on_confirm=handle_camera_confirm)
        return

    if phase == PHASE_FINISHED:
        render_finished_view(
            results=st.session_state.results,
            on_restart=handle_start,
        )
        return

    if exercise is None:
        st.error("現在の動作を取得できませんでした。")
        return

    if phase == PHASE_DEMO:
        render_demo_view(
            exercise=exercise,
            phase_started_at=phase_started_at,
            phase_duration=phase_duration,
        )
    elif phase == PHASE_PRE_MEASURE:
        render_pre_measure_view(
            exercise=exercise,
            phase_started_at=phase_started_at,
            phase_duration=phase_duration,
        )
    elif phase == PHASE_START_DISPLAY:
        render_start_display_view(
            exercise=exercise,
            phase_started_at=phase_started_at,
            phase_duration=phase_duration,
        )
    elif phase == PHASE_MEASURE:
        render_measure_view(
            exercise=exercise,
            phase_started_at=phase_started_at,
            phase_duration=phase_duration,
        )
    elif phase == PHASE_TRANSITION:
        render_transition_view(
            exercise=exercise,
            phase_started_at=phase_started_at,
            phase_duration=phase_duration,
        )
    else:
        st.error(f"未対応の phase です: {phase}")

    # 進行状況インジケーター（DEMO/COUNTDOWN/MEASURE/TRANSITION のみ内部で表示判定）
    render_progress_indicator()


def phase_controller() -> None:
    """フェーズ境界を検出して遷移を実行する（通常関数・fragment なし）。

    各 view の st.rerun() ループの中で毎回呼ばれ、
    遷移が必要なタイミングだけ session_state を更新して st.rerun() する。
    """

    if not should_advance_phase():
        return

    exercise = get_current_exercise()
    phase = st.session_state.phase

    if phase == PHASE_TRANSITION:
        # TRANSITION (6s) 終了で DEMO へ
        transition_to_demo()
        st.rerun()

    elif phase == PHASE_DEMO:
        # DEMO 終了で計測前カウントダウン (PRE_MEASURE) へ
        transition_to_pre_measure()
        st.rerun()

    elif phase == PHASE_PRE_MEASURE and exercise is not None:
        # PRE_MEASURE は JS が「カウントダウン 3s + Start!! 0.8s +
        # 移動 0.7s + 計測 demo_duration」を担当。同じ duration の
        # Python タイマーが切れたら結果を保存して TRANSITION/FINISHED へ。
        complete_measurement_phase(
            exercise=exercise,
            stop_measurement_fn=stop_measurement,
        )
        st.rerun()


def main() -> None:
    init_db()
    init_session_state()
    st.markdown(get_common_css(), unsafe_allow_html=True)
    play_bgm()
    # カメラを一度だけ起動（rerun でも getUserMedia を再実行しない）
    render_camera_once()
    render_settings_button()
    render_settings_panel()
    # PRE_MEASURE 以外のフェーズでは JS タイマーの DOM 残骸をクリーンアップ
    if st.session_state.get("phase") != PHASE_PRE_MEASURE:
        cleanup_measure_dom()
    phase_controller()
    route_view()


if __name__ == "__main__":
    main()
