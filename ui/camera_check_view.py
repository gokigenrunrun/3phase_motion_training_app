from typing import Callable

from ui.training_stage import render_camera_check_layout


def render_camera_check_view(on_confirm: Callable[[], None]) -> None:
    """計測前にカメラの画角を確認します。"""

    render_camera_check_layout(on_confirm=on_confirm)
