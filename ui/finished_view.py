"""結果発表画面（FINISHED フェーズ）。"""

from typing import Callable

import streamlit as st

import database
from ui.legacy_result_view import render_legacy_result_view
from ui.styles import (
    COLOR_BLUE_DARK,
    COLOR_BLUE_MID,
    COLOR_ORANGE,
    render_character_gif,
    render_header,
    speak,
)


def render_finished_view(*, results: list[dict], on_restart: Callable[[], None]) -> None:
    """結果発表画面を描画する。

    Args:
        results:    各種目の計測結果リスト
        on_restart: 再スタートコールバック
    """
    avg_score = _compute_average_score(results)
    overall_grade = _score_to_grade(avg_score)

    # 初回描画時に DB 保存（前回比較で必要）
    _save_results_to_db_once(results)

    # 音声案内（初回のみ）
    if st.session_state.get("last_spoken") != "finished":
        speak(_score_to_speak_message(avg_score))
        st.session_state.last_spoken = "finished"

    # 1. ヘッダー
    st.markdown(
        render_header("", "けっか　はっぴょう！"),
        unsafe_allow_html=True,
    )

    # 2. グレードバナー（グレード・点数・前回比較）
    _render_grade_banner(grade=overall_grade, score=avg_score)

    # 3. キャラクター + 吹き出し（2カラム）
    char_col, bubble_col = st.columns([1, 2], gap="medium")
    with char_col:
        render_character_gif(width=160)
    with bubble_col:
        st.info(_score_to_bubble_message(avg_score))

    # 4. 種目別グレード（3カラム）
    _render_per_exercise_cards(results=results)

    # 5. アンケート（Google フォーム埋め込み）
    _render_survey_form()

    # 6. 研究者用折りたたみ（従来の詳細結果ビューをそのまま表示）
    with st.expander("くわしい　けっか（けんきゅうしゃ　よう）"):
        render_legacy_result_view(results=results, on_restart=on_restart)

    # 7. 「もう　いちど！」ボタン（最下部）
    st.button(
        "もう　いちど！",
        type="primary",
        use_container_width=True,
        on_click=on_restart,
    )


# -------------------------------------------------------
# 6: アンケート（Google フォーム）
# -------------------------------------------------------

# embedded=true で埋め込み専用のレイアウトに切り替わる
_SURVEY_FORM_URL = (
    "https://docs.google.com/forms/d/e/"
    "1FAIpQLSe9w24uhyt_6FvJQ9BvhdEZcHSolQ5oNoDXgfjoHdcpGFoEsw/"
    "viewform?embedded=true"
)


def _render_survey_form() -> None:
    """Google フォームを iframe で埋め込んで表示する。"""
    st.markdown(
        "<p style='font-size:20px;color:#378ADD;margin-top:24px;'>"
        "📝 アンケートに　こたえてね"
        "</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <iframe
            src="{_SURVEY_FORM_URL}"
            width="100%"
            height="800"
            frameborder="0"
            marginheight="0"
            marginwidth="0"
            style="border-radius:12px;">
            よみこみちゅう...
        </iframe>
        """,
        unsafe_allow_html=True,
    )


# -------------------------------------------------------
# 1〜2: グレードバナー
# -------------------------------------------------------

def _render_grade_banner(*, grade: str, score: float) -> None:
    """グレードバッジ・総合点・前回比較を表示する。"""
    grade_col, score_col, diff_col = st.columns([1, 2, 2])
    with grade_col:
        st.markdown(
            f'<div style="width:72px;height:72px;border-radius:50%;'
            f'background:{COLOR_ORANGE};display:flex;align-items:center;'
            f'justify-content:center;color:#FFFFFF;font-size:36px;'
            f'font-weight:800;margin:0 auto;">{grade}</div>',
            unsafe_allow_html=True,
        )
    with score_col:
        st.metric(label="ごうけい　てんすう", value=f"{score:.0f} てん")
    with diff_col:
        diff_text, diff_color = _build_diff_text(current_score=score)
        st.markdown(
            f'<div style="display:flex;align-items:center;justify-content:center;'
            f'height:100%;font-size:18px;font-weight:700;color:{diff_color};">'
            f'{diff_text}</div>',
            unsafe_allow_html=True,
        )


def _build_diff_text(*, current_score: float) -> tuple[str, str]:
    """前回スコアと比較し、表示テキストと色を返す。"""
    subject_id = st.session_state.get("subject_id")
    current_session_id = st.session_state.get("session_id")
    if not subject_id or current_session_id is None:
        return ("はじめての　チャレンジ！", COLOR_BLUE_DARK)

    sessions = database.get_session_history(subject_id)
    previous = next((s for s in sessions if s["id"] != current_session_id), None)
    if previous is None:
        return ("はじめての　チャレンジ！", COLOR_BLUE_DARK)

    previous_score = database.get_session_overall_score(previous["id"])
    if previous_score is None:
        return ("はじめての　チャレンジ！", COLOR_BLUE_DARK)

    diff = current_score - previous_score
    if diff > 0.5:
        return (f"▲ {diff:.0f}てん　あがったよ！", COLOR_ORANGE)
    if diff < -0.5:
        return (f"▼ {abs(diff):.0f}てん　さがったね", COLOR_BLUE_MID)
    return ("ぜんかいと　おなじくらい", COLOR_BLUE_DARK)


# -------------------------------------------------------
# 4: 種目別グレード
# -------------------------------------------------------

# 本人向け表示用の種目名（exercise.name の漢字を全部ひらがな・カタカナに）
_DISPLAY_NAMES_BY_KEY: dict[str, str] = {
    "banzai": "バンザイ",
    "right_leg_raise": "みぎあし　あげ",
    "left_leg_raise": "ひだりあし　あげ",
}


def _render_per_exercise_cards(*, results: list[dict]) -> None:
    """種目ごとのグレードと点数を3カラムで表示する。"""
    if not results:
        return
    cols = st.columns(len(results))
    for col, result in zip(cols, results):
        key = result.get("exercise_key", "")
        name = _DISPLAY_NAMES_BY_KEY.get(key, result.get("exercise_name", ""))
        grade = result.get("overall", "C")
        metrics = result.get("metrics", {})
        score = sum(metrics.values()) / len(metrics) if metrics else 0.0
        with col:
            st.markdown(
                f'<div style="background:#E6F1FB;border-radius:12px;'
                f'border:0.5px solid #B5D4F4;padding:16px;text-align:center;'
                f'margin-bottom:12px;">'
                f'<div style="font-size:16px;color:{COLOR_BLUE_DARK};margin-bottom:6px;">'
                f'{name}</div>'
                f'<div style="font-size:32px;font-weight:800;color:{COLOR_ORANGE};'
                f'line-height:1.1;">{grade}</div>'
                f'<div style="font-size:18px;font-weight:700;color:{COLOR_BLUE_DARK};">'
                f'{score:.0f}<span style="font-size:13px;">てん</span></div>'
                f'</div>',
                unsafe_allow_html=True,
            )


# -------------------------------------------------------
# DB 保存
# -------------------------------------------------------

def _save_results_to_db_once(results: list[dict]) -> None:
    """初回表示時のみ DB に結果を保存する。

    session_state.results_saved フラグで二重保存を防ぐ。
    overall_score は metrics の平均で計算し、grade は result["overall"] を使う。
    """
    if st.session_state.get("results_saved"):
        return
    session_id = st.session_state.get("session_id")
    if session_id is None:
        return

    for r in results:
        metrics = r.get("metrics", {})
        if not metrics:
            continue
        overall_score = sum(metrics.values()) / len(metrics)
        grade = r.get("overall", _score_to_grade(overall_score))
        try:
            database.save_result(
                session_id=session_id,
                exercise_key=r.get("exercise_key", ""),
                overall_score=overall_score,
                grade=grade,
                metric_scores={k: float(v) for k, v in metrics.items()},
            )
        except Exception:
            # 既に保存済み等のエラーは無視する（rerun で再実行された場合の保険）
            pass
    st.session_state.results_saved = True


# -------------------------------------------------------
# スコア計算ヘルパー
# -------------------------------------------------------

def _compute_average_score(results: list[dict]) -> float:
    """全種目の全指標スコアの平均を計算する。"""
    values = [
        v
        for result in results
        for v in result.get("metrics", {}).values()
        if isinstance(v, (int, float))
    ]
    return sum(values) / len(values) if values else 0.0


def _score_to_grade(score: float) -> str:
    """スコアをグレード（A/B/C/D）に変換する。"""
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    return "D"


def _score_to_bubble_message(score: float) -> str:
    """吹き出し表示用：全角スペースで読みやすく。"""
    if score >= 85:
        return "すごい！！　がんばったね！　えらい！"
    if score >= 70:
        return "よく　できました！　がんばったね！"
    if score >= 55:
        return "がんばったね！　えらい！　つぎも　やろう！"
    return "よく　チャレンジしたね！　えらい！"


def _score_to_speak_message(score: float) -> str:
    """音声読み上げ用：句読点で自然に区切る。"""
    if score >= 85:
        return "すごい！！がんばったね！えらい！"
    if score >= 70:
        return "よくできました！がんばったね！"
    if score >= 55:
        return "がんばったね！えらい！つぎも やろう！"
    return "よく チャレンジしたね！えらい！"
