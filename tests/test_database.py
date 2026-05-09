"""database.pyのテスト。

テスト用に一時DBパスを monkeypatch で差し替え、
本番の data/assessment.db を汚染しない設計にしている。
"""

import pytest
from pathlib import Path

import database


# -------------------------------------------------------
# フィクスチャ
# -------------------------------------------------------

@pytest.fixture(autouse=True)
def use_temp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """各テストで独立した一時DBを使用する。"""
    test_db_path = tmp_path / "test_assessment.db"
    monkeypatch.setattr(database, "_DB_PATH", test_db_path)
    database.init_db()


# -------------------------------------------------------
# init_db
# -------------------------------------------------------

def test_init_db_is_idempotent() -> None:
    """init_dbを複数回呼び出しても例外が発生しないこと。"""
    database.init_db()
    database.init_db()


# -------------------------------------------------------
# create_session
# -------------------------------------------------------

def test_create_session_returns_int() -> None:
    """セッションIDとして正の整数が返ること。"""
    session_id = database.create_session("001")
    assert isinstance(session_id, int)
    assert session_id > 0


def test_create_session_increments_id() -> None:
    """複数作成時にIDが増加すること。"""
    id1 = database.create_session("001")
    id2 = database.create_session("001")
    assert id2 > id1


# -------------------------------------------------------
# get_session_history
# -------------------------------------------------------

def test_get_session_history_returns_created_session() -> None:
    """作成したセッションが履歴に含まれること。"""
    database.create_session("001")
    history = database.get_session_history("001")
    assert len(history) == 1
    assert history[0]["subject_id"] == "001"


def test_get_session_history_empty_for_unknown_subject() -> None:
    """存在しない被験者IDで履歴取得した場合に空リストを返すこと。"""
    history = database.get_session_history("999")
    assert history == []


def test_get_session_history_ordered_newest_first() -> None:
    """履歴が新しい順（降順）で返ること。"""
    database.create_session("002")
    database.create_session("002")
    database.create_session("002")
    history = database.get_session_history("002")
    assert len(history) == 3
    dates = [h["created_at"] for h in history]
    assert dates == sorted(dates, reverse=True)


def test_get_session_history_filters_by_subject_id() -> None:
    """異なる被験者のセッションが混在しないこと。"""
    database.create_session("001")
    database.create_session("002")
    history_001 = database.get_session_history("001")
    history_002 = database.get_session_history("002")
    assert len(history_001) == 1
    assert len(history_002) == 1
    assert history_001[0]["subject_id"] == "001"
    assert history_002[0]["subject_id"] == "002"


def test_get_session_history_contains_required_keys() -> None:
    """返却辞書に必須キーが含まれること。"""
    database.create_session("001")
    history = database.get_session_history("001")
    assert "id" in history[0]
    assert "subject_id" in history[0]
    assert "created_at" in history[0]


# -------------------------------------------------------
# save_result
# -------------------------------------------------------

def test_save_result_returns_int() -> None:
    """result_idとして正の整数が返ること。"""
    session_id = database.create_session("001")
    result_id = database.save_result(
        session_id=session_id,
        exercise_key="banzai",
        overall_score=85.0,
        grade="A",
        metric_scores={"head_movement": 90.0},
    )
    assert isinstance(result_id, int)
    assert result_id > 0


def test_save_result_with_empty_metric_scores() -> None:
    """指標スコアが空の辞書でも正常に保存されること。"""
    session_id = database.create_session("001")
    result_id = database.save_result(
        session_id=session_id,
        exercise_key="banzai",
        overall_score=85.0,
        grade="A",
        metric_scores={},
    )
    detail = database.get_result_detail(result_id)
    assert detail["metrics"] == {}


# -------------------------------------------------------
# get_result_detail
# -------------------------------------------------------

def test_get_result_detail_returns_correct_values() -> None:
    """保存した値が正しく取得できること。"""
    session_id = database.create_session("001")
    metrics = {"head_movement": 90.0, "shoulder_tilt": 80.0}
    result_id = database.save_result(
        session_id=session_id,
        exercise_key="banzai",
        overall_score=85.0,
        grade="A",
        metric_scores=metrics,
    )
    detail = database.get_result_detail(result_id)

    assert detail["exercise_key"] == "banzai"
    assert detail["overall_score"] == 85.0
    assert detail["grade"] == "A"
    assert detail["session_id"] == session_id


def test_get_result_detail_returns_all_metric_scores() -> None:
    """全指標スコアが正しく取得できること。"""
    session_id = database.create_session("001")
    metrics = {
        "head_movement": 88.0,
        "shoulder_tilt": 75.0,
        "torso_tilt": 82.0,
        "leg_lift": 70.0,
        "foot_sway": 65.0,
        "arm_sag": 78.0,
    }
    result_id = database.save_result(
        session_id=session_id,
        exercise_key="right_leg_raise",
        overall_score=76.3,
        grade="B",
        metric_scores=metrics,
    )
    detail = database.get_result_detail(result_id)

    assert len(detail["metrics"]) == 6
    for key, value in metrics.items():
        assert detail["metrics"][key] == value


def test_get_result_detail_returns_empty_for_nonexistent_id() -> None:
    """存在しないresult_idに対して空辞書を返すこと。"""
    detail = database.get_result_detail(9999)
    assert detail == {}


def test_get_result_detail_contains_required_keys() -> None:
    """返却辞書に必須キーが含まれること。"""
    session_id = database.create_session("001")
    result_id = database.save_result(
        session_id=session_id,
        exercise_key="banzai",
        overall_score=85.0,
        grade="A",
        metric_scores={},
    )
    detail = database.get_result_detail(result_id)
    for key in ("id", "session_id", "exercise_key", "overall_score", "grade", "created_at", "metrics"):
        assert key in detail


# -------------------------------------------------------
# 統合：セッション → 結果 → 指標の一連フロー
# -------------------------------------------------------

def test_full_flow_session_result_metrics() -> None:
    """セッション作成→結果保存→詳細取得の一連フローが正常に動作すること。"""
    session_id = database.create_session("003")
    assert session_id > 0

    result_id = database.save_result(
        session_id=session_id,
        exercise_key="left_leg_raise",
        overall_score=72.0,
        grade="B",
        metric_scores={"leg_lift": 68.0, "foot_sway": 76.0},
    )
    assert result_id > 0

    history = database.get_session_history("003")
    assert len(history) == 1
    assert history[0]["id"] == session_id

    detail = database.get_result_detail(result_id)
    assert detail["exercise_key"] == "left_leg_raise"
    assert detail["metrics"]["leg_lift"] == 68.0
    assert detail["metrics"]["foot_sway"] == 76.0
