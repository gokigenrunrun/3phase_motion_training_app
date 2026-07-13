"""計測する3種目（バンザイ・右足あげ・左足あげ）の定義モジュール。

Exercise データクラスで各種目の動画パス・再生時間・計測時間を管理し、
モジュール読み込み時に EXERCISES リストとしてインスタンス化する。
state.py はこのリストの順番どおりに種目を進行させる。
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path


ASSETS_DIR = Path(__file__).resolve().parent / "assets"
DEFAULT_DEMO_SECONDS = 5.0


@dataclass(frozen=True)
class Exercise:
    """各動作の定義です。

    evaluator_key は将来 MediaPipe の評価関数をつなぐために残しています。
    loop_count: DEMO フェーズで何回ループ再生するか。
    measure_loop_count: 計測（MEASURE/PRE_MEASURE）で動画を何回ループ再生するか。
    """

    key: str
    name: str
    description: str
    video_path: Path
    demo_duration: float        # DEMO フェーズの再生時間（秒）
    evaluator_key: str
    loop_count: int = 1
    measure_loop_count: int = 1
    measure_duration: float | None = None   # 計測時間（秒）。None なら demo_duration を流用
    measure_video_end: float | None = None   # 計測フェーズでの動画終了位置（秒）

    def get_measure_duration(self) -> float:
        """計測時間を返す。未設定の場合は demo_duration × measure_loop_count を使用。"""
        if self.measure_duration is not None:
            return self.measure_duration
        return self.demo_duration * self.measure_loop_count

    def get_measure_video_end(self) -> float:
        """計測フェーズの動画終了位置を返す。未設定なら計測時間を使用。"""
        if self.measure_video_end is not None:
            return self.measure_video_end
        return self.get_measure_duration()

    @property
    def uses_segmented_video(self) -> bool:
        """単一動画を区間（DEMO 部分／計測部分）に分けて再生する種目か。

        measure_video_end が明示されている種目（バンザイ）だけ True。
        旧来のループ再生（右足あげ・左足あげ）は False のまま据え置く。
        """
        return self.measure_video_end is not None


def _probe_video_duration(video_path: Path) -> float:
    """ffprobe で動画秒数を取得します。

    ffprobe が使えない環境では既定値にフォールバックします。
    """

    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
        )
        duration = float(result.stdout.strip())
        return max(duration, 1.0)
    except (FileNotFoundError, subprocess.CalledProcessError, ValueError):
        return DEFAULT_DEMO_SECONDS


def _build_exercise(
    key: str,
    name: str,
    description: str,
    filename: str,
    evaluator_key: str,
    loop_count: int = 1,
    measure_loop_count: int = 1,
    demo_duration: float | None = None,
    measure_duration: float | None = None,
    measure_video_end: float | None = None,
) -> Exercise:
    """Exercise を組み立てるヘルパー。demo_duration 未指定時は動画ファイルの
    実尺を ffprobe で自動取得する。"""
    video_path = ASSETS_DIR / filename
    # demo_duration を明示した種目（バンザイ）は ffprobe を使わず指定値を採用。
    # 未指定の種目は従来どおり動画全体の秒数を自動取得する。
    resolved_demo = (
        demo_duration if demo_duration is not None
        else _probe_video_duration(video_path)
    )
    return Exercise(
        key=key,
        name=name,
        description=description,
        video_path=video_path,
        demo_duration=resolved_demo,
        evaluator_key=evaluator_key,
        loop_count=loop_count,
        measure_loop_count=measure_loop_count,
        measure_duration=measure_duration,
        measure_video_end=measure_video_end,
    )


EXERCISES = [
    _build_exercise(
        key="banzai",
        name="バンザイ",
        description="まずはこの動きをやってみよう！\n膝を曲げて小さくなって、両手両足を伸ばしてバンザイを2回します。",
        filename="otehon_banzai02.mp4",
        evaluator_key="evaluate_banzai",
        loop_count=1,
        measure_loop_count=1,
        demo_duration=16.0,        # DEMO は 0〜16 秒を再生
        measure_duration=32.0,     # 計測は 32 秒
        measure_video_end=34.0,    # 動画は 34 秒で終了
    ),
    _build_exercise(
        key="right_leg_raise",
        name="みぎあし　あげ",
        description="次はこの動きをやってみよう！\n両手を横に広げ、右足を上げます。",
        filename="otehon_migi02.mp4",
        evaluator_key="evaluate_right_leg_raise",
        loop_count=1,
        measure_loop_count=1,
        demo_duration=16.0,        # DEMO は 0〜16 秒を再生
        measure_duration=32.0,     # 計測は 32 秒
        measure_video_end=34.0,    # 動画は 34 秒で終了
    ),
    _build_exercise(
        key="left_leg_raise",
        name="ひだりあし　あげ",
        description="次はこの動きをやってみよう！\n両手を横に広げ、左足を上げます。",
        filename="otehon_hidari02.mp4",
        evaluator_key="evaluate_left_leg_raise",
        loop_count=1,
        measure_loop_count=1,
        demo_duration=16.0,        # DEMO は 0〜16 秒を再生
        measure_duration=32.0,     # 計測は 32 秒
        measure_video_end=34.0,    # 動画は 34 秒で終了
    ),
]
