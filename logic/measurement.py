from exercises import Exercise


def start_measurement(exercise: Exercise) -> None:
    """将来 MediaPipe の開始処理を入れる場所です。"""

    print(f"[measurement] start: {exercise.key}")


def stop_measurement() -> None:
    """将来 MediaPipe の停止処理を入れる場所です。"""

    print("[measurement] stop")
