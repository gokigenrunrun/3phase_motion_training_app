"""logic/calculate_metrics.py の前処理（preprocess_landmarks）の回帰テスト。

以前は、あるランドマークがクリップ全体で低visibility（＝座標がNaN化）だと、
interpolate() はランドマーク単位でグループ化されていたのに、直後の
ffill().bfill() がグループ化されておらず、MultiIndex 上で隣に積まれた
別ランドマークの値で埋まってしまうバグがあった。

これにより「カメラに映っていない部位」が「別部位の値をコピーした
一定値」に化け、arm_sag/leg_lift/foot_sway 等が誤って「完璧に安定
(≈100点)」と判定されてしまっていた。
"""

import numpy as np
import pandas as pd

from logic.calculate_metrics import calculate_metrics_by_frame, preprocess_landmarks
from logic.scoring import score_from_frame_metrics

# 6指標の計算に使う最小限のランドマーク（鼻・肩・肘・手首・腰・足首）
LANDMARKS_USED = {
    0: (0.50, 0.05),    # nose
    11: (0.40, 0.20), 12: (0.60, 0.20),   # shoulders
    13: (0.36, 0.38), 14: (0.64, 0.38),   # elbows
    15: (0.34, 0.52), 16: (0.66, 0.52),   # wrists
    23: (0.42, 0.55), 24: (0.58, 0.55),   # hips
    27: (0.40, 0.92), 28: (0.60, 0.92),   # ankles
}


def _build_df(
    n_frames: int,
    low_vis_landmarks: set[int],
    jitter_std: float = 0.0015,
    seed: int = 0,
) -> pd.DataFrame:
    """一部ランドマークをクリップ全体で低visibility（欠損）にした長形式DataFrameを作る。"""
    rng = np.random.default_rng(seed)
    rows = []
    for frame in range(n_frames):
        for idx, (x, y) in LANDMARKS_USED.items():
            jx = rng.normal(0, jitter_std)
            jy = rng.normal(0, jitter_std)
            vis = 0.1 if idx in low_vis_landmarks else 0.95
            rows.append(
                {
                    "frame": frame,
                    "landmark_index": idx,
                    "x": x + jx,
                    "y": y + jy,
                    "z": 0.0,
                    "visibility": vis,
                }
            )
    return pd.DataFrame(rows)


def test_preprocess_landmarks_keeps_fully_missing_landmark_as_nan():
    """クリップ全体で低visibilityなランドマークは、前処理後もNaNのまま残ること
    （隣接ランドマークの値がコピーされてこないこと）。"""
    df = _build_df(n_frames=30, low_vis_landmarks={13, 14})  # 肘を常時低visibilityに
    processed = preprocess_landmarks(df)

    elbow_rows = processed[processed["landmark_index"].isin([13, 14])]
    assert elbow_rows["x"].isna().all()
    assert elbow_rows["y"].isna().all()

    # 比較対象：正常なランドマーク（肩）は値を持ち続けていること
    shoulder_rows = processed[processed["landmark_index"].isin([11, 12])]
    assert shoulder_rows["y"].notna().all()


def test_preprocess_landmarks_missing_landmark_value_is_not_copied_from_neighbor():
    """欠損ランドマークの値が、MultiIndexで隣接する別ランドマークの値と
    偶然一致してしまう（＝コピーされている）ことがないこと。"""
    df = _build_df(n_frames=30, low_vis_landmarks={13})
    processed = preprocess_landmarks(df)

    elbow_y = processed.loc[processed["landmark_index"] == 13, "y"]
    shoulder_y = processed.loc[processed["landmark_index"] == 12, "y"]

    assert elbow_y.isna().all()
    # 修正前バグでは elbow_y が shoulder_y の最終フレーム値でベタ埋めされていた
    assert not np.isclose(elbow_y.fillna(-999).to_numpy(), shoulder_y.iloc[-1]).any()


def test_arm_sag_is_nan_not_perfect_when_elbow_fully_missing():
    """肘が常時検出できない場合、arm_sagはNaNのまま除外され、
    誤って「完璧に安定(100点)」と判定されないこと。"""
    df = _build_df(n_frames=60, low_vis_landmarks={13, 14})
    frame_df = calculate_metrics_by_frame(df, action_override="right_leg")

    assert frame_df["arm_sag"].isna().all()

    scores = score_from_frame_metrics(frame_df, action="right_leg")
    assert np.isnan(scores["arm_sag"])


def test_leg_lift_and_foot_sway_are_nan_not_perfect_when_ankle_fully_missing():
    """足首が常時検出できない場合、leg_lift/foot_swayがNaNのまま除外され、
    誤って高得点にならないこと。"""
    df = _build_df(n_frames=60, low_vis_landmarks={27, 28})
    frame_df = calculate_metrics_by_frame(df, action_override="right_leg")

    assert frame_df["leg_lift"].isna().all()
    assert frame_df["foot_sway"].isna().all()

    scores = score_from_frame_metrics(frame_df, action="right_leg")
    assert np.isnan(scores["leg_lift"])
    assert np.isnan(scores["foot_sway"])


def test_visible_landmarks_are_unaffected_by_missing_neighbor():
    """一部ランドマークが欠損していても、他の正常なランドマークの指標計算は
    通常どおり行われること（過剰に厳しくなっていないこと）。"""
    df = _build_df(n_frames=60, low_vis_landmarks={13, 14})
    frame_df = calculate_metrics_by_frame(df, action_override="right_leg")

    # 肘(13,14)に依存しない指標は、通常どおり有限値で計算される
    assert frame_df["head_movement"].notna().all()
    assert frame_df["shoulder_tilt"].notna().all()
    assert frame_df["torso_tilt"].notna().all()
    assert frame_df["leg_lift"].notna().all()
    assert frame_df["foot_sway"].notna().all()
