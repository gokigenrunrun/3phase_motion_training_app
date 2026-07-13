"""結果発表画面（FINISHED フェーズ）。

3種目の計測結果（results）を受け取り、グレードバナー・種目別カード・
アンケート・研究者向け詳細ビューを表示する。初回描画時に一度だけ DB へ
結果を保存する（_save_results_to_db_once）。

注意: 画面上部のグレードは全種目の全指標をまとめて平均した値から算出し、
種目カードのグレードは build_real_result() 側で種目ごとに算出した値を
そのまま使う。DB保存用のスコアもここでさらに別途平均を計算しており、
「有限値の平均」という同じ処理が3箇所（本ファイルと scoring.py）に
分散している。
"""

import os
import tempfile
from typing import Callable

import numpy as np
import pandas as pd
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
    # 全種目・全指標をまとめて平均した点数からバナーのグレードを算出する
    # （種目カードのグレードとは別計算。モジュール docstring 参照）
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

    # 6. 研究者用折りたたみ（CSV採点 UI + 従来の詳細結果ビュー）
    with st.expander("くわしい　けっか（けんきゅうしゃ　よう）"):
        _render_researcher_csv_scoring()
        st.divider()
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
        diff_text, diff_color = _build_diff_text()
        st.markdown(
            f'<div style="display:flex;align-items:center;justify-content:center;'
            f'height:100%;font-size:18px;font-weight:700;color:{diff_color};">'
            f'{diff_text}</div>',
            unsafe_allow_html=True,
        )


def _build_diff_text() -> tuple[str, str]:
    """前回比較欄に表示する固定メッセージを返す。

    被験者番号入力を廃止し session_state.subject_id が常に空文字になったため、
    DB 上で「同一人物の前回セッション」を安全に特定する手段がない。
    以前は subject_id で database.get_session_history() を横断検索していたが、
    誤って別人のスコアと比較してしまう事故を避けるため、この横断検索は行わず
    回数に依存しない中立な固定メッセージのみを返す。
    """
    return ("よく　がんばったね！", COLOR_BLUE_DARK)


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
        finite = _finite_values(metrics)
        score = sum(finite) / len(finite) if finite else 0.0
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
        finite = _finite_values(metrics)
        if not finite:
            # 全指標が NaN（計測データなし等）の場合は DB に保存しない
            continue
        overall_score = sum(finite) / len(finite)
        grade = r.get("overall", _score_to_grade(overall_score))
        # NaN/inf は REAL NOT NULL 制約に反するため有限値のみ保存する
        finite_metric_scores = {
            k: float(v)
            for k, v in metrics.items()
            if isinstance(v, (int, float)) and np.isfinite(v)
        }
        try:
            database.save_result(
                session_id=session_id,
                exercise_key=r.get("exercise_key", ""),
                overall_score=overall_score,
                grade=grade,
                metric_scores=finite_metric_scores,
            )
        except Exception:
            # 既に保存済み等のエラーは無視する（rerun で再実行された場合の保険）
            pass
    st.session_state.results_saved = True


# -------------------------------------------------------
# スコア計算ヘルパー
# -------------------------------------------------------

def _finite_values(metrics: dict) -> list[float]:
    """metrics の値のうち、数値かつ有限（NaN/inf でない）ものだけを返す。

    実スコアでは適用外の指標（バンザイの leg_lift 等）が NaN になるため、
    平均計算や DB 保存の前に除外する。
    """
    return [
        float(v)
        for v in metrics.values()
        if isinstance(v, (int, float)) and np.isfinite(v)
    ]


def _compute_average_score(results: list[dict]) -> float:
    """全種目の全指標スコアの平均を計算する（NaN は除外）。"""
    values = [
        v
        for result in results
        for v in _finite_values(result.get("metrics", {}))
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


# -------------------------------------------------------
# 研究者用：CSV をアップロードして採点する暫定 UI
# -------------------------------------------------------

def _render_researcher_csv_scoring() -> None:
    """ランドマーク CSV をアップロード→旧アプリのロジックで採点する暫定 UI。"""
    from logic.calculate_metrics import (
        calculate_metrics_by_frame,
        load_pose_dataframe,
    )
    from logic.scoring import (
        calculate_overall_score,
        get_grade,
        score_from_frame_metrics,
    )

    st.markdown("#### CSVから採点（暫定）")

    side = st.radio(
        "CSVの種類",
        ["みぎあし（right）", "ひだりあし（left）"],
        horizontal=True,
        key="csv_side",
    )
    action = "right_leg" if "right" in side else "left_leg"

    uploaded_file = st.file_uploader(
        "ランドマークCSVをアップロード",
        type=["csv"],
        key="landmark_csv",
    )

    if uploaded_file is None:
        return

    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name

    try:
        pose_df = load_pose_dataframe(tmp_path)
        frame_df = calculate_metrics_by_frame(pose_df)
        scores = score_from_frame_metrics(frame_df, action=action)
        overall = calculate_overall_score(scores)
        grade = get_grade(overall)

        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                "そうごうスコア",
                f"{overall:.1f} てん" if not np.isnan(overall) else "N/A",
            )
        with col2:
            st.metric("グレード", grade)

        st.dataframe(
            pd.DataFrame(
                {
                    "指標": list(scores.keys()),
                    "スコア": [
                        f"{v:.1f}" if v is not None and not np.isnan(v) else "N/A"
                        for v in scores.values()
                    ],
                }
            ),
            hide_index=True,
        )

    except Exception as e:  # noqa: BLE001
        st.error(f"採点エラー：{e}")
        st.exception(e)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
