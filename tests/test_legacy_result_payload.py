"""詳細ビュー（ui/legacy_result_view.py）が実測データを使うことを確認するテスト。

以前は st.session_state["legacy_result_payload"] をセットする箇所がどこにも無く、
詳細ビュー（レーダーチャート・ドーナツ図・指標別フィードバック）は常に
build_dummy_result_payload() のダミー値にフォールバックしていた。

このテストでは、
  1. build_real_result_payload() が build_real_result() 相当の実測 results から
     正しく指標別スコアを集計すること
  2. ui/finished_view.py と同じ配線（session_state へのセット→描画）を経て、
     実際に描画される HTML に実測の指標別スコア・コメントが反映されること
     （ダミー値ではないこと）
を検証する。
"""

import math

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

from ui.legacy_result_view import SCORE_COLUMNS, build_real_result_payload


# -------------------------------------------------------
# テスト用の実測 results（build_real_result() が返す形式と同じ）
# -------------------------------------------------------

def _make_real_results() -> list[dict]:
    """leg_lift だけが低い、というシナリオの実測結果を1種目分作る。"""
    return [
        {
            "exercise_key": "right_leg_raise",
            "exercise_name": "みぎあし　あげ",
            "overall": "B",
            "metrics": {
                "head_movement": 90.0,
                "shoulder_tilt": 92.0,
                "torso_tilt": 88.0,
                "leg_lift": 15.0,  # ここだけ低い
                "foot_sway": 85.0,
                "arm_sag": 90.0,
            },
        }
    ]


# -------------------------------------------------------
# build_real_result_payload() の単体テスト
# -------------------------------------------------------

def test_build_real_result_payload_reflects_each_metric() -> None:
    """各指標のスコアが実測値どおりに個別反映されること（ダミーの固定値ではない）。"""
    payload = build_real_result_payload(_make_real_results())
    result_df = payload["result_df"]

    row = result_df.iloc[0]
    assert row["head_movement_score"] == pytest.approx(90.0)
    assert row["shoulder_tilt_score"] == pytest.approx(92.0)
    assert row["torso_tilt_score"] == pytest.approx(88.0)
    assert row["leg_lift_score"] == pytest.approx(15.0)
    assert row["foot_sway_score"] == pytest.approx(85.0)
    assert row["arm_sag_score"] == pytest.approx(90.0)

    # ダミーの固定値（head_movement_score=82.0 等）ではないこと
    assert row["head_movement_score"] != 82.0
    assert row["leg_lift_score"] != 76.0


def test_build_real_result_payload_total_score_is_mean_of_all_metrics() -> None:
    """total_score が全指標値の平均になっていること（グレードバナーと同じ計算式）。"""
    results = _make_real_results()
    payload = build_real_result_payload(results)
    total_score = float(payload["result_df"].iloc[0]["total_score"])

    all_values = list(results[0]["metrics"].values())
    expected = float(np.mean(all_values))
    assert total_score == pytest.approx(expected)


def test_build_real_result_payload_excludes_banzai_score() -> None:
    """banzai_score は現状方針（総合スコアに含めない）どおり、この payload でも算出しないこと。"""
    payload = build_real_result_payload(_make_real_results())
    result_df = payload["result_df"]
    assert "banzai_score_score" not in result_df.columns


def test_build_real_result_payload_falls_back_to_dummy_when_no_results() -> None:
    """results が無い（全種目で計測失敗）場合はダミー payload にフォールバックすること。"""
    payload = build_real_result_payload(None)
    assert payload["result_df"] is not None
    # ダミーの固定値であることを確認
    assert payload["result_df"].iloc[0]["head_movement_score"] == pytest.approx(82.0)


def test_build_real_result_payload_omits_frame_level_dummy_data() -> None:
    """フレーム単位のCSV等、実測できないデータをダミーで埋めて見せかけないこと。"""
    payload = build_real_result_payload(_make_real_results())
    assert payload["frame_scores_df"] is None
    assert payload["frame_scores_csv"] is None
    assert payload["pose_csv_bytes"] is None


# -------------------------------------------------------
# 描画レベルの検証（AppTest）
# -------------------------------------------------------

def _render_detail_view_with_real_data() -> None:
    """ui/finished_view.py が行うのと同じ配線を再現するテスト対象スクリプト。"""
    import streamlit as st

    from ui.legacy_result_view import build_real_result_payload, render_legacy_result_view

    results = [
        {
            "exercise_key": "right_leg_raise",
            "exercise_name": "みぎあし　あげ",
            "overall": "B",
            "metrics": {
                "head_movement": 90.0,
                "shoulder_tilt": 92.0,
                "torso_tilt": 88.0,
                "leg_lift": 15.0,
                "foot_sway": 85.0,
                "arm_sag": 90.0,
            },
        }
    ]
    # ui/finished_view.py の render_finished_view() が詳細ビュー表示前に行う配線と同じ
    st.session_state["legacy_result_payload"] = build_real_result_payload(results)
    render_legacy_result_view(results=results, on_restart=lambda: None)


def _all_markdown_html(at: AppTest) -> str:
    """AppTest 上でレンダリングされた markdown/html を1本の文字列に結合する。"""
    return "\n".join(md.value for md in at.markdown)


def test_detail_view_shows_low_metric_distinctly() -> None:
    """leg_lift だけ低いケースで、詳細ビューにその低さが個別に反映されること。

    ダミーpayloadでは leg_lift_score は常に 76.0 固定（他指標より一律に低いだけ）
    だが、ここでは実測値 15.0 が使われ、feedback もそれに応じた「low」コメントに
    なることを確認する。
    """
    at = AppTest.from_function(_render_detail_view_with_real_data)
    at.run()

    assert not at.exception

    html = _all_markdown_html(at)

    # 実測どおりの点数がそのまま表示されている
    assert "15.0 点" in html  # leg_lift（低い指標）
    assert "92.0 点" in html  # shoulder_tilt（高い指標）

    # leg_lift は「low」コメントテンプレートが選ばれている
    assert "ひざをさらに高く持ち上げて動きを強調しましょう。" in html
    # shoulder_tilt は「high」コメントテンプレートが選ばれている
    assert "肩のラインが水平に保たれています。" in html

    # ダミー固定値が出ていないこと
    assert "82.0 点" not in html
    assert "76.0 点" not in html


def test_detail_view_banzai_card_shows_no_data_message() -> None:
    """banzai_score は実測 results に含まれないため、詳細ビューでは
    スコア「-- 点」＋「データが不足しているため評価できません。」と表示されること
    （ダミー固定スコア 88.0 の代わりに欠損として扱われること）。"""
    at = AppTest.from_function(_render_detail_view_with_real_data)
    at.run()

    assert not at.exception

    html = _all_markdown_html(at)
    assert "データが不足しているため評価できません。" in html
    # 実測データがある6指標はすべて有限値のため、"-- 点" が出るのは
    # banzai_score カードのみ（欠損表示であることの確認）
    assert "-- 点" in html


def test_detail_view_total_score_matches_payload() -> None:
    """画面上部の総合スコア表示が build_real_result_payload() の total_score と一致すること。"""
    results_metrics = {
        "head_movement": 90.0,
        "shoulder_tilt": 92.0,
        "torso_tilt": 88.0,
        "leg_lift": 15.0,
        "foot_sway": 85.0,
        "arm_sag": 90.0,
    }
    expected_total = float(np.mean(list(results_metrics.values())))

    at = AppTest.from_function(_render_detail_view_with_real_data)
    at.run()

    assert not at.exception
    html = _all_markdown_html(at)
    assert f"{expected_total:.1f} 点" in html
