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
    demo_duration: float
    evaluator_key: str
    loop_count: int = 1
    measure_loop_count: int = 1


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
) -> Exercise:
    video_path = ASSETS_DIR / filename
    return Exercise(
        key=key,
        name=name,
        description=description,
        video_path=video_path,
        demo_duration=_probe_video_duration(video_path),
        evaluator_key=evaluator_key,
        loop_count=loop_count,
        measure_loop_count=measure_loop_count,
    )


EXERCISES = [
    _build_exercise(
        key="banzai",
        name="バンザイ",
        description="まずはこの動きをやってみよう！\n膝を曲げて小さくなって、両手両足を伸ばしてバンザイを2回します。",
        filename="otehon_banzai.mp4",
        evaluator_key="evaluate_banzai",
        loop_count=1,
        measure_loop_count=2,
    ),
    _build_exercise(
        key="right_leg_raise",
        name="右足あげ",
        description="次はこの動きをやってみよう！\n両手を横に広げ、右足を上げます。",
        filename="otehon_migi.mp4",
        evaluator_key="evaluate_right_leg_raise",
        loop_count=2,
        measure_loop_count=4,
    ),
    _build_exercise(
        key="left_leg_raise",
        name="左足あげ",
        description="次はこの動きをやってみよう！\n両手を横に広げ、左足を上げます。",
        filename="otehon_hidari.mp4",
        evaluator_key="evaluate_left_leg_raise",
        loop_count=2,
        measure_loop_count=4,
    ),
]
