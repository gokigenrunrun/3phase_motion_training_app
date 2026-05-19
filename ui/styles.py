"""アプリ全体の共通CSSとHTMLコンポーネントを管理するモジュール。

CSS の注入は app.py の main() で一度だけ行うこと。
各 view ファイルや fragment 内で get_common_css() を呼ばないこと。
動的コンテンツ（吹き出し・キャラクター）は st.info()/st.image() を使い
unsafe_allow_html=True を極力使わない。
"""

import base64
import json
import os
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

# .env から GOOGLE_AI_API_KEY を読み込む（インポート時に1回だけ）
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# -------------------------------------------------------
# カラー定数
# -------------------------------------------------------

COLOR_BLUE_BASE = "#378ADD"     # ベース青・完了（ヘッダー・ボーダー）
COLOR_BLUE_DARK = "#0C447C"     # 濃い青（テキスト）
COLOR_BLUE_LIGHT = "#E6F1FB"    # 薄い水色（カード背景）
COLOR_BLUE_MID = "#B5D4F4"      # 未実施・非アクティブ
COLOR_ORANGE = "#FF8C00"        # オレンジ・現在進行中・アクション
COLOR_ORANGE_LIGHT = "#FFF3E0"  # 薄いオレンジ（フィードバック背景）
COLOR_WHITE = "#FFFFFF"


# -------------------------------------------------------
# 共通CSS（app.py の main() で一度だけ注入する）
# -------------------------------------------------------

def get_common_css() -> str:
    """アプリ全体の共通CSSを返す。unsafe_allow_html=True で一度だけ注入する。"""
    return f"""<style>
/* Streamlit上部の黒いバーを非表示 */
header[data-testid="stHeader"] {{
    display: none !important;
    height: 0 !important;
}}

/* 右上メニュー・ツールバーを非表示 */
#MainMenu {{ display: none !important; }}
[data-testid="stToolbar"] {{ display: none !important; }}
[data-testid="stDecoration"] {{ display: none !important; }}
[data-testid="collapsedControl"] {{ display: none !important; }}

/* メインコンテンツの余白をゼロにする */
.stMainBlockContainer {{
    padding-top: 0 !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
    max-width: 100% !important;
}}

/* appBlock全体の余白もゼロ */
.stAppViewBlockContainer {{
    padding-top: 0 !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
    max-width: 100% !important;
}}

/* コンテンツを中央800px以内に収める（ヘッダーはネガティブマージンで横幅いっぱい） */
section[data-testid="stMain"] > div {{
    max-width: 800px !important;
    margin-left: auto !important;
    margin-right: auto !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
}}

/* ふりがな */
rt {{
    font-size: 12px;
    color: {COLOR_BLUE_BASE};
}}

/* ボタン全般（サイズ・形状） */
div[data-testid="stButton"] button {{
    font-size: 22px !important;
    height: 64px !important;
    border-radius: 12px !important;
    width: 100% !important;
}}

/* primary ボタン（は じ め る・だいじょうぶ・もう いちど）はオレンジ */
div[data-testid="stButton"] button[kind="primary"] {{
    background-color: {COLOR_ORANGE} !important;
    border: 2px solid {COLOR_ORANGE} !important;
    color: {COLOR_WHITE} !important;
}}
div[data-testid="stButton"] button[kind="primary"]:hover {{
    background-color: #E07A00 !important;
    border-color: #E07A00 !important;
}}

/* 全体フォント・背景 */
.stApp {{
    background-color: #FFFFFF !important;
    font-size: 20px;
    font-family: 'Hiragino Sans', 'Noto Sans CJK JP', sans-serif;
}}
</style>"""


# -------------------------------------------------------
# ヘッダー（静的HTML・unsafe_allow_html=True で使用可）
# -------------------------------------------------------

def render_header(icon: str, title_html: str) -> str:
    """ヘッダーHTMLを返す。静的コンテンツのため unsafe_allow_html=True で安全に使用できる。

    Args:
        icon:       絵文字アイコン。空文字の場合はアイコン円を描画しない
        title_html: タイトルのHTML文字列（例: "<ruby>運動<rt>うんどう</rt></ruby>"）
    """
    icon_block = (
        f'<div style="width:48px;height:48px;background:{COLOR_WHITE};border-radius:50%;'
        f'display:flex;align-items:center;justify-content:center;font-size:24px;flex-shrink:0;">'
        f'{icon}</div>'
        if icon else ""
    )
    # render_header_with_timer と同じ寸法（min-height:88px）に統一して
    # フェーズが切り替わっても動画・カメラの y 座標が変わらないようにする
    return (
        f'<div data-app-header="1" '
        f'style="background:{COLOR_BLUE_BASE};border-radius:0 0 12px 12px;'
        f'padding:12px 20px;display:flex;align-items:center;gap:12px;'
        f'min-height:88px;box-sizing:border-box;'
        f'margin-left:-1rem;margin-right:-1rem;margin-top:-1rem;margin-bottom:16px;">'
        f'{icon_block}'
        f'<div data-app-header-title="1" '
        f'style="color:{COLOR_WHITE};font-size:20px;font-weight:700;line-height:1.3;">'
        f'{title_html}</div>'
        f'</div>'
    )


def render_header_with_timer(
    icon: str,
    title_html: str,
    remaining: int,
    duration: float,
) -> str:
    """ヘッダー右端の上端に 64×64 円形タイマーを埋め込んだHTMLを返す。

    レイアウト:
    - ヘッダー全体は align-items: flex-start でタイマーを上端に寄せる
    - 左側のアイコン+タイトルは内側の padding:12px 0 で上下中央配置を維持
    - SVG は viewBox 0 0 56 56 で内側をヘッダー色に塗ってシームレスに統合

    Args:
        icon:       絵文字アイコン（例: "⏱"）。空文字なら左の白丸自体を出さない
        title_html: タイトルのHTML文字列（ruby タグなど可）
        remaining:  残り秒数（整数）
        duration:   フェーズ全体の秒数
    """
    r = 22
    circumference = 2 * 3.14159 * r  # ≈ 138.23
    progress = max(0.0, min(1.0, remaining / duration)) if duration > 0 else 0.0
    offset = circumference * (1.0 - progress)

    icon_block = (
        f'<div style="width:40px;height:40px;border-radius:50%;'
        f'background:{COLOR_WHITE};display:flex;align-items:center;'
        f'justify-content:center;font-size:20px;flex-shrink:0;">{icon}</div>'
        if icon else ""
    )

    return (
        # 行頭空白なしで連結（Markdown コードブロック化を回避）
        # ヘッダー本体: vertical padding は 0 にして子要素側で個別に padding
        f'<div style="background:{COLOR_BLUE_BASE};padding:0 20px;'
        f'display:flex;align-items:flex-start;justify-content:space-between;'
        f'margin-left:-1rem;margin-right:-1rem;margin-top:-1rem;margin-bottom:16px;'
        f'min-height:64px;box-sizing:border-box;'
        f'border-radius:0 0 12px 12px;">'
        # 左: アイコン+タイトル（padding で上下中央配置）
        f'<div style="display:flex;align-items:center;gap:12px;padding:12px 0;">'
        f'{icon_block}'
        f'<div style="color:{COLOR_WHITE};font-size:20px;font-weight:500;'
        f'line-height:1.3;">{title_html}</div>'
        f'</div>'
        # 右: 64×64 円形タイマー（上端に寄せる・SVG 内座標は 56）
        f'<svg width="64" height="64" viewBox="0 0 56 56" '
        f'xmlns="http://www.w3.org/2000/svg" '
        f'style="flex-shrink:0;align-self:flex-start;">'
        # 背景の薄い円
        f'<circle cx="28" cy="28" r="{r}" fill="none" '
        f'stroke="rgba(255,255,255,0.25)" stroke-width="4"/>'
        # オレンジのゲージ
        f'<circle cx="28" cy="28" r="{r}" fill="none" '
        f'stroke="{COLOR_ORANGE}" stroke-width="4" '
        f'stroke-dasharray="{circumference:.2f}" '
        f'stroke-dashoffset="{offset:.2f}" '
        f'stroke-linecap="round" '
        f'transform="rotate(-90 28 28)"/>'
        # 内側をヘッダーと同じ青で塗る（一体感）
        f'<circle cx="28" cy="28" r="18" fill="{COLOR_BLUE_BASE}"/>'
        # 白文字で残り秒数
        f'<text x="28" y="33" text-anchor="middle" fill="white" '
        f'font-size="16" font-weight="700" font-family="sans-serif">'
        f'{remaining}</text>'
        f'</svg>'
        f'</div>'
    )


# -------------------------------------------------------
# キャラクターSVG（st.image() で表示・unsafe_allow_html 不要）
# -------------------------------------------------------

def get_character_svg() -> str:
    """棒人間SVGの base64 データURIを返す。st.image() で表示する。"""
    svg = (
        '<svg width="80" height="100" viewBox="0 0 60 80" xmlns="http://www.w3.org/2000/svg">'
        f'<circle cx="30" cy="12" r="10" fill="none" stroke="{COLOR_BLUE_BASE}" stroke-width="3"/>'
        f'<line x1="30" y1="22" x2="30" y2="52" stroke="{COLOR_BLUE_BASE}" stroke-width="3"/>'
        f'<line x1="30" y1="32" x2="10" y2="44" stroke="{COLOR_BLUE_BASE}" stroke-width="3"/>'
        f'<line x1="30" y1="32" x2="50" y2="44" stroke="{COLOR_BLUE_BASE}" stroke-width="3"/>'
        f'<line x1="30" y1="52" x2="12" y2="72" stroke="{COLOR_BLUE_BASE}" stroke-width="3"/>'
        f'<line x1="30" y1="52" x2="48" y2="72" stroke="{COLOR_BLUE_BASE}" stroke-width="3"/>'
        '</svg>'
    )
    b64 = base64.b64encode(svg.encode()).decode()
    return f"data:image/svg+xml;base64,{b64}"


# -------------------------------------------------------
# プログレスサークル（st.image() で表示・unsafe_allow_html 不要）
# -------------------------------------------------------

def render_countdown_overlay(
    remaining: int,
    duration: float,
    zero_text: str = "Start!",
) -> str:
    """半透明オーバーレイ + 200×200 円形カウントダウン SVG の HTML を返す。

    position:fixed で全画面を覆い、background は rgba(0,0,0,0.35) の薄暗幕。
    pointer-events:none なので背後の操作はブロックしない。
    COUNTDOWN・PRE_DEMO どちらのフェーズからも利用する共有ヘルパー。
    Markdown のコードブロック化を避けるため、行頭空白なしの 1 行 HTML として返す。

    Args:
        remaining:  残り秒数（整数）
        duration:   フェーズ全体の秒数
        zero_text:  remaining=0 のときに表示する文字列（デフォルト "Start!"）
    """
    r = 80
    circumference = 2 * 3.14159 * r  # ≒ 502.65
    progress = max(0.0, min(1.0, remaining / duration)) if duration > 0 else 0.0
    offset = circumference * (1 - progress)
    display_text = str(remaining) if remaining > 0 else zero_text
    # 多文字（"Start!" 等）はフォントを少し小さくして円内に収める
    font_size = 64 if remaining > 0 else 48

    return (
        f'<div style="position:fixed;top:0;left:0;right:0;bottom:0;'
        f'background:rgba(0,0,0,0.35);display:flex;flex-direction:column;'
        f'align-items:center;justify-content:center;z-index:1000;'
        f'pointer-events:none;">'
        f'<svg width="200" height="200" viewBox="0 0 200 200" '
        f'xmlns="http://www.w3.org/2000/svg">'
        # 背景の薄い円
        f'<circle cx="100" cy="100" r="{r}" fill="none" '
        f'stroke="rgba(255,255,255,0.2)" stroke-width="10"/>'
        # 進捗を示す青い円弧（12時方向起点・時計回りに減る）
        f'<circle cx="100" cy="100" r="{r}" fill="none" '
        f'stroke="{COLOR_BLUE_BASE}" stroke-width="10" '
        f'stroke-dasharray="{circumference:.2f}" '
        f'stroke-dashoffset="{offset:.2f}" '
        f'stroke-linecap="round" '
        f'transform="rotate(-90 100 100)"/>'
        # 内側の半透明黒円（数字の可読性向上）
        f'<circle cx="100" cy="100" r="68" fill="rgba(0,0,0,0.4)"/>'
        # 残り秒数 / zero_text
        f'<text x="100" y="118" text-anchor="middle" fill="white" '
        f'font-size="{font_size}" font-weight="700" '
        f'font-family="sans-serif">'
        f'{display_text}</text>'
        f'</svg>'
        f'</div>'
    )


def render_start_display_overlay() -> str:
    """円形カウントダウンと同じデザインの中央に「Start!!」を表示するオーバーレイ。

    PRE_MEASURE のカウントダウン終了直後 (START_DISPLAY フェーズ) に
    2 秒間表示する。render_countdown_overlay と統一デザイン。
    pointer-events:none なので背後の操作はブロックしない。
    Markdown のコードブロック化を避けるため、行頭空白なしの 1 行 HTML として返す。
    """
    r = 80
    circumference = 2 * 3.14159 * r  # ≒ 502.65

    return (
        f'<div style="position:fixed;top:0;left:0;right:0;bottom:0;'
        f'background:rgba(0,0,0,0.35);display:flex;flex-direction:column;'
        f'align-items:center;justify-content:center;z-index:1000;'
        f'pointer-events:none;">'
        f'<svg width="200" height="200" viewBox="0 0 200 200" '
        f'xmlns="http://www.w3.org/2000/svg">'
        # 背景の薄い円（カウントダウンと同じ）
        f'<circle cx="100" cy="100" r="{r}" fill="none" '
        f'stroke="rgba(255,255,255,0.2)" stroke-width="10"/>'
        # 青い円（満タン状態 = 円弧 100%）
        f'<circle cx="100" cy="100" r="{r}" fill="none" '
        f'stroke="{COLOR_BLUE_BASE}" stroke-width="10" '
        f'stroke-dasharray="{circumference:.2f}" '
        f'stroke-dashoffset="0" '
        f'stroke-linecap="round" '
        f'transform="rotate(-90 100 100)"/>'
        # 内側の半透明黒円（テキストの可読性向上）
        f'<circle cx="100" cy="100" r="68" fill="rgba(0,0,0,0.4)"/>'
        # Start!! テキスト
        f'<text x="100" y="108" text-anchor="middle" fill="white" '
        f'font-size="28" font-weight="700" font-family="sans-serif">'
        f'Start!!</text>'
        f'</svg>'
        f'</div>'
    )


def render_progress_circle(remaining: float, total: float, size: int = 160) -> str:
    """残り時間を円形プログレスバーで表示するSVGの base64 データURIを返す。

    st.image() で表示することを前提とする（unsafe_allow_html=True 不要）。
    12時方向から時計回りにオレンジの弧が減っていく。

    Args:
        remaining: 残り秒数（浮動小数）
        total:     フェーズ全体の秒数
        size:      SVG の一辺ピクセル数（デフォルト 160）

    Returns:
        "data:image/svg+xml;base64,..." 形式の文字列
    """
    stroke_width = 12
    r = (size - stroke_width * 2) / 2
    cx = cy = size / 2
    circumference = 2 * 3.14159265 * r
    progress = max(0.0, min(1.0, remaining / total)) if total > 0 else 0.0
    offset = circumference * (1.0 - progress)
    remaining_int = max(0, int(remaining))

    svg = (
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" '
        f'xmlns="http://www.w3.org/2000/svg">'
        # トラック（薄い青の背景円）
        f'<circle cx="{cx}" cy="{cy}" r="{r:.2f}" '
        f'fill="none" stroke="{COLOR_BLUE_MID}" stroke-width="{stroke_width}"/>'
        # 進捗弧（オレンジ）: 12時方向を起点に -90度回転
        f'<circle cx="{cx}" cy="{cy}" r="{r:.2f}" '
        f'fill="none" stroke="{COLOR_ORANGE}" stroke-width="{stroke_width}" '
        f'stroke-dasharray="{circumference:.2f}" stroke-dashoffset="{offset:.2f}" '
        f'stroke-linecap="round" transform="rotate(-90 {cx} {cy})"/>'
        # 中央: 残り秒数
        f'<text x="{cx}" y="{cy - 8}" text-anchor="middle" '
        f'font-size="36" font-weight="700" fill="{COLOR_BLUE_DARK}" '
        f'font-family="Hiragino Sans, Noto Sans CJK JP, sans-serif">'
        f'{remaining_int}</text>'
        # 中央: ラベル
        f'<text x="{cx}" y="{cy + 20}" text-anchor="middle" '
        f'font-size="15" fill="{COLOR_BLUE_BASE}" '
        f'font-family="Hiragino Sans, Noto Sans CJK JP, sans-serif">'
        f'びょう</text>'
        f'</svg>'
    )
    b64 = base64.b64encode(svg.encode()).decode()
    return f"data:image/svg+xml;base64,{b64}"


# -------------------------------------------------------
# キャラクター GIF（アニメーション再生）
# -------------------------------------------------------

@st.cache_data(show_spinner=False)
def _load_gif_base64(gif_path: str, mtime_ns: int) -> str:
    """GIF の base64 をキャッシュして返す。mtime でキャッシュ無効化。"""
    return base64.b64encode(Path(gif_path).read_bytes()).decode()


def render_character_gif(width: int = 160) -> None:
    """キャラクターの GIF をアニメーション付きで表示する。

    <img> タグは React の dangerouslySetInnerHTML でも安全に動作するため、
    unsafe_allow_html=True で問題なく描画できる（<script> と違い実行リスクなし）。
    """
    gif_path = Path(__file__).resolve().parent.parent / "assets" / "images" / "character01_cheer.gif"
    if not gif_path.exists():
        return

    gif_b64 = _load_gif_base64(str(gif_path), gif_path.stat().st_mtime_ns)
    st.markdown(
        f"""
        <div style="display:flex;justify-content:center;margin:8px 0;">
            <img src="data:image/gif;base64,{gif_b64}"
                 width="{width}"
                 alt="character"
                 style="image-rendering:auto;">
        </div>
        """,
        unsafe_allow_html=True,
    )


# -------------------------------------------------------
# BGM 再生
# -------------------------------------------------------

@st.cache_data(show_spinner=False)
def _load_bgm_base64(bgm_path: str, mtime_ns: int) -> str:
    """BGM の base64 文字列をキャッシュして返す。

    mtime_ns（ファイル更新時刻）をキャッシュキーに含めることで、
    ファイル上書き時に自動でキャッシュを無効化する。
    """
    return base64.b64encode(Path(bgm_path).read_bytes()).decode()


def play_bgm() -> None:
    """BGM をループ再生する。

    assets/audio/bgm.mp3 が存在し、かつ空ファイルでない場合のみ動作する。
    <audio> 要素を **親ドキュメント (window.parent)** に追加することで
    iframe が破棄されても再生が継続し、設定パネルから直接音量を変更できる。
    自動再生がブロックされた場合は親ドキュメントの最初のクリック等で再試行する。
    """
    bgm_path = Path(__file__).resolve().parent.parent / "assets" / "audio" / "bgm.mp3"
    if not bgm_path.exists() or bgm_path.stat().st_size == 0:
        return

    bgm_b64 = _load_bgm_base64(str(bgm_path), bgm_path.stat().st_mtime_ns)
    initial_volume = st.session_state.get("bgm_volume", 30) / 100

    components.html(
        f"""
        <script>
        (function() {{
            try {{
                var parent = window.parent;
                if (parent._bgmInit) return;
                parent._bgmInit = true;

                var audio = parent.document.createElement('audio');
                audio.src = "data:audio/mp3;base64,{bgm_b64}";
                audio.loop = true;
                audio.volume = {initial_volume};
                parent.document.body.appendChild(audio);
                parent._bgmAudio = audio;

                function tryPlay() {{
                    return audio.play()
                        .then(function() {{ return true; }})
                        .catch(function() {{ return false; }});
                }}

                tryPlay().then(function(ok) {{
                    if (ok) return;
                    var unlock = function() {{
                        tryPlay();
                        parent.document.removeEventListener('click', unlock, true);
                        parent.document.removeEventListener('keydown', unlock, true);
                        parent.document.removeEventListener('touchstart', unlock, true);
                    }};
                    parent.document.addEventListener('click', unlock, true);
                    parent.document.addEventListener('keydown', unlock, true);
                    parent.document.addEventListener('touchstart', unlock, true);
                }});
            }} catch (e) {{ console.error('play_bgm error:', e); }}
        }})();
        </script>
        """,
        height=0,
    )


# -------------------------------------------------------
# 音声読み上げ（Web Speech API）
# -------------------------------------------------------

def cleanup_measure_dom() -> None:
    """PRE_MEASURE で parent.body に追加された timer/overlay DOM を削除する。

    PRE_MEASURE 以外のフェーズの view 冒頭で呼ぶことで、JS タイマーの
    残骸が画面に残り続ける問題を防ぐ。`_preMeasureRunning` フラグも
    リセットして、次回 PRE_MEASURE の JS が正しく起動できるようにする。
    """
    components.html(
        """
        <script>
        (function() {
            try {
                var pdoc = window.parent.document;
                ['_pmOverlay', '_pmTimer'].forEach(function(id) {
                    var el = pdoc.getElementById(id);
                    if (el && el.parentNode) {
                        el.parentNode.removeChild(el);
                    }
                });
                if (window.parent._preMeasureRunning !== undefined) {
                    window.parent._preMeasureRunning = false;
                }
            } catch (e) { /* 黙って無視 */ }
        })();
        </script>
        """,
        height=0,
    )


def _resolve_api_key() -> str | None:
    """GOOGLE_AI_API_KEY を環境変数 → st.secrets の順に探して返す。

    ローカルでは .env、Streamlit Cloud では Secrets（TOML）から読めるよう
    両方の経路をサポートする。
    """
    key = os.getenv("GOOGLE_AI_API_KEY")
    if key:
        return key
    try:
        return st.secrets.get("GOOGLE_AI_API_KEY")
    except Exception:
        return None


def speak(text: str, rate: float = 0.85, pitch: float = 1.1) -> None:
    """Google AI Studio (Gemini TTS) で日本語テキストを読み上げる。

    生成した音声を base64 にして components.html() の iframe で再生する。
    GOOGLE_AI_API_KEY が無い・SDK 失敗時は Web Speech API にフォールバック。
    同じテキストの連続読み上げは session_state で抑制する。

    Args:
        text:  読み上げるテキスト
        rate:  Web Speech API フォールバック時のみ使用（速度）
        pitch: Web Speech API フォールバック時のみ使用（声の高さ）
    """
    # 同じテキストの重複再生を防止（フェーズ遷移時に session_state でリセット）
    cache_key = f"spoken_{hash(text)}"
    if st.session_state.get(cache_key):
        return
    st.session_state[cache_key] = True

    api_key = _resolve_api_key()
    if not api_key or api_key.strip() in ("", "ここにAPIキーを貼り付ける"):
        _speak_web_speech(text, rate, pitch)
        return

    try:
        from google import genai
        from google.genai import types

        # 音声バイト列を取得（API キー付きでキャッシュ）
        audio_bytes, mime_type = _generate_gemini_tts(api_key, text, genai, types)

        audio_b64 = base64.b64encode(audio_bytes).decode()
        volume = st.session_state.get("speech_volume", 80) / 100

        components.html(
            f"""
            <script>
            (function() {{
                try {{
                    var audio = new Audio("data:{mime_type};base64,{audio_b64}");
                    audio.volume = {volume};
                    audio.play().catch(function(e) {{
                        console.log('[TTS] audio play error:', e);
                    }});
                }} catch (e) {{ console.log('[TTS] inject error:', e); }}
            }})();
            </script>
            """,
            height=0,
        )

    except Exception as e:  # noqa: BLE001
        print(f"[TTS] Google AI Studio error: {e}")
        _speak_web_speech(text, rate, pitch)


_TTS_CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "tts_cache"


def _tts_cache_path(text: str) -> Path:
    """テキスト文字列ごとの WAV キャッシュファイルパスを返す。"""
    import hashlib
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]
    return _TTS_CACHE_DIR / f"{digest}.wav"


@st.cache_data(show_spinner=False, max_entries=64)
def _generate_gemini_tts(api_key: str, text: str, _genai, _types) -> tuple[bytes, str]:
    """Gemini TTS で音声を生成し (bytes, mime_type) を返す。

    無料枠 (10 req/day) を節約するため、生成した WAV をディスクに永続キャッシュ。
    同じテキストは 2 回目以降 API を叩かない。Gemini TTS は生 PCM を返すので
    ブラウザ再生可能な WAV にラップして保存。
    """
    # ── ディスクキャッシュ ──
    cache_file = _tts_cache_path(text)
    if cache_file.exists():
        return (cache_file.read_bytes(), "audio/wav")

    # 短い文字列だと TTS モデルがテキスト生成と誤認することがあるため、
    # プロンプトを段階的に強化しながら複数フォーマットでリトライする。
    # ただし 429 (quota exhausted) はリトライしても無駄なので即座に raise。
    prompts = [
        f"Say in a friendly Japanese voice: 「{text}」",
        f"次の日本語の文を、明るく自然な声で読み上げてください。文: 「{text}」",
        f"以下のテキストを音声で出力してください。テキスト全体を必ず読み上げること。テキスト: 「{text}」",
    ]

    client = _genai.Client(api_key=api_key)
    response = None
    last_error: Exception | None = None
    for prompt in prompts:
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash-preview-tts",
                contents=prompt,
                config=_types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=_types.SpeechConfig(
                        voice_config=_types.VoiceConfig(
                            prebuilt_voice_config=_types.PrebuiltVoiceConfig(
                                voice_name="Kore",
                            ),
                        ),
                    ),
                ),
            )
            # 空レスポンスチェック（parts が無いと別プロンプトで再試行）
            if (response.candidates
                    and response.candidates[0].content
                    and getattr(response.candidates[0].content, "parts", None)
                    and getattr(response.candidates[0].content.parts[0], "inline_data", None)):
                break  # 成功
            last_error = RuntimeError("Gemini TTS: parts が空")
            response = None
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            response = None
            # 429 (quota exhausted) はリトライしても枯渇のままなので即終了
            if "429" in str(exc) or "RESOURCE_EXHAUSTED" in str(exc):
                break

    if response is None:
        raise last_error or RuntimeError("Gemini TTS: 全リトライ失敗")
    part = response.candidates[0].content.parts[0]
    pcm_data = part.inline_data.data
    raw_mime = part.inline_data.mime_type or ""

    # mime から sample rate を抽出（例: audio/L16;codec=pcm;rate=24000）
    sample_rate = 24000
    for token in raw_mime.split(";"):
        token = token.strip()
        if token.startswith("rate="):
            try:
                sample_rate = int(token.split("=", 1)[1])
            except ValueError:
                pass

    wav_bytes = _pcm_to_wav(pcm_data, sample_rate=sample_rate, bits_per_sample=16, channels=1)

    # ディスクキャッシュに保存（次回以降 API を叩かない）
    try:
        _TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file.write_bytes(wav_bytes)
    except OSError:
        pass  # キャッシュ書き込み失敗は致命的でない

    return (wav_bytes, "audio/wav")


def _pcm_to_wav(pcm_data: bytes, *, sample_rate: int, bits_per_sample: int, channels: int) -> bytes:
    """生 PCM (L16) バイト列に WAV ヘッダーを付けて返す。"""
    import struct

    byte_rate = sample_rate * channels * bits_per_sample // 8
    block_align = channels * bits_per_sample // 8
    data_size = len(pcm_data)
    fmt_chunk_size = 16
    riff_size = 4 + (8 + fmt_chunk_size) + (8 + data_size)

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        riff_size,
        b"WAVE",
        b"fmt ",
        fmt_chunk_size,
        1,  # PCM format
        channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size,
    )
    return header + pcm_data


def _speak_web_speech(text: str, rate: float = 0.85, pitch: float = 1.1) -> None:
    """フォールバック用 Web Speech API での読み上げ（API キー無し or 失敗時）。"""
    safe_text = json.dumps(text, ensure_ascii=False)
    components.html(
        f"""
        <script>
        (function() {{
            var parent = null, synth = null, Utterance = null;
            try {{ parent = window.parent; }} catch (e) {{}}
            try {{
                synth = (parent && parent.speechSynthesis) || window.speechSynthesis;
                Utterance = (parent && parent.SpeechSynthesisUtterance) || window.SpeechSynthesisUtterance;
            }} catch (e) {{
                synth = window.speechSynthesis;
                Utterance = window.SpeechSynthesisUtterance;
            }}
            if (!synth || !Utterance) return;
            synth.cancel();
            var u = new Utterance({safe_text});
            u.lang = 'ja-JP';
            u.rate = {rate};
            u.pitch = {pitch};
            try {{
                u.volume = (parent && parent._speechVolume !== undefined)
                    ? parent._speechVolume : 0.8;
            }} catch (e) {{
                u.volume = 0.8;
            }}
            synth.speak(u);
        }})();
        </script>
        """,
        height=0,
    )


# -------------------------------------------------------
# 音量設定ボタン・パネル
# -------------------------------------------------------

def _init_settings_state() -> None:
    """設定関連の session_state 既定値を初期化する。"""
    if "show_settings" not in st.session_state:
        st.session_state.show_settings = False
    if "bgm_volume" not in st.session_state:
        st.session_state.bgm_volume = 30
    if "speech_volume" not in st.session_state:
        st.session_state.speech_volume = 80


def render_settings_button() -> None:
    """画面右上に⚙️設定ボタンを固定表示する。"""
    _init_settings_state()

    # 設定ボタン専用の固定配置 CSS（key="settings_toggle" にスコープ）
    st.markdown(
        """
        <style>
        .st-key-settings_toggle {
            position: fixed !important;
            top: 16px !important;
            right: 20px !important;
            z-index: 9999 !important;
            width: auto !important;
            height: auto !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        .st-key-settings_toggle button {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            font-size: 24px !important;
            width: 40px !important;
            height: 40px !important;
            min-height: 40px !important;
            padding: 0 !important;
            color: #378ADD !important;
        }
        .st-key-settings_toggle button:hover {
            background: rgba(55,138,221,0.1) !important;
            color: #378ADD !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if st.button("⚙️", key="settings_toggle", help="おとの せってい"):
        st.session_state.show_settings = not st.session_state.show_settings


def render_settings_panel() -> None:
    """設定パネルを画面右側のサイドパネルとして表示する（position:fixed）。

    st.slider と st.button を使うことで、スライダー操作とボタン押下が即座に
    session_state に反映される。BGM 音量は再生中の <audio> へ components.html
    経由で同時反映する（st.markdown 内の <script> は Streamlit が剥がすため
    使用できない）。
    """
    _init_settings_state()
    if not st.session_state.show_settings:
        return

    # 背景の薄暗幕（視覚的にのみ。クリック判定は不要）
    st.markdown(
        '<div style="position:fixed;top:0;left:0;right:320px;bottom:0;'
        'background:rgba(0,0,0,0.2);z-index:9997;pointer-events:none;"></div>',
        unsafe_allow_html=True,
    )

    # コンテナ（key="settings_panel"）を position:fixed で右側サイドパネル化
    st.markdown(
        f"""<style>
        .st-key-settings_panel {{
            position: fixed !important;
            top: 0 !important;
            right: 0 !important;
            width: 320px !important;
            height: 100vh !important;
            background: {COLOR_WHITE} !important;
            border-left: 1px solid #E0E0E0 !important;
            box-shadow: -4px 0 16px rgba(0,0,0,0.08) !important;
            z-index: 9998 !important;
            padding: 24px 20px !important;
            overflow-y: auto !important;
            box-sizing: border-box !important;
        }}
        .st-key-settings_panel [data-testid="stCaptionContainer"] {{
            font-size: 14px !important;
            color: {COLOR_BLUE_DARK} !important;
            margin-bottom: 4px !important;
        }}
        </style>""",
        unsafe_allow_html=True,
    )

    with st.container(key="settings_panel"):
        st.markdown(
            f'<div style="font-size:18px;font-weight:500;color:{COLOR_BLUE_BASE};'
            f'margin-bottom:16px;">⚙️ おとの　せってい</div>',
            unsafe_allow_html=True,
        )

        # BGM 音量
        st.caption("🎵 BGMの　おおきさ")
        bgm_vol = st.slider(
            "BGM",
            min_value=0,
            max_value=100,
            value=st.session_state.bgm_volume,
            key="bgm_slider",
            label_visibility="collapsed",
        )
        st.session_state.bgm_volume = bgm_vol

        # 再生中の BGM <audio>（play_bgm が parent.window に張り付け）に
        # 音量を即時反映する
        components.html(
            f"""
            <script>
            (function() {{
                try {{
                    var p = window.parent;
                    if (p && p._bgmAudio) p._bgmAudio.volume = {bgm_vol / 100};
                    if (p) p._bgmVolume = {bgm_vol / 100};
                }} catch (e) {{}}
            }})();
            </script>
            """,
            height=0,
        )

        # 読み上げ音量
        st.caption("🔊 よみあげの　おおきさ")
        speech_vol = st.slider(
            "よみあげ",
            min_value=0,
            max_value=100,
            value=st.session_state.speech_volume,
            key="speech_slider",
            label_visibility="collapsed",
        )
        st.session_state.speech_volume = speech_vol

        # 次回の読み上げで参照する parent._speechVolume を更新
        components.html(
            f"""
            <script>
            (function() {{
                try {{ window.parent._speechVolume = {speech_vol / 100}; }} catch (e) {{}}
            }})();
            </script>
            """,
            height=0,
        )

        st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)

        if st.button(
            "とじる",
            key="close_settings_btn",
            use_container_width=True,
            type="primary",
        ):
            st.session_state.show_settings = False
            st.rerun()
