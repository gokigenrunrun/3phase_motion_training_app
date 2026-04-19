import streamlit as st

from logic.measurement import start_measurement, stop_measurement
from state import (
    PHASE_CAMERA_CHECK,
    PHASE_COUNTDOWN,
    PHASE_DEMO,
    PHASE_FINISHED,
    PHASE_MEASURE,
    PHASE_READY,
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
    transition_to_countdown,
    transition_to_demo,
)
from ui.camera_check_view import render_camera_check_view
from ui.countdown_view import render_countdown_view
from ui.demo_view import render_demo_view
from ui.finished_view import render_finished_view
from ui.measure_view import render_measure_view
from ui.ready_view import render_ready_view
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
    elif phase == PHASE_COUNTDOWN:
        render_countdown_view(
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


@st.fragment(run_every=0.2)
def phase_controller() -> None:
    """フェーズ境界だけを監視します。

    常時の全体 rerun は行わず、遷移が必要な瞬間だけ session_state を更新して
    1回だけ st.rerun() します。
    """

    if not should_advance_phase():
        return

    exercise = get_current_exercise()
    phase = st.session_state.phase

    if phase == PHASE_DEMO:
        transition_to_countdown()
        rerun_app()
        return

    if phase == PHASE_COUNTDOWN and exercise is not None:
        begin_measurement_phase(exercise=exercise, start_measurement_fn=start_measurement)
        rerun_app()
        return

    if phase == PHASE_MEASURE and exercise is not None:
        complete_measurement_phase(
            exercise=exercise,
            stop_measurement_fn=stop_measurement,
        )
        rerun_app()
        return

    if phase == PHASE_TRANSITION:
        transition_to_demo()
        rerun_app()
        return


def rerun_app() -> None:
    """fragment 内からでも画面本体を更新するため app rerun を優先します。"""

    try:
        st.rerun(scope="app")
    except TypeError:
        st.rerun()


def main() -> None:
    init_session_state()
    phase_controller()
    route_view()


if __name__ == "__main__":
    main()
