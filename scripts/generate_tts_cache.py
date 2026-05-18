"""Gemini TTS のキャッシュを一括生成するスクリプト。

quota リセット後（翌日）に実行することで、アプリで使用する全セリフを
事前に音声生成して `data/tts_cache/` に保存する。

使い方:
    python scripts/generate_tts_cache.py

仕組み:
- 既にキャッシュ済みのセリフはスキップ
- 新しいセリフだけ Gemini TTS API を叩く
- 429 (quota 枯渇) を検出したら即座に停止
"""

import os
import sys
from pathlib import Path

# プロジェクトルートを sys.path に追加して ui パッケージを import 可能にする
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from google import genai  # noqa: E402
from google.genai import types  # noqa: E402

# styles.py の関数を使い回すことでキャッシュキー (sha1[:16]) を完全に一致させる
from ui.styles import _generate_gemini_tts, _tts_cache_path  # noqa: E402


# アプリで使用する全セリフ
ALL_SPEECHES: list[str] = [
    # READY
    "いっしょに うんどう しよう！ばんごうを いれてね",
    # CAMERA_CHECK
    "カメラを かくにん しよう。からだ ぜんぶ うつっていますか？",
    # TRANSITION（種目ごとに3パターン）
    "つぎは バンザイ です。まずは おてほんを かくにんしよう！",
    "つぎは みぎあし上げ です。まずは おてほんを かくにんしよう！",
    "つぎは ひだりあし上げ です。まずは おてほんを かくにんしよう！",
    # PRE_MEASURE 開始時
    "つぎは いっしょに やってみよう！",
    # MEASURE 種目別動作説明
    "ちいさくなって　うでを のばす！",
    "うでを よこに ひろげて、みぎあしを ゆっくり うえに あげよう！",
    "うでを よこに ひろげて、ひだりあしを ゆっくり うえに あげよう！",
    # FINISHED（スコア帯別）
    "すごい！！がんばったね！えらい！",
    "よくできました！がんばったね！",
    "がんばったね！えらい！つぎも やろう！",
    "よく チャレンジしたね！えらい！",
]


def main() -> int:
    """全セリフをキャッシュ生成。戻り値: 失敗時は 1、正常時は 0。"""
    api_key = os.getenv("GOOGLE_AI_API_KEY")
    if not api_key or api_key.strip() in ("", "ここにAPIキーを貼り付ける"):
        print("❌ GOOGLE_AI_API_KEY が設定されていません（.env を確認）")
        return 1

    ok = 0
    ng = 0
    skip = 0
    quota_hit = False

    print(f"全 {len(ALL_SPEECHES)} セリフのキャッシュを生成します")
    print(f"キャッシュ先: {_tts_cache_path(ALL_SPEECHES[0]).parent}\n")

    for text in ALL_SPEECHES:
        cache_path = _tts_cache_path(text)

        # 既にキャッシュ済みならスキップ
        if cache_path.exists():
            print(f"⏭️  スキップ（キャッシュ済み）: {text[:40]}")
            skip += 1
            continue

        try:
            audio_bytes, mime_type = _generate_gemini_tts(
                api_key, text, genai, types,
            )
            print(f"✅ 生成成功: {text[:40]}  ({len(audio_bytes):,} bytes, {mime_type})")
            ok += 1
        except Exception as exc:  # noqa: BLE001
            err_msg = str(exc)
            print(f"❌ 失敗: {text[:40]}")
            print(f"   エラー: {err_msg[:120]}")
            ng += 1

            # 429 (quota 枯渇) は即終了
            if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                quota_hit = True
                print("\n⚠️  quota 枯渇を検出。残りは明日以降に再実行してください。")
                break

    print(f"\n結果: ✅成功 {ok} / ⏭️スキップ {skip} / ❌失敗 {ng}")
    print(f"キャッシュ済みセリフ: {ok + skip} / {len(ALL_SPEECHES)}")

    return 1 if quota_hit else 0


if __name__ == "__main__":
    sys.exit(main())
