"""スコアリングモジュール。

旧アプリ（Physical-assessment-web）の calculate_metrics をそのまま流用し、
フレームごとの指標を 0〜100 のスコアに変換するラッパーを提供する。
"""
from typing import Dict

import numpy as np
import pandas as pd

from logic.calculate_metrics import (
    SCORE_COLUMNS,
    get_score_range,
)


def scale_score(value: float, min_val: float, max_val: float) -> float:
    """値を 0〜100 のスコアに変換する。

    値が小さいほど高スコアになる。min_val 以下は 100、max_val 以上は 0、
    その間は線形補間。
    """
    if value is None:
        return float("nan")
    if pd.isna(value) or np.isnan(value):
        return float("nan")
    if value <= min_val:
        return 100.0
    if value >= max_val:
        return 0.0
    return (1.0 - (value - min_val) / (max_val - min_val)) * 100.0


def score_from_frame_metrics(
    frame_df: pd.DataFrame,
    action: str = "right_leg",
) -> Dict[str, float]:
    """フレームごとの指標 DataFrame から各指標の平均スコアを計算して返す。

    Args:
        frame_df: calculate_metrics_by_frame() の出力 DataFrame
        action:   "right_leg" or "left_leg"（スコアレンジの選択に使用）
    """
    scores: Dict[str, float] = {}
    for col in SCORE_COLUMNS:
        if col == "banzai_score":
            # banzai_score は evaluate_banzai_pose_auto() 由来の別スケールの値のため、
            # 他の6指標と同じ scale_score() では変換せず採点対象から除外する。
            continue
        if col not in frame_df.columns:
            scores[col] = float("nan")
            continue
        mean_val = frame_df[col].mean(skipna=True)
        try:
            min_val, max_val = get_score_range(col, action)
            scores[col] = scale_score(mean_val, min_val, max_val)
        except KeyError:
            scores[col] = float("nan")
    return scores


def calculate_overall_score(scores: Dict[str, float]) -> float:
    """6 指標の平均を総合スコアとして返す。NaN は除外。"""
    values = [
        v for v in scores.values()
        if v is not None and not np.isnan(v)
    ]
    if not values:
        return float("nan")
    return float(np.mean(values))


def get_grade(score: float) -> str:
    """スコアから A/B/C/D のグレードを返す。

    A: 85以上、B: 70〜84、C: 55〜69、D: 54以下
    """
    if score is None or np.isnan(score):
        return "N/A"
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    return "D"
