"""アプリ全体の共通CSSとHTMLコンポーネントを管理するモジュール。

CSS の注入は app.py の main() で一度だけ行うこと。
各 view ファイルや fragment 内で get_common_css() を呼ばないこと。
動的コンテンツ（吹き出し・キャラクター）は st.info()/st.image() を使い
unsafe_allow_html=True を極力使わない。
"""

import base64
import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

# -------------------------------------------------------
# カラー定数
# -------------------------------------------------------

COLOR_BLUE_BASE = "#378ADD"     # ベース青（ヘッダー・ボーダー）
COLOR_BLUE_LIGHT = "#FFFFFF"    # 背景色（白）
COLOR_BLUE_DARK = "#0C447C"     # 濃い青（テキスト）
COLOR_BLUE_MID = "#85B7EB"      # 中間青（サブボーダー）
COLOR_ORANGE = "#FF8C00"        # オレンジ（ボタン・アクセント）
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

/* ボタン */
div[data-testid="stButton"] button {{
    font-size: 22px !important;
    height: 64px !important;
    border-radius: 12px !important;
    width: 100% !important;
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
        f'<div style="background:{COLOR_BLUE_BASE};border-radius:0 0 12px 12px;'
        f'padding:12px 20px;display:flex;align-items:center;gap:12px;'
        f'min-height:88px;box-sizing:border-box;'
        f'margin-left:-1rem;margin-right:-1rem;margin-top:-1rem;margin-bottom:16px;">'
        f'{icon_block}'
        f'<div style="color:{COLOR_WHITE};font-size:20px;font-weight:700;line-height:1.3;">'
        f'{title_html}</div>'
        f'</div>'
    )


def render_header_with_timer(
    icon: str,
    title_html: str,
    remaining: int,
    duration: float,
) -> str:
    """ヘッダー右端に円形タイマーを埋め込んだHTMLを返す（measure_view 専用）。

    fragment 内で 0.8 秒ごとに再描画する想定。中身は静的HTMLのみで
    iframe/script を含まないため、頻繁な再描画でも removeChild エラーが起きない。

    Args:
        icon:       絵文字アイコン（例: "🏃"）
        title_html: タイトルのHTML文字列（ruby タグなど可）
        remaining:  残り秒数（整数）
        duration:   フェーズ全体の秒数
    """
    percent = max(0.0, min(1.0, remaining / duration)) if duration > 0 else 0.0
    deg = int(360 * percent)
    icon_block = (
        f'<div style="width:48px;height:48px;border-radius:50%;'
        f'background:{COLOR_WHITE};display:flex;align-items:center;'
        f'justify-content:center;font-size:24px;flex-shrink:0;">{icon}</div>'
        if icon else ""
    )

    return (
        # 行頭空白なしで連結（Markdown コードブロック化を回避）
        f'<div style="background:{COLOR_BLUE_BASE};padding:12px 20px;'
        f'display:flex;align-items:center;justify-content:space-between;'
        f'margin-left:-1rem;margin-right:-1rem;margin-top:-1rem;margin-bottom:16px;'
        f'border-radius:0 0 12px 12px;">'
        # 左: アイコン + タイトル
        f'<div style="display:flex;align-items:center;gap:12px;">'
        f'{icon_block}'
        f'<div style="color:{COLOR_WHITE};font-size:20px;font-weight:700;'
        f'line-height:1.3;">{title_html}</div>'
        f'</div>'
        # 右: 円形タイマー（conic-gradient で残り割合をオレンジ円弧で表示）
        f'<div style="width:64px;height:64px;border-radius:50%;flex-shrink:0;'
        f'background:conic-gradient({COLOR_ORANGE} {deg}deg,'
        f'rgba(255,255,255,0.3) {deg}deg);'
        f'display:flex;align-items:center;justify-content:center;">'
        f'<div style="width:52px;height:52px;border-radius:50%;'
        f'background:{COLOR_BLUE_BASE};display:flex;flex-direction:column;'
        f'align-items:center;justify-content:center;">'
        f'<span style="color:{COLOR_WHITE};font-size:20px;font-weight:700;'
        f'line-height:1;">{remaining}</span>'
        f'<span style="color:rgba(255,255,255,0.85);font-size:10px;'
        f'margin-top:2px;">びょう</span>'
        f'</div>'
        f'</div>'
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

def speak(text: str, rate: float = 0.85, pitch: float = 1.1) -> None:
    """Web Speech API で日本語テキストを読み上げる。

    音量は親ウィンドウの window._speechVolume（設定パネルが書き込み）から取得。
    未設定の場合は 0.8 を使用する。

    Args:
        text:  読み上げるテキスト
        rate:  読み上げ速度（1.0 が標準、0.85 でゆっくり）
        pitch: 声の高さ（1.1 で少し高め・明るい印象）
    """
    safe_text = json.dumps(text, ensure_ascii=False)
    components.html(
        f"""
        <script>
        (function() {{
            // 親ウィンドウの speechSynthesis を優先（iframe 破棄に強い）
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
            // 設定パネルからの音量を反映（未設定時は 0.8）
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
    """画面右上に⚙️設定ボタンを固定表示する。

    Streamlit 1.43+ で `key` 引数指定の widget には `.st-key-<key>` クラスが
    自動付与されるため、このクラスにのみ position:fixed を適用することで
    他のボタン（とじる等）に影響を与えない。
    """
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
    """設定パネルを表示する（show_settings=True のときだけ）。

    BGM 音量と読み上げ音量のスライダーを表示し、変更を即座に
    親ウィンドウの _bgmAudio.volume / _speechVolume に反映する。
    """
    _init_settings_state()
    if not st.session_state.show_settings:
        return

    with st.container(border=True):
        st.markdown(
            "<p style='font-size:18px;color:#378ADD;font-weight:500;margin-bottom:12px;'>"
            "⚙️ おとの　せってい</p>",
            unsafe_allow_html=True,
        )

        st.caption("🎵 BGMの　おとの　おおきさ")
        bgm_vol = st.slider(
            label="BGM",
            min_value=0,
            max_value=100,
            value=st.session_state.bgm_volume,
            key="bgm_slider",
            label_visibility="collapsed",
        )
        st.session_state.bgm_volume = bgm_vol

        st.caption("🔊 よみあげの　おとの　おおきさ")
        speech_vol = st.slider(
            label="speech",
            min_value=0,
            max_value=100,
            value=st.session_state.speech_volume,
            key="speech_slider",
            label_visibility="collapsed",
        )
        st.session_state.speech_volume = speech_vol

        if st.button("とじる", key="close_settings", use_container_width=True):
            st.session_state.show_settings = False
            st.rerun()

    # 音量変更を即時反映する JS（components.html で確実にスクリプト実行）
    components.html(
        f"""
        <script>
        (function() {{
            try {{
                var parent = window.parent;
                if (parent._bgmAudio) {{
                    parent._bgmAudio.volume = {bgm_vol / 100};
                }}
                parent._speechVolume = {speech_vol / 100};
            }} catch (e) {{ console.error('settings apply error:', e); }}
        }})();
        </script>
        """,
        height=0,
    )
