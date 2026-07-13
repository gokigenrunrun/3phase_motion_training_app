"""計測ロジック。

MediaPipe ランドマーク取得の開始/停止と、
取得データからのスコア計算を担当する。
"""
from typing import Optional

import streamlit as st

from exercises import Exercise


def start_measurement(exercise: Exercise) -> None:
    """計測を開始する。

    webrtc_streamer のプロセッサの start_capture() を呼ぶ。

    Args:
        exercise: これから計測する種目（ログ出力にのみ使用）。
    """
    processor = _get_processor()
    if processor:
        processor.start_capture()
        print(f"[measurement] capture started: {exercise.key}")
    else:
        print("[measurement] WARNING: processor not found, capture not started")


def stop_measurement() -> None:
    """計測を停止し、ランドマーク DataFrame を session_state に退避する。

    プロセッサの stop_capture() → get_dataframe() を行い、
    結果を st.session_state._last_measurement_df に格納する。
    実スコア計算は build_real_result() 側で行う。
    """
    processor = _get_processor()
    if processor:
        processor.stop_capture()
        df = processor.get_dataframe()
        n_frames = df["frame"].nunique() if len(df) > 0 else 0
        print(f"[measurement] capture stopped: {len(df)} rows, {n_frames} frames")
        st.session_state._last_measurement_df = df if len(df) > 0 else None
    else:
        print("[measurement] WARNING: processor not found")
        st.session_state._last_measurement_df = None


def build_real_result(exercise: Exercise) -> dict:
    """計測データから実スコアの結果 dict を生成する。

    finished_view が期待する形式:
    {
        "exercise_key": str,
        "exercise_name": str,
        "overall": "A"/"B"/...,
        "metrics": {"head_movement": 88.5, ...},
    }

    計測データがない場合はフォールバック結果（N/A）を返す。
    """
    from logic.calculate_metrics import calculate_metrics_by_frame
    from logic.scoring import (
        calculate_overall_score,
        get_grade,
        score_from_frame_metrics,
    )

    df = st.session_state.get("_last_measurement_df")

    if df is None or len(df) == 0:
        print("[measurement] no capture data, falling back to N/A")
        return _build_fallback_result(exercise)

    try:
        # 種目から action を決定（classify_action のハードコード窓を回避）
        action = _exercise_to_action(exercise.key)

        # バンザイは脚フェーズ窓に依存しないため override しない。
        # 足あげ種目は全フレームを当該脚フェーズに固定する。
        if exercise.key == "banzai":
            frame_df = calculate_metrics_by_frame(df)
        else:
            frame_df = calculate_metrics_by_frame(df, action_override=action)

        scores = score_from_frame_metrics(frame_df, action=action)
        overall = calculate_overall_score(scores)
        grade = get_grade(overall)

        print(f"[measurement] scores: {scores}")
        print(f"[measurement] overall: {overall}, grade: {grade}")

        return {
            "exercise_key": exercise.key,
            "exercise_name": exercise.name,
            "overall": grade,
            "metrics": scores,
        }

    except Exception as e:  # noqa: BLE001
        print(f"[measurement] scoring error: {e}")
        import traceback
        traceback.print_exc()
        return _build_fallback_result(exercise)


def _exercise_to_action(exercise_key: str) -> str:
    """種目キーから calculate_metrics の action 文字列に変換する。

    Args:
        exercise_key: exercises.Exercise.key（"banzai"/"right_leg_raise"/"left_leg_raise"）。

    Returns:
        "right_leg" または "left_leg"。スコアレンジの選択に使われる。
    """
    mapping = {
        "banzai": "right_leg",  # バンザイはデフォルトのスコアレンジを使用
        "right_leg_raise": "right_leg",
        "left_leg_raise": "left_leg",
    }
    return mapping.get(exercise_key, "right_leg")


def _build_fallback_result(exercise: Exercise) -> dict:
    """計測データがない場合のフォールバック結果。

    Args:
        exercise: 対象の種目。

    Returns:
        dict: build_real_result() と同じ形式で、metrics を全て NaN、
            overall を "N/A" にしたもの。
    """
    return {
        "exercise_key": exercise.key,
        "exercise_name": exercise.name,
        "overall": "N/A",
        "metrics": {
            "head_movement": float("nan"),
            "shoulder_tilt": float("nan"),
            "torso_tilt": float("nan"),
            "leg_lift": float("nan"),
            "foot_sway": float("nan"),
            "arm_sag": float("nan"),
        },
    }


def _get_processor():
    """session_state から webrtc プロセッサを取得する。

    Returns:
        PoseCaptureProcessor | None: WebRTC 接続が確立し映像処理が
            開始されていれば processor インスタンス、未接続なら None。
    """
    ctx = st.session_state.get("_webrtc_ctx")
    if ctx is not None and getattr(ctx, "video_processor", None):
        return ctx.video_processor
    return None
