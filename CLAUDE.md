# プロジェクト概要

## アプリの目的
ダウン症の方の運動能力を客観的に計測・記録するための研究用Webアプリケーション。
3種目の運動（バンザイ・右足上げ・左足上げ）をガイドしながら実施し、
姿勢ランドマークデータをもとに運動パフォーマンスを自動採点する。

## 研究背景
土田研究室が運営。被験者の身体能力評価を効率化することが目的。

---

# 技術スタック

- **言語**: Python 3.11（MediaPipeの安定動作のため3.13から移行）
- **Webフレームワーク**: Streamlit
- **データ処理**: pandas, numpy
- **可視化**: matplotlib, seaborn, plotly
- **姿勢推定**: MediaPipe Pose
- **データ保存**: SQLite
- **対象OS**: Mac/Windows/Linux すべて対応（クロスプラットフォーム）

---

# アプリの構成

## 3フェーズフロー
READY → CAMERA_CHECK → DEMO → COUNTDOWN → MEASURE → TRANSITION → ... → FINISHED
（バンザイ・右足上げ・左足上げの3種目分くり返す）

## 評価指標（6つ）
指標の定義はmetrics_config.yamlで管理する（コードにハードコードしない）。
現在の指標：
- head_movement（頭部の安定性）
- shoulder_tilt（肩の傾き）
- torso_tilt（体幹の傾き）
- leg_lift（足の上がり高さ）
- foot_sway（横方向の安定性）
- arm_sag（腕の下がり具合）

## 被験者識別
- セッション開始時に被験者番号を手入力（例：001）
- ログイン機能なし（将来的に拡張予定）

---

# データ保存設計

SQLiteを使用。以下のテーブル構成：

- sessions: id, subject_id（被験者番号）, created_at
- results: id, session_id, exercise_key, overall_score, created_at
- metric_scores: id, result_id, metric_key, value
  ※ metric_keyを文字列で持つことで、指標の変更・追加に対応

---

# コーディングルール

- **コメント**: 日本語
- **変数名・関数名**: 英語（スネークケース）
- **コミットメッセージ**: 日本語
- **指標定義**: metrics_config.yamlで管理し、コードにハードコードしない
- **クロスプラットフォーム対応**: ファイルパスはos.pathまたはPathlibを使用、
  絶対パスのハードコード禁止

---

# 開発ルール

- ファイルの作成・変更は自動で行う（確認不要）
- テストコードを必ず書く（pytestを使用）
- requirements.txtを常に最新の状態に保つ
- 未実装部分はスタブ関数として明示し、TODOコメントを残す

---

# 現在の実装状況

## 実装済み
- 7段階の画面フロー（state.py, ui/各view）
- お手本動画＋ウェブカメラの2カラム表示
- 円形プログレスタイマー
- 結果画面UI（グラフ・CSVエクスポート）

## 未実装（優先順位順）
1. SQLiteによるデータ保存
2. UI改善（被験者番号入力、スコア履歴表示など）
3. MediaPipe Poseによる実際のスコア計算ロジック

## 既知の問題
- 現在のスコアはすべてダミーデータ（build_dummy_result()）
- legacy_result_view.pyに開発者マシンの絶対パスがハードコードされている
- requirements.txtが存在しない

---

# ディレクトリ構成

```
3phase_motion_training_app/
├── CLAUDE.md
├── requirements.txt
├── metrics_config.yaml        # 指標定義（ハードコード禁止）
├── app.py                     # エントリーポイント
├── state.py                   # セッション状態管理
├── exercises.py               # 種目定義
├── database.py                # SQLite操作（未実装）
├── logic/
│   └── measurement.py         # 計測ロジック（MediaPipeスタブ）
├── ui/
│   ├── ready_view.py
│   ├── camera_check_view.py
│   ├── demo_view.py
│   ├── countdown_view.py
│   ├── measure_view.py
│   ├── transition_view.py
│   ├── finished_view.py
│   ├── training_stage.py
│   ├── media_blocks.py
│   └── legacy_result_view.py
├── assets/
│   ├── otehon_banzai.mp4
│   ├── otehon_migi.mp4
│   └── otehon_hidari.mp4
└── tests/                     # pytestテスト（未作成）
```
