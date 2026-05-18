import time
from typing import Callable

import streamlit as st

from exercises import EXERCISES, Exercise


PHASE_READY = "ready"
PHASE_CAMERA_CHECK = "camera_check"
PHASE_DEMO = "demo"
PHASE_PRE_MEASURE = "pre_measure"
PHASE_START_DISPLAY = "start_display"
PHASE_MEASURE = "measure"
PHASE_TRANSITION = "transition"
PHASE_FINISHED = "finished"

# 廃止された定数（旧コード互換のため残置・流れには登場しない）
PHASE_PRE_DEMO = "pre_demo"
PHASE_COUNTDOWN = "countdown"

PRE_MEASURE_SECONDS = 3
START_DISPLAY_SECONDS = 2
TRANSITION_SECONDS = 6.0

PHASE_DURATIONS = {
    PHASE_PRE_MEASURE: PRE_MEASURE_SECONDS,
    PHASE_START_DISPLAY: START_DISPLAY_SECONDS,
    PHASE_TRANSITION: TRANSITION_SECONDS,
}


def init_session_state() -> None:
    """必要な状態を初期化します。"""

    defaults = {
        "phase": PHASE_READY,
        "exercise_index": 0,
        "phase_started_at": None,
        "measurement_running": False,
        "measurement_token": 0,
        "last_started_token": None,
        "last_completed_exercise": None,
        "last_index_transition": None,
        "transition_message": None,
        "results": [],
        "debug_mode": True,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_flow() -> None:
    """最初の画面からやり直せるようにします。"""

    st.session_state.phase = PHASE_READY
    st.session_state.exercise_index = 0
    st.session_state.phase_started_at = None
    st.session_state.measurement_running = False
    st.session_state.measurement_token = 0
    st.session_state.last_started_token = None
    st.session_state.last_completed_exercise = None
    st.session_state.last_index_transition = None
    st.session_state.transition_message = None
    st.session_state.results = []


def start_flow() -> None:
    """計測開始ボタンから呼ばれる開始処理です。"""

    reset_flow()
    set_phase(PHASE_CAMERA_CHECK)


def start_training_after_camera_check() -> None:
    """画角確認後、最初の動作を知らせる transition に入ります。"""

    st.session_state.exercise_index = 0
    first_exercise = get_current_exercise()
    st.session_state.transition_message = (
        f"まずは{first_exercise.name}から" if first_exercise else "まずは最初の動作から"
    )
    set_phase(PHASE_TRANSITION)


def set_phase(phase: str) -> None:
    """フェーズを更新し、その開始時刻を記録します。

    フェーズ遷移時に音声読み上げの重複防止キャッシュをクリアして、
    次フェーズで同じテキストでも改めて読み上げられるようにする。
    """

    st.session_state.phase = phase
    st.session_state.phase_started_at = time.time()

    # speak() の重複防止キャッシュ（spoken_<hash> キー）をクリア
    spoken_keys = [k for k in st.session_state.keys() if str(k).startswith("spoken_")]
    for k in spoken_keys:
        del st.session_state[k]


def get_current_exercise() -> Exercise | None:
    """現在対象の動作を返します。"""

    index = st.session_state.exercise_index
    if 0 <= index < len(EXERCISES):
        return EXERCISES[index]
    return None


def get_phase_elapsed() -> float:
    """現在フェーズの経過秒数です。"""

    started_at = st.session_state.phase_started_at
    if started_at is None:
        return 0.0
    return max(0.0, time.time() - started_at)


def get_phase_duration() -> float:
    """現在フェーズの長さを返します。"""

    return get_duration_for_phase(
        phase=st.session_state.phase,
        exercise=get_current_exercise(),
    )


def _measure_seconds_for_js(exercise: Exercise | None) -> int:
    """JS タイマーに渡す計測秒数（demo_duration × measure_loop_count を四捨五入）。"""
    if exercise is None:
        return 10
    return max(1, int(round(exercise.demo_duration * exercise.measure_loop_count)))


def get_duration_for_phase(phase: str, exercise: Exercise | None) -> float:
    """指定された phase と exercise に対応する長さを返します。

    DEMO         : demo_duration × loop_count
    MEASURE      : demo_duration × measure_loop_count
    PRE_MEASURE  : JS アニメ(4.5s) + JS タイマー秒 + バッファ(1.0s)
                   バッファは JS が確実に 0 に到達してクリーンアップを
                   完了する時間を確保するため。
    """

    if phase == PHASE_DEMO:
        return (exercise.demo_duration * exercise.loop_count) if exercise else 0.0
    if phase == PHASE_MEASURE:
        return (exercise.demo_duration * exercise.measure_loop_count) if exercise else 0.0
    if phase == PHASE_PRE_MEASURE:
        # JS アニメーション(4.5s) + JS タイマー int 秒 + バッファ(1.0s)
        return _measure_seconds_for_js(exercise) + 4.5 + 1.0
    return PHASE_DURATIONS.get(phase, 0.0)


def get_phase_remaining() -> float:
    """現在フェーズの残り時間です。"""

    duration = get_phase_duration()
    remaining = duration - get_phase_elapsed()
    return max(0.0, remaining)


def get_remaining_from_snapshot(*, started_at: float | None, duration: float) -> float:
    """描画時点で固定した started_at と duration から残り時間を計算します。"""

    if started_at is None:
        return max(0.0, duration)
    remaining = duration - max(0.0, time.time() - started_at)
    return max(0.0, remaining)


def should_advance_phase() -> bool:
    """フェーズ終了条件を満たしたかを判定します。"""

    phase = st.session_state.phase
    if phase in {PHASE_READY, PHASE_CAMERA_CHECK, PHASE_FINISHED}:
        return False
    return get_phase_elapsed() >= get_phase_duration()


def transition_to_demo() -> None:
    """TRANSITION 終了後、現在の exercise_index の demo に入ります。"""

    st.session_state.measurement_running = False
    st.session_state.transition_message = None
    set_phase(PHASE_DEMO)


def transition_to_pre_measure() -> None:
    """DEMO 終了後、計測前の 3 秒カウントダウン (PRE_MEASURE) に入ります。"""

    st.session_state.measurement_running = False
    set_phase(PHASE_PRE_MEASURE)


def transition_to_start_display() -> None:
    """PRE_MEASURE 終了後、Start!! 表示の 2 秒間 (START_DISPLAY) に入ります。"""

    st.session_state.measurement_running = False
    set_phase(PHASE_START_DISPLAY)


def transition_to_countdown() -> None:
    """demo または次の計測前から countdown に入ります。"""

    st.session_state.measurement_running = False
    set_phase(PHASE_COUNTDOWN)


def begin_measurement_phase(
    exercise: Exercise,
    start_measurement_fn: Callable[[Exercise], None],
) -> None:
    """countdown 終了後に measure を開始します。"""

    st.session_state.measurement_token += 1
    current_token = st.session_state.measurement_token
    st.session_state.last_started_token = current_token
    st.session_state.measurement_running = True
    start_measurement_fn(exercise)
    set_phase(PHASE_MEASURE)


def complete_measurement_phase(
    exercise: Exercise,
    stop_measurement_fn: Callable[[], None],
) -> None:
    """measure 終了後は次の動作の demo、または finished に進みます。"""

    previous_index = st.session_state.exercise_index

    if st.session_state.measurement_running:
        stop_measurement_fn()

    st.session_state.measurement_running = False
    st.session_state.results.append(build_dummy_result(exercise=exercise))
    st.session_state.last_completed_exercise = exercise.name

    if st.session_state.exercise_index < len(EXERCISES) - 1:
        st.session_state.exercise_index += 1
        next_exercise = get_current_exercise()
        st.session_state.transition_message = (
            f"次は{next_exercise.name}" if next_exercise else "次の動作を確認しましょう"
        )
        st.session_state.last_index_transition = {
            "completed": exercise.name,
            "from": previous_index,
            "to": st.session_state.exercise_index,
            "next_phase": PHASE_TRANSITION,
        }
        set_phase(PHASE_TRANSITION)
        return

    st.session_state.last_index_transition = {
        "completed": exercise.name,
        "from": previous_index,
        "to": previous_index,
        "next_phase": PHASE_FINISHED,
    }
    st.session_state.transition_message = None
    set_phase(PHASE_FINISHED)


def build_dummy_result(exercise: Exercise) -> dict:
    """本計測ロジックが入るまでの結果表示用ダミーデータです。"""

    base_scores = {
        "banzai": {
            "overall": "A",
            "metrics": {
                "リズム": 88,
                "大きさ": 91,
                "安定性": 84,
                "左右バランス": 86,
            },
            "feedback": {
                "リズム": "2回のバンザイを一定のテンポで行えています。",
                "大きさ": "手足を大きく伸ばせています。",
                "安定性": "着地姿勢が安定しています。",
                "左右バランス": "左右差は小さめです。",
            },
            "left_right": {
                "left": [76, 80, 83, 86, 88, 90, 92],
                "right": [74, 79, 82, 85, 87, 89, 91],
            },
        },
        "right_leg_raise": {
            "overall": "B",
            "metrics": {
                "リズム": 82,
                "大きさ": 79,
                "安定性": 76,
                "左右バランス": 73,
            },
            "feedback": {
                "リズム": "動き出しはよいですが、最後に少し速くなっています。",
                "大きさ": "右足をもう少し高く上げられるとよいです。",
                "安定性": "軸足が少し揺れています。",
                "左右バランス": "右側の動きがやや小さめです。",
            },
            "left_right": {
                "left": [78, 80, 82, 84, 85, 87, 89],
                "right": [68, 71, 73, 75, 77, 79, 82],
            },
        },
        "left_leg_raise": {
            "overall": "B",
            "metrics": {
                "リズム": 80,
                "大きさ": 77,
                "安定性": 78,
                "左右バランス": 75,
            },
            "feedback": {
                "リズム": "全体のテンポは保てています。",
                "大きさ": "左足を上げる高さを少し増やせそうです。",
                "安定性": "上半身の傾きを抑えるとさらに安定します。",
                "左右バランス": "左側の可動域を少し広げるとよいです。",
            },
            "left_right": {
                "left": [69, 72, 74, 76, 78, 80, 83],
                "right": [77, 79, 81, 83, 85, 86, 88],
            },
        },
    }
    result = base_scores.get(exercise.key, base_scores["banzai"])
    return {
        "exercise_key": exercise.key,
        "exercise_name": exercise.name,
        **result,
    }


def render_debug_sidebar(render_context: dict | None = None) -> None:
    """開発中に状態を確認しやすいように sidebar に表示します。"""

    with st.sidebar:
        st.subheader("Debug")
        st.checkbox("デバッグ表示", key="debug_mode")

        if not st.session_state.debug_mode:
            return

        exercise = get_current_exercise()
        debug_payload = {
            "phase": st.session_state.phase,
            "exercise_index": st.session_state.exercise_index,
            "state_exercise_name": exercise.name if exercise else None,
            "measurement_running": st.session_state.measurement_running,
            "phase_started_at": st.session_state.phase_started_at,
            "phase_elapsed": round(get_phase_elapsed(), 2),
            "phase_remaining": round(get_phase_remaining(), 2),
            "phase_duration": round(get_phase_duration(), 2),
            "measurement_token": st.session_state.measurement_token,
            "last_started_token": st.session_state.last_started_token,
            "last_completed_exercise": st.session_state.last_completed_exercise,
            "last_index_transition": st.session_state.last_index_transition,
            "transition_message": st.session_state.transition_message,
            "results_count": len(st.session_state.results),
        }
        if render_context is not None:
            debug_payload["render_phase"] = render_context.get("phase")
            debug_payload["render_exercise_name"] = render_context.get("exercise_name")
            debug_payload["render_phase_started_at"] = render_context.get("phase_started_at")
            debug_payload["render_phase_duration"] = render_context.get("phase_duration")
        st.json(debug_payload)
