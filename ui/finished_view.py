from typing import Callable

from ui.legacy_result_view import render_legacy_result_view


def render_finished_view(*, results: list[dict], on_restart: Callable[[], None]) -> None:
    """旧アプリの結果発表画面を finished phase で表示します。"""

    render_legacy_result_view(results=results, on_restart=on_restart)
