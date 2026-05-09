"""SQLiteによるデータ保存モジュール。"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

# プロジェクトルートからの相対パスでDBファイルを管理（絶対パスのハードコード禁止）
_PROJECT_ROOT = Path(__file__).parent
_DB_PATH = _PROJECT_ROOT / "data" / "assessment.db"


@contextmanager
def _connect() -> Generator[sqlite3.Connection, None, None]:
    """SQLite接続を管理するコンテキストマネージャ。

    - 外部キー制約を有効化
    - 正常終了時はコミット、例外発生時はロールバック
    - 必ず接続をクローズ
    """
    # dataディレクトリが存在しない場合は自動作成
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    # カラム名でアクセスできるようにRow型を設定
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """DBとテーブルを初期化する。存在する場合はスキップ。"""
    with _connect() as conn:
        # セッションテーブル：被験者番号と計測日時を管理
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id         INTEGER  PRIMARY KEY AUTOINCREMENT,
                subject_id TEXT     NOT NULL,
                created_at DATETIME NOT NULL
            )
        """)
        # 種目結果テーブル：総合スコアとグレードを管理
        conn.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id            INTEGER  PRIMARY KEY AUTOINCREMENT,
                session_id    INTEGER  NOT NULL REFERENCES sessions(id),
                exercise_key  TEXT     NOT NULL,
                overall_score REAL     NOT NULL,
                grade         TEXT     NOT NULL,
                created_at    DATETIME NOT NULL
            )
        """)
        # 指標スコアテーブル：metric_keyを文字列で持ち指標の変更・追加に対応
        conn.execute("""
            CREATE TABLE IF NOT EXISTS metric_scores (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                result_id  INTEGER NOT NULL REFERENCES results(id),
                metric_key TEXT    NOT NULL,
                value      REAL    NOT NULL
            )
        """)


def create_session(subject_id: str) -> int:
    """新しいセッションを作成し、session_idを返す。

    Args:
        subject_id: 被験者番号（例："001"）

    Returns:
        作成されたセッションのID
    """
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        cursor = conn.execute(
            "INSERT INTO sessions (subject_id, created_at) VALUES (?, ?)",
            (subject_id, now),
        )
        return cursor.lastrowid


def save_result(
    session_id: int,
    exercise_key: str,
    overall_score: float,
    grade: str,
    metric_scores: dict[str, float],
) -> int:
    """種目の結果と指標スコアを保存し、result_idを返す。

    Args:
        session_id:    紐づくセッションのID
        exercise_key:  種目キー（例："banzai"）
        overall_score: 総合スコア（0〜100）
        grade:         グレード（"A"/"B"/"C"/"D"）
        metric_scores: 指標キーとスコアの辞書（例：{"head_movement": 88.0}）

    Returns:
        作成された結果のID
    """
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        # 種目結果を保存
        cursor = conn.execute(
            """
            INSERT INTO results (session_id, exercise_key, overall_score, grade, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, exercise_key, overall_score, grade, now),
        )
        result_id = cursor.lastrowid

        # 各指標スコアを一括保存
        conn.executemany(
            "INSERT INTO metric_scores (result_id, metric_key, value) VALUES (?, ?, ?)",
            [(result_id, key, value) for key, value in metric_scores.items()],
        )
        return result_id


def get_session_history(subject_id: str) -> list[dict]:
    """被験者の過去セッション一覧を新しい順で返す。

    Args:
        subject_id: 被験者番号

    Returns:
        セッション情報の辞書リスト。該当なしの場合は空リスト。
        各辞書のキー: id, subject_id, created_at
    """
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, subject_id, created_at
            FROM sessions
            WHERE subject_id = ?
            ORDER BY created_at DESC
            """,
            (subject_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def get_session_overall_score(session_id: int) -> float | None:
    """指定セッション内の全 results の overall_score 平均を返す。

    Args:
        session_id: 対象セッションのID

    Returns:
        overall_score の平均値。results が存在しない場合は None。
    """
    with _connect() as conn:
        row = conn.execute(
            "SELECT AVG(overall_score) AS avg FROM results WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        if row is None or row["avg"] is None:
            return None
        return float(row["avg"])


def get_result_detail(result_id: int) -> dict:
    """result_idに紐づく結果と指標スコアを返す。

    Args:
        result_id: 取得対象の結果ID

    Returns:
        結果情報の辞書。"metrics"キーに指標スコアの辞書を含む。
        該当なしの場合は空の辞書。
        キー: id, session_id, exercise_key, overall_score, grade, created_at, metrics
    """
    with _connect() as conn:
        result_row = conn.execute(
            "SELECT * FROM results WHERE id = ?",
            (result_id,),
        ).fetchone()

        # 存在しないresult_idの場合は空辞書を返す
        if result_row is None:
            return {}

        metric_rows = conn.execute(
            "SELECT metric_key, value FROM metric_scores WHERE result_id = ?",
            (result_id,),
        ).fetchall()

        result = dict(result_row)
        result["metrics"] = {row["metric_key"]: row["value"] for row in metric_rows}
        return result
