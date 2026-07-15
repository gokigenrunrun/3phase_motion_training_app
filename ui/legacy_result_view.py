"""研究者向けの旧アプリ（Physical-assessment-web）風の詳細結果ビュー。

ui/finished_view.py の「くわしい けっか（けんきゅうしゃ よう）」
エキスパンダー内から render_legacy_result_view() のみが呼ばれる。
ドーナツチャート・レーダーチャート・指標別フィードバックカードなど、
旧アプリのUIをできるだけ再現したもの。

注意: LEGACY_APP_ROOT は開発者のローカルマシン上の絶対パス
（CLAUDE.md の「既知の問題」に記載の通り、他環境には存在しない）。
参照先の violin_data.py が無い場合は空データにフォールバックするため、
アプリの動作自体は壊れない。
"""

import base64
import math
from html import escape
from importlib import util
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

try:
    from scipy.stats import gaussian_kde
except Exception:  # pragma: no cover - optional dependency fallback
    gaussian_kde = None


plt.rcParams["font.family"] = [
    "Hiragino Sans",
    "IPAexGothic",
    "Noto Sans CJK JP",
    "Yu Gothic",
    "sans-serif",
]

LEGACY_APP_ROOT = Path("/Users/sakaiminami/Desktop/Physical-assessment-web/Physical-assessment-web")

SCORE_COLUMNS = [
    "head_movement",
    "shoulder_tilt",
    "torso_tilt",
    "leg_lift",
    "foot_sway",
    "arm_sag",
    "banzai_score",
]

METRIC_LABELS = {
    "head_movement": "<ruby>頭部<rt>とうぶ</rt></ruby>の<ruby>安定<rt>あんてい</rt></ruby>性",
    "shoulder_tilt": "<ruby>肩<rt>かた</rt></ruby>の傾き",
    "torso_tilt": "<ruby>体幹<rt>たいかん</rt></ruby>の傾き",
    "leg_lift": "脚上げの高さ",
    "foot_sway": "軸足のブレ",
    "arm_sag": "<ruby>腕<rt>うで</rt></ruby>の保持",
    "banzai_score": "バンザイ姿勢",
    "average_score": "平均スコア",
}

# 配色は青・オレンジ系に統一（赤・ピンク・緑は使用禁止）
SCORE_COLORS = {
    "バンザイ姿勢": "#0C447C",   # 濃い青
    "頭部の安定性": "#FF8C00",   # オレンジ（旧ピンク）
    "肩の傾き": "#3B82F6",       # 中間青
    "体幹の傾き": "#0EA5E9",     # 水色寄りの青
    "腕の保持": "#F59E0B",       # 黄色寄りオレンジ
    "軸足のブレ": "#378ADD",     # ベース青（旧グリーン）
    "脚上げの高さ": "#B5D4F4",   # 薄い青（旧パープル）
}

NEUTRAL_COLOR = "#9CA3AF"
ACTION_LABELS = {
    "right_leg_1": "右脚上げ（1回目）",
    "right_leg_2": "右脚上げ（2回目）",
    "left_leg_1": "左脚上げ（1回目）",
    "left_leg_2": "左脚上げ（2回目）",
}
LEG_PHASE_ORDER = ["right_leg_1", "left_leg_1", "right_leg_2", "left_leg_2"]
LEG_PHASE_GROUPS = {
    "right_leg": ["right_leg_1", "right_leg_2"],
    "left_leg": ["left_leg_1", "left_leg_2"],
}
LEG_GROUP_LABELS = {
    "right_leg": "右脚平均",
    "left_leg": "左脚平均",
}
LEG_PHASE_SHADING = [
    ("right_leg_1", 15, 29, "skyblue"),
    ("left_leg_1", 51, 65, "lightpink"),
    ("right_leg_2", 86, 100, "skyblue"),
    ("left_leg_2", 120, 134, "lightpink"),
]
ATTEMPT_COLOR_PINK = "#FF69B4"
ATTEMPT_COLOR_BLUE = "#007BFF"
ATTEMPT_FILL_PINK = "rgba(255,105,180,0.4)"
ATTEMPT_FILL_BLUE = "rgba(0,123,255,0.6)"
AVERAGE_SCORE_COLOR = NEUTRAL_COLOR
LEG_RADAR_STYLES = {
    "right_leg": [
        ("right_leg_1", "1回目", ATTEMPT_COLOR_PINK, ATTEMPT_FILL_PINK),
        ("right_leg_2", "2回目", ATTEMPT_COLOR_BLUE, ATTEMPT_FILL_BLUE),
    ],
    "left_leg": [
        ("left_leg_1", "1回目", ATTEMPT_COLOR_PINK, ATTEMPT_FILL_PINK),
        ("left_leg_2", "2回目", ATTEMPT_COLOR_BLUE, ATTEMPT_FILL_BLUE),
    ],
}
LEG_RADAR_TITLES = {
    "right_leg": "右脚上げ（1回目・2回目）",
    "left_leg": "左脚上げ（1回目・2回目）",
}
SCORE_TIER_RULES = [
    (85, "#378ADD", "とても良い", "非常に安定した動きです。"),
    (70, "#0C447C", "良い", "動作全体を通してバランスがとれています。"),
    (55, "#FFB300", "まずまず", "全体の安定性をさらに磨きましょう。"),
    (0, "#FF8C00", "要改善", "フォーム改善の余地があります。"),
]
DEFAULT_SCORE_COLOR = "#FF8C00"
DEFAULT_SCORE_LABEL = "スコアなし"
DEFAULT_SCORE_MESSAGE = "測定に必要なデータが不足しています。"

METRIC_FEEDBACK_TEMPLATES = {
    "head_movement": {
        "high": "頭がほとんど揺れず安定しています。",
        "mid": "頭の揺れは小さいですが、引き続き安定性を意識しましょう。",
        "low": "動作中の頭の揺れを抑えることに集中しましょう。",
    },
    "shoulder_tilt": {
        "high": "肩のラインが水平に保たれています。",
        "mid": "肩の傾きは許容範囲ですが、さらに安定させましょう。",
        "low": "両肩を同じ高さに保つよう意識しましょう。",
    },
    "torso_tilt": {
        "high": "動作全体で体幹がまっすぐ保たれています。",
        "mid": "体幹は概ね安定しています。呼吸を合わせて揺れを減らしましょう。",
        "low": "上半身が揺れているので体幹を意識して引き締めましょう。",
    },
    "leg_lift": {
        "high": "脚上げの高さは十分です。",
        "mid": "もう少し高く上げるとスコアが伸びます。",
        "low": "ひざをさらに高く持ち上げて動きを強調しましょう。",
    },
    "foot_sway": {
        "high": "軸足がしっかり安定しています。",
        "mid": "軸足は概ね安定しています。体重の位置を一定に保ちましょう。",
        "low": "接地している足が揺れています。軸を安定させましょう。",
    },
    "arm_sag": {
        "high": "動作全体で腕がしっかり持ち上がっています。",
        "mid": "腕は保てていますが、肩を意識してもう少し高く上げましょう。",
        "low": "腕がすぐに下がってしまいます。ひじを持ち上げたまま意識しましょう。",
    },
    "banzai_score": {
        "high": "バンザイ姿勢が明確に保たれています。",
        "mid": "概ね良いバンザイ姿勢です。最後まで意識してキメましょう。",
        "low": "肩と腕をしっかり伸ばして姿勢を保ちましょう。",
    },
}
DEFAULT_FEEDBACK_TEMPLATE = {
    "high": "動きは安定しバランスが取れています。",
    "mid": "動作中も常に安定性を意識しましょう。",
    "low": "改善ポイントを意識してフォームを整えましょう。",
}

RESEARCH_UI_CSS = """
<style>
section[data-testid="stSidebar"] {display:none !important;}
div[data-testid="collapsedControl"] {display:none !important;}
#MainMenu {visibility:hidden;}
footer {visibility:hidden;}
header {visibility:hidden;}
body {background-color:#FFFFFF;}
.block-container {max-width:1000px;padding:2rem 1.5rem;margin:0 auto;}
.hero-score-section {
    background:#F8FAFF;
    border:1px solid #E0E7FF;
    border-radius:24px;
    padding:2.5rem 1rem;
    text-align:center;
    margin-bottom:2rem;
}
.hero-badge {
    display:inline-flex;
    align-items:center;
    justify-content:center;
    padding:0.25rem 0.75rem;
    border-radius:999px;
    background:#DBEAFE;
    color:#1E3A8A;
    font-weight:600;
    font-size:0.9rem;
    margin-bottom:0.75rem;
}
.hero-score {font-size:64px;font-weight:700;color:#2563EB;line-height:1;}
.hero-comment {font-size:18px;color:#374151;margin-top:0.5rem;}
.section-title {
    font-size:20px;
    font-weight:600;
    color:#1E3A8A;
    margin:1rem 0 0.5rem;
}
.subsection-title {
    font-size:16px;
    font-weight:600;
    color:#1E40AF;
    margin:1.5rem 0 0.5rem;
}
.radar-wrap {display:flex;justify-content:center;margin-bottom:2rem;}
.metric-grid {
    display:flex;
    flex-direction:column;
    align-items:center;
    gap:1.5rem;
    width:100%;
}
.metric-row {
    display:grid;
    grid-template-columns:repeat(2, minmax(0, 1fr));
    gap:1rem;
    width:100%;
    max-width:900px;
}
.metric-row.single {
    display:grid;
    grid-template-columns:repeat(2, minmax(0, 1fr));
    justify-content:center;
    width:100%;
    max-width:900px;
}
.metric-row.single .metric-card {
    grid-column:span 2;
    width:100%;
}
.metric-card {
    width:100%;
    background:#F9FAFB;
    border:1px solid #E5E7EB;
    border-radius:16px;
    padding:1rem 1.2rem;
}
.metric-card.long {
    height:auto;
    padding:2rem;
}
.metric-title {
    font-size:16px;
    font-weight:600;
    color:#1E3A8A;
    border-bottom:1px solid #E5E7EB;
    padding-bottom:0.3rem;
    margin-bottom:0.8rem;
}
.metric-content {
    display:flex;
    align-items:center;
}
.metric-left {
    flex:0 0 120px;
    display:flex;
    justify-content:center;
    align-items:center;
}
.metric-chart {
    width:120px;
    height:120px;
    object-fit:contain;
}
.metric-right {
    flex:1;
    padding-left:1rem;
}
.metric-score {
    font-size:22px;
    font-weight:700;
    color:#2563EB;
    margin-bottom:0.2rem;
}
.metric-comment {
    font-size:14px;
    color:#6B7280;
    line-height:1.4;
}
.metric-comment.long-comment {
    white-space:pre-line;
    line-height:1.6;
    font-size:14px;
    color:#4B5563;
    margin-top:0.5rem;
}
</style>
"""


def load_legacy_violin_data() -> Dict[str, Dict[str, Any]]:
    """旧アプリの violin_data.py（母集団分布データ）を動的 import で読み込む。

    ファイルが存在しない環境（LEGACY_APP_ROOT は開発者ローカルパス）では
    空辞書を返し、以降の分布比較系の描画はスキップされる。
    """
    violin_path = LEGACY_APP_ROOT / "violin_data.py"
    if not violin_path.exists():
        return {}
    spec = util.spec_from_file_location("legacy_violin_data", violin_path)
    if spec is None or spec.loader is None:
        return {}
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, "VIOLIN_DATA", {})


VIOLIN_DATA = load_legacy_violin_data()


def inject_research_ui_styles() -> None:
    """このビュー専用の CSS（RESEARCH_UI_CSS）を注入する。"""
    st.markdown(RESEARCH_UI_CSS, unsafe_allow_html=True)


def describe_total_score(score: float) -> Tuple[str, str, str]:
    """総合スコアを SCORE_TIER_RULES と照合し、(色, ラベル, コメント) を返す。"""
    if not np.isfinite(score):
        return DEFAULT_SCORE_COLOR, DEFAULT_SCORE_LABEL, DEFAULT_SCORE_MESSAGE
    for threshold, color, label, message in SCORE_TIER_RULES:
        if score >= threshold:
            return color, label, message
    return DEFAULT_SCORE_COLOR, DEFAULT_SCORE_LABEL, DEFAULT_SCORE_MESSAGE


def select_metric_feedback(metric_key: str, score: float) -> str:
    """指標キーとスコアから、high/mid/low いずれかの定型フィードバック文を選ぶ。"""
    template = METRIC_FEEDBACK_TEMPLATES.get(metric_key, DEFAULT_FEEDBACK_TEMPLATE)
    if not np.isfinite(score):
        return "データが不足しているため評価できません。"
    if score >= 75:
        return template.get("high") or DEFAULT_FEEDBACK_TEMPLATE["high"]
    if score >= 50:
        return template.get("mid") or template.get("high") or DEFAULT_FEEDBACK_TEMPLATE["mid"]
    return template.get("low") or template.get("mid") or DEFAULT_FEEDBACK_TEMPLATE["low"]


def render_score_block(score: float, label: str, comment_text: str) -> None:
    """画面上部の総合スコア表示ブロック（ラベルバッジ＋大きな点数＋コメント）を描画する。"""
    if np.isfinite(score):
        if score < 50:
            label_bg, label_border, label_color = "#FEE2E2", "#EF4444", "#991B1B"
        elif score < 70:
            label_bg, label_border, label_color = "#FEF3C7", "#F59E0B", "#92400E"
        elif score < 85:
            label_bg, label_border, label_color = "#DBEAFE", "#3B82F6", "#1E40AF"
        else:
            label_bg, label_border, label_color = "#DCFCE7", "#22C55E", "#14532D"
        score_text = f"{score:.1f} 点"
    else:
        label_bg, label_border, label_color = "#E5E7EB", "#9CA3AF", "#374151"
        score_text = "--"
        label = label or "スコアなし"
        comment_text = comment_text or DEFAULT_SCORE_MESSAGE

    st.markdown(
        f"""
        <div style="
            background-color:#EFF6FF;
            border-radius:16px;
            text-align:center;
            padding:1.8rem 1rem;
            margin-bottom:2rem;
        ">
            <div style="
                display:inline-block;
                background-color:{label_bg};
                border:2px solid {label_border};
                color:{label_color};
                font-weight:600;
                border-radius:999px;
                padding:6px 18px;
                font-size:16px;
            ">
                {label}
            </div>
            <div style="font-size:64px; font-weight:700; color:#2563EB; margin-top:8px; line-height:1;">
                {score_text}
            </div>
            <div style="font-size:18px; color:#1E3A8A; margin-top:6px;">
                {comment_text}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def make_donut_chart(score: float, color: str = "#3B82F6") -> go.Figure:
    """スコアを表すドーナツ型の Plotly 円グラフを作成する。"""
    safe_score = float(np.clip(score if np.isfinite(score) else 0.0, 0.0, 100.0))
    remainder = max(0.0, 100.0 - safe_score)
    fig = go.Figure(
        go.Pie(
            values=[safe_score, remainder],
            marker=dict(colors=[color, "#E5E7EB"]),
            hole=0.75,
            sort=False,
            direction="clockwise",
            textinfo="none",
        )
    )
    fig.update_layout(
        showlegend=False,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def _fallback_donut_image(score: float, color: str) -> str:
    """plotly の to_image()（kaleido）が使えない環境向けに、SVGで同等のドーナツ画像を手作りする。"""
    safe_score = float(np.clip(score if np.isfinite(score) else 0.0, 0.0, 100.0))
    radius = 46
    circumference = 2 * math.pi * radius
    dash = circumference * safe_score / 100
    svg = f"""
<svg xmlns="http://www.w3.org/2000/svg" width="240" height="240" viewBox="0 0 120 120">
  <circle cx="60" cy="60" r="{radius}" fill="none" stroke="#E5E7EB" stroke-width="14" />
  <circle cx="60" cy="60" r="{radius}" fill="none" stroke="{color}" stroke-width="14"
          stroke-dasharray="{dash:.3f} {circumference:.3f}" stroke-linecap="butt"
          transform="rotate(-90 60 60)" />
</svg>
"""
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def render_metric_card_html(title: str, score: float, comment: str) -> str:
    """1指標分のカード（ドーナツ画像＋点数＋コメント）のHTML文字列を組み立てる。

    バンザイ姿勢のカードだけは固定の補足アドバイス2行を追加し、
    長文用のレイアウト（card_modifier=" long"）を使う。
    """
    display_value = float(score) if np.isfinite(score) else np.nan
    score_for_chart = float(np.clip(display_value, 0.0, 100.0)) if np.isfinite(display_value) else 0.0
    card_color = "#3B82F6"
    fig = make_donut_chart(score_for_chart, color=card_color)
    try:
        image_bytes = fig.to_image(format="png", width=240, height=240, scale=2)
        chart_src = f"data:image/png;base64,{base64.b64encode(image_bytes).decode('ascii')}"
    except Exception:
        chart_src = _fallback_donut_image(score_for_chart, card_color)
    title_html = escape(title)
    score_text = "-- 点" if not np.isfinite(display_value) else f"{display_value:.1f} 点"
    raw_comment = (comment or "").strip()
    is_banzai = title == "バンザイ姿勢"
    if is_banzai:
        detail_lines = [raw_comment] if raw_comment else []
        detail_lines.extend(
            [
                "両腕の角度をそろえ、肩を引いて安定させましょう。",
                "頭と体幹を一直線に保ちましょう。",
            ]
        )
        comment_text = "\n".join(line for line in detail_lines if line)
        if not comment_text:
            comment_text = "バンザイ姿勢のスコアデータがありません。"
        comment_class = "metric-comment long-comment"
        card_modifier = " long"
        comment_html = escape(comment_text)
    else:
        comment_class = "metric-comment"
        card_modifier = ""
        comment_text = raw_comment or "データが不足しているため評価できません。"
        comment_html = escape(comment_text).replace("\n", "<br />")
    return (
        f'<div class="metric-card{card_modifier}">'
        f'\n    <div class="metric-title">{title_html}</div>'
        f'\n    <div class="metric-content">'
        f'\n        <div class="metric-left">'
        f'\n            <img class="metric-chart" src="{chart_src}" alt="{title_html} のスコアチャート" />'
        f"\n        </div>"
        f'\n        <div class="metric-right">'
        f'\n            <div class="metric-score">{score_text}</div>'
        f'\n            <div class="{comment_class}">{comment_html}</div>'
        f"\n        </div>"
        f"\n    </div>"
        f"\n</div>"
    )


def build_summary_display_df(result_df: pd.DataFrame) -> pd.DataFrame:
    """表示用に result_df を整形する（列名が重複した banzai_score 列を除去）。"""
    if result_df is None or result_df.empty:
        return result_df
    display_df = result_df.copy()
    duplicate_pair = {"banzai_score", "banzai_score_score"}
    if duplicate_pair.issubset(display_df.columns):
        display_df = display_df.drop(columns=["banzai_score_score"])
    return display_df


def _prepare_population(values: Any) -> np.ndarray:
    """配列から有限値だけを取り出す（分布図の母集団データ整形用）。"""
    arr = np.asarray(values, dtype=float)
    return arr[np.isfinite(arr)]


def _normalized_density(samples: np.ndarray, xs: np.ndarray) -> Optional[np.ndarray]:
    """サンプル集合からカーネル密度推定（scipy無ければヒストグラム近似）し、
    ピークが1になるよう正規化した密度配列を返す。"""
    if samples.size < 2:
        return None
    if np.allclose(samples, samples[0]):
        return None
    if gaussian_kde is not None:
        kde = gaussian_kde(samples)
        density = kde(xs)
    else:
        counts, edges = np.histogram(samples, bins=24, range=(float(xs[0]), float(xs[-1])), density=True)
        centers = (edges[:-1] + edges[1:]) / 2
        density = np.interp(xs, centers, counts, left=0.0, right=0.0)
        kernel = np.array([1, 2, 3, 2, 1], dtype=float)
        kernel /= kernel.sum()
        density = np.convolve(density, kernel, mode="same")
    max_val = float(np.max(density))
    if max_val <= 0:
        return None
    return density / max_val


RIGHT_LEG_PHASES = ["right_leg_1", "right_leg_2"]
LEFT_LEG_PHASES = ["left_leg_1", "left_leg_2"]


def compute_side_metric_series(
    frame_scores_df: Optional[pd.DataFrame],
    metric_names: Iterable[str],
) -> pd.Series:
    """フレームごとの指標 DataFrame から、左右の脚あげフェーズ別の平均値を計算する。

    Returns:
        pd.Series: キーは "{metric}_{right|left}" 形式。
    """
    if frame_scores_df is None or frame_scores_df.empty or "action" not in frame_scores_df.columns:
        return pd.Series(dtype=float)

    side_map = {
        "right": RIGHT_LEG_PHASES,
        "left": LEFT_LEG_PHASES,
    }
    data: Dict[str, float] = {}
    for metric in metric_names:
        if metric not in frame_scores_df.columns:
            continue
        for side_key, actions in side_map.items():
            subset = frame_scores_df[frame_scores_df["action"].isin(actions)]
            if subset.empty:
                value = np.nan
            else:
                metric_series = subset[metric]
                value = float(metric_series.mean(skipna=True)) if metric_series.notna().any() else np.nan
            data[f"{metric}_{side_key}"] = value
    return pd.Series(data, dtype=float)


def render_metric_feedback_cards(result_row: pd.Series, violin_data: Optional[Dict[str, Any]] = None) -> None:
    """7指標分のフィードバックカード（バンザイ姿勢＋6指標）をグリッド表示する。"""
    st.markdown(
        '<div class="section-title">🧩 '
        '<ruby>詳細<rt>しょうさい</rt></ruby>'
        '<ruby>指標<rt>しひょう</rt></ruby></div>',
        unsafe_allow_html=True,
    )
    card_order = [
        ("banzai_score", "バンザイ姿勢"),
        ("head_movement", "頭部の安定性"),
        ("shoulder_tilt", "肩の傾き"),
        ("torso_tilt", "体幹の傾き"),
        ("arm_sag", "腕の保持"),
        ("foot_sway", "軸足のブレ"),
        ("leg_lift", "脚上げの高さ"),
    ]
    if not any(f"{key}_score" in result_row.index for key, _ in card_order):
        st.info("指標スコアがまだ計算されていません。")
        return

    def card_html(metric_key: str, title: str) -> str:
        """指標キーからスコアとフィードバックを引いて1カード分のHTMLを作る内部ヘルパー。"""
        score_val = float(result_row.get(f"{metric_key}_score", np.nan))
        feedback = select_metric_feedback(metric_key, score_val)
        return render_metric_card_html(title, score_val, feedback)

    cards_html = """
<div class="metric-grid">
    <div class="metric-row single">
        {banzai}
    </div>
    <div class="metric-row">
        {head}
        {shoulder}
    </div>
    <div class="metric-row">
        {torso}
        {arm}
    </div>
    <div class="metric-row">
        {foot}
        {leg}
    </div>
</div>
""".format(
        banzai=card_html("banzai_score", "バンザイ姿勢"),
        head=card_html("head_movement", "頭部の安定性"),
        shoulder=card_html("shoulder_tilt", "肩の傾き"),
        torso=card_html("torso_tilt", "体幹の傾き"),
        arm=card_html("arm_sag", "腕の保持"),
        foot=card_html("foot_sway", "軸足のブレ"),
        leg=card_html("leg_lift", "脚上げの高さ"),
    )
    st.markdown(cards_html, unsafe_allow_html=True)


def build_frame_chart(frame_scores: pd.DataFrame) -> go.Figure:
    """フレームごとの各指標スコアを折れ線で重ね描きし、脚あげフェーズを背景色で示す図を作る。"""
    fig = go.Figure()
    if frame_scores.empty or "frame" not in frame_scores.columns:
        return fig
    x_values = frame_scores["frame"]
    for col in frame_scores.columns:
        if col in {"frame", "action", "average_score"}:
            continue
        if col == "banzai_score":
            continue
        if col.endswith("_score"):
            base = col.replace("_score", "")
            label = f"{METRIC_LABELS.get(base, base)}（スコア）"
            fig.add_trace(
                go.Scatter(
                    x=x_values,
                    y=frame_scores[col],
                    mode="lines",
                    name=label,
                    line=dict(width=2.5),
                )
            )
    fig.update_layout(
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis_title="フレーム",
        yaxis_title="スコア（0-100）",
        yaxis=dict(range=[0, 100]),
        template="plotly_white",
    )
    for _, start, end, color in LEG_PHASE_SHADING:
        fig.add_vrect(x0=start, x1=end, fillcolor=color, opacity=0.15, line_width=0, layer="below")
    return fig


def build_dummy_result_df(results: Optional[list[dict]] = None) -> pd.DataFrame:
    """このビュー用の1行サマリ DataFrame を作る（研究者ビューのフォールバック表示用）。

    results（build_real_result() 由来の実測結果）が渡されればその平均との
    差分でダミー値を底上げ/底下げする。渡されなければ固定のダミー値のみ。
    """
    score_values = {
        "head_movement_score": 82.0,
        "shoulder_tilt_score": 78.5,
        "torso_tilt_score": 80.0,
        "leg_lift_score": 76.0,
        "foot_sway_score": 84.0,
        "arm_sag_score": 79.5,
        "banzai_score_score": 88.0,
    }
    if results:
        collected_scores = [
            float(score)
            for result in results
            for score in result.get("metrics", {}).values()
            if isinstance(score, (int, float)) and np.isfinite(score)
        ]
        if collected_scores:
            adjustment = float(np.mean(collected_scores) - np.mean(list(score_values.values())))
            for key, value in score_values.items():
                score_values[key] = float(np.clip(value + adjustment, 0, 100))
    total_score = float(np.mean(list(score_values.values())))
    return pd.DataFrame([{**score_values, "total_score": total_score}])


def build_dummy_frame_scores_df() -> pd.DataFrame:
    """フレーム推移グラフ表示用に、4つの脚あげフェーズ区間分のダミーフレームデータを作る。"""
    rows = []
    actions = [
        ("right_leg_1", 15, 29),
        ("left_leg_1", 51, 65),
        ("right_leg_2", 86, 100),
        ("left_leg_2", 120, 134),
    ]
    raw_base = {
        "head_movement": 0.026,
        "shoulder_tilt": 0.066,
        "torso_tilt": 0.034,
        "leg_lift": 0.43,
        "foot_sway": 0.041,
        "arm_sag": 0.091,
        "banzai_score": 88.0,
    }
    score_base = {
        "head_movement": 82.0,
        "shoulder_tilt": 78.5,
        "torso_tilt": 80.0,
        "leg_lift": 76.0,
        "foot_sway": 84.0,
        "arm_sag": 79.5,
        "banzai_score": 88.0,
    }
    for action, start, end in actions:
        side_adjustment = 1.0 if action.startswith("right") else -1.0
        for frame in range(start, end + 1):
            wave = math.sin(frame / 4.0)
            row: Dict[str, Any] = {"frame": frame, "action": action}
            for metric, base_value in raw_base.items():
                if metric == "banzai_score":
                    row[metric] = base_value + wave * 1.5
                elif metric == "leg_lift":
                    row[metric] = max(0.0, base_value + side_adjustment * 0.015 + wave * 0.012)
                else:
                    row[metric] = max(0.0, base_value + side_adjustment * 0.002 + wave * 0.003)
            score_values = []
            for metric, base_score in score_base.items():
                score = float(np.clip(base_score + side_adjustment * 1.5 + wave * 3.0, 0, 100))
                row[f"{metric}_score"] = score
                score_values.append(score)
            row["average_score"] = float(np.mean(score_values))
            rows.append(row)
    return pd.DataFrame(rows)


def build_dummy_score_history(current_score: float) -> pd.DataFrame:
    """旧結果画面に追加する推移グラフ用のダミー履歴です。"""

    safe_current_score = float(current_score) if np.isfinite(current_score) else 78.0
    return pd.DataFrame(
        [
            {"session": "1回目", "score": 62.0, "is_current": False},
            {"session": "2回目", "score": 68.0, "is_current": False},
            {"session": "3回目", "score": 71.0, "is_current": False},
            {"session": "4回目", "score": 69.0, "is_current": False},
            {"session": "5回目", "score": 75.0, "is_current": False},
            {"session": "今回", "score": safe_current_score, "is_current": True},
        ]
    )


def render_score_history_chart(history_df: Optional[pd.DataFrame]) -> None:
    """総合スコアの履歴を折れ線グラフで表示します。"""

    if history_df is None or history_df.empty:
        return
    required_columns = {"session", "score"}
    if not required_columns.issubset(history_df.columns):
        return

    display_df = history_df.copy()
    display_df["score"] = pd.to_numeric(display_df["score"], errors="coerce")
    display_df = display_df.dropna(subset=["score"]).reset_index(drop=True)
    if display_df.empty:
        return
    if "is_current" not in display_df.columns:
        display_df["is_current"] = False

    st.markdown('<div class="section-title">📈 これまでのスコアの推移</div>', unsafe_allow_html=True)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=display_df["session"],
            y=display_df["score"],
            mode="lines+markers",
            line=dict(color="#3B82F6", width=3),
            marker=dict(size=9, color="#3B82F6"),
            name="総合スコア",
            hovertemplate="%{x}<br>総合スコア: %{y:.1f} 点<extra></extra>",
        )
    )
    current_rows = display_df[display_df["is_current"].astype(bool)]
    if not current_rows.empty:
        fig.add_trace(
            go.Scatter(
                x=current_rows["session"],
                y=current_rows["score"],
                mode="markers+text",
                marker=dict(size=15, color="#FF8C00", line=dict(color="#FFFFFF", width=2)),
                text=["今回"] * len(current_rows),
                textposition="top center",
                name="今回",
                hovertemplate="%{x}<br>総合スコア: %{y:.1f} 点<extra></extra>",
            )
        )
    fig.update_layout(
        height=320,
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis_title="測定回",
        yaxis_title="スコア",
        yaxis=dict(range=[0, 100], gridcolor="#E5E7EB"),
        xaxis=dict(gridcolor="#F3F4F6"),
        template="plotly_white",
        showlegend=False,
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def build_dummy_result_payload(results: Optional[list[dict]] = None) -> Dict[str, Any]:
    """render_legacy_result_view() が必要とする一式（result_df/frame_scores_df等）を
    ダミーデータとしてまとめて生成する。session_state に payload が無い場合のフォールバック。"""
    result_df = build_dummy_result_df(results)
    frame_scores_df = build_dummy_frame_scores_df()
    current_score = float(result_df.iloc[0].get("total_score", np.nan)) if not result_df.empty else np.nan
    return {
        "result_df": result_df,
        "frame_scores_df": frame_scores_df,
        "score_history_df": build_dummy_score_history(current_score),
        "frame_scores_csv": frame_scores_df.to_csv(index=False).encode("utf-8"),
        "pose_csv_bytes": _build_dummy_pose_csv_bytes(),
        "violin_data": VIOLIN_DATA,
    }


def _build_dummy_pose_csv_bytes() -> bytes:
    """「ポーズデータCSV出力」ボタン用のダミー CSV バイト列を作る。"""
    pose_df = pd.DataFrame(
        [
            {"frame": frame, "landmark_index": landmark, "x": 0.4 + landmark * 0.01, "y": 0.5, "z": 0.0}
            for frame in range(3)
            for landmark in range(6)
        ]
    )
    return pose_df.to_csv(index=False).encode("utf-8")


def build_real_result_payload(results: Optional[list[dict]]) -> Dict[str, Any]:
    """build_real_result() 由来の実測 results から、詳細ビュー用の payload を組み立てる。

    各指標のスコアは、種目をまたいで計算できた（NaNでない）値だけを平均した
    「セッション全体の平均スコア」として扱う（種目によって leg_lift/foot_sway
    等が NaN になる仕様は logic/calculate_metrics.py の設計どおり）。

    total_score は ui/finished_view.py の _compute_average_score() と同じ
    「全種目・全指標の有限値をまとめて平均する」計算にそろえてある。
    これはグレードバナーの点数とここでの総合点を一致させるための意図的な選択。

    banzai_score は logic/scoring.py の score_from_frame_metrics() が採点対象
    から明示的に除外しており、results の metrics dict にキー自体が存在しない。
    この payload でも同じ方針を踏襲し、banzai_score のスコアは算出しない
    （フィードバックカードは「データが不足しているため評価できません」と表示される）。

    実測データが1件も無い場合（全種目で計測失敗）は build_dummy_result_payload()
    にフォールバックする。
    """
    if not results:
        return build_dummy_result_payload(results)

    all_values: List[float] = [
        float(v)
        for result in results
        for v in result.get("metrics", {}).values()
        if isinstance(v, (int, float)) and np.isfinite(v)
    ]
    if not all_values:
        return build_dummy_result_payload(results)

    aggregated: Dict[str, float] = {}
    for metric in SCORE_COLUMNS:
        if metric == "banzai_score":
            continue
        metric_values = [
            float(result["metrics"][metric])
            for result in results
            if isinstance(result.get("metrics", {}).get(metric), (int, float))
            and np.isfinite(result["metrics"][metric])
        ]
        if metric_values:
            aggregated[f"{metric}_score"] = float(np.mean(metric_values))

    total_score = float(np.mean(all_values))
    result_df = pd.DataFrame([{**aggregated, "total_score": total_score}])

    # 過去セッションとの比較は subject_id 廃止により安全に特定できないため
    # （ui/finished_view.py _build_diff_text() 参照）、架空の推移は作らず
    # 「今回」1点のみを表示する。
    score_history_df = pd.DataFrame(
        [{"session": "今回", "score": total_score, "is_current": True}]
    )

    return {
        "result_df": result_df,
        # フレーム単位のスコア・CSVダウンロードは実測データを持たないため
        # ダミー値を出さず未提供（None）とする。ダウンロードボタンは
        # payload.get(...) is not None のガードにより自然に非表示になる。
        "frame_scores_df": None,
        "score_history_df": score_history_df,
        "frame_scores_csv": None,
        "pose_csv_bytes": None,
        "violin_data": VIOLIN_DATA,
    }


def get_legacy_result_payload(results: Optional[list[dict]] = None) -> Dict[str, Any]:
    """session_state に保存済みの payload があればそれを返す。

    無い場合（本来は ui/finished_view.py が計測完了時に
    st.session_state["legacy_result_payload"] をセットしておく）は、
    渡された results から build_real_result_payload() でその場で組み立てる
    （results も無ければ内部でダミー payload にフォールバックする）。
    """
    payload = st.session_state.get("legacy_result_payload")
    if isinstance(payload, dict) and payload.get("result_df") is not None:
        return payload
    return build_real_result_payload(results)


def render_legacy_result_view(*, results: Optional[list[dict]] = None, on_restart: Callable[[], None]) -> None:
    """研究者向け詳細結果ビューのエントリー関数。

    総合スコアブロック → スコア推移グラフ → レーダーチャート →
    指標別フィードバックカード → 詳細スコア表 → CSVダウンロードの順に描画する。
    ui/finished_view.py のエキスパンダー内から呼ばれる。

    Args:
        results:    build_real_result() 由来の各種目の結果リスト（省略可）。
        on_restart: 「もう一度測定する」ボタン押下時のコールバック。
    """
    inject_research_ui_styles()
    payload = get_legacy_result_payload(results)
    result_df = payload.get("result_df")
    frame_scores_df = payload.get("frame_scores_df")

    if result_df is None:
        st.info("スコアデータが見つかりません。再度測定してください。")
        return

    summary_table = build_summary_display_df(result_df)
    if summary_table is None or summary_table.empty:
        st.info("スコアデータが見つかりません。再度測定してください。")
        return

    summary_row = summary_table.iloc[0].copy()

    total_score = float(summary_row.get("total_score", np.nan))
    _, tier_label, tier_message = describe_total_score(total_score)
    render_score_block(total_score, tier_label, tier_message)
    score_history_df = payload.get("score_history_df")
    if score_history_df is None:
        score_history_df = build_dummy_score_history(total_score)
    render_score_history_chart(score_history_df)

    st.markdown('<div class="section-title">📊 モーションプロフィール</div>', unsafe_allow_html=True)
    english_keys = SCORE_COLUMNS
    metric_labels = [METRIC_LABELS.get(k, k) for k in english_keys]
    values = [
        float(np.nan_to_num(summary_row.get(f"{k}_score", np.nan), nan=0.0))
        for k in english_keys
    ]
    labels_closed = metric_labels + [metric_labels[0]]
    radar_values = values + values[:1]
    radar_primary_color = "#3B82F6"
    fig = go.Figure(
        data=go.Scatterpolar(
            r=radar_values,
            theta=labels_closed,
            fill="toself",
            line_color=radar_primary_color,
            fillcolor="rgba(59,130,246,0.3)",
        )
    )
    fig.update_layout(
        polar=dict(
            domain=dict(x=[0.15, 0.85], y=[0.0, 1.0]),
            radialaxis=dict(range=[0, 100], showline=False, gridcolor="rgba(0,0,0,0.1)"),
            angularaxis=dict(showline=False, gridcolor="rgba(0,0,0,0.05)"),
        ),
        showlegend=False,
        autosize=False,
        width=600,
        height=500,
        margin=dict(l=0, r=0, t=40, b=40),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
    )
    st.markdown('<div style="display:flex; justify-content:center;">', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=False, config={"displayModeBar": False, "staticPlot": True})
    st.markdown("</div>", unsafe_allow_html=True)

    render_metric_feedback_cards(summary_row)

    show_additional_charts = False
    if show_additional_charts and frame_scores_df is not None and not frame_scores_df.empty:
        st.markdown('<div class="section-title">📈 追加のチャート</div>', unsafe_allow_html=True)
        st.markdown('<div class="subsection-title">⏱ フレームごとの推移</div>', unsafe_allow_html=True)
        if "average_score" in frame_scores_df:
            avg_frame_score = float(frame_scores_df["average_score"].mean(skipna=True))
            if np.isfinite(avg_frame_score):
                st.metric("フレーム平均スコア（主要指標）", f"{avg_frame_score:.1f} 点")
        st.plotly_chart(build_frame_chart(frame_scores_df), use_container_width=True)
        with st.expander("フレームごとのスコアを表示"):
            st.dataframe(frame_scores_df)

    with st.expander("詳細スコア表を表示"):
        st.dataframe(summary_table)

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if payload.get("frame_scores_csv") is not None:
            st.download_button(
                "💾 フレームスコアをCSVで出力",
                data=payload["frame_scores_csv"],
                file_name="frame_scores.csv",
                mime="text/csv",
            )
        if payload.get("pose_csv_bytes") is not None:
            st.download_button(
                "💾 ポーズデータをCSVで出力",
                data=payload["pose_csv_bytes"],
                file_name="pose_landmarks.csv",
                mime="text/csv",
            )
    with col2:
        st.button("🔁 もう一度測定する", on_click=on_restart)
