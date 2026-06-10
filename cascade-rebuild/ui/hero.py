"""
Hero section + stats bar for the Cascade dashboard.
"""

import streamlit as st

from lineage.impact import get_deepest_lineage_path, get_most_connected_nodes
from lineage.models import LineageGraph

# ─── Dark theme CSS ───────────────────────────────────────────────────────────
DARK_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700;800&family=Inter:wght@400;500;600;700&display=swap');

.stApp {
    background: #0D1117 !important;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #161B22 !important;
    border-right: 1px solid #30363D;
}

section[data-testid="stSidebar"] .stMarkdown {
    font-family: 'Inter', sans-serif;
}

/* Push main content below Streamlit's hosted Deploy button overlay */
.stAppDeployButton { top: 56px !important; }
.block-container { padding-top: 3.5rem !important; }

section[data-testid="stSidebar"] .stMarkdown {
    font-family: 'Inter', sans-serif;
    font-weight: 500 !important;
}

/* Typography */
h1, h2, h3, h4, h5, h6 {
    font-family: 'JetBrains Mono', monospace !important;
    color: #E6EDF3 !important;
    font-weight: 700 !important;
    letter-spacing: -0.3px !important;
}

body, p, span, div, label {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

h2, h3, h4, h5, h6 {
    font-family: 'JetBrains Mono', monospace !important;
    color: #E6EDF3 !important;
    font-weight: 700 !important;
}

/* Metric cards */
.cascade-metric-card {
    background: #161B22;
    border: 1px solid #30363D;
    border-radius: 10px;
    padding: 16px 20px;
    text-align: center;
    transition: all 0.2s;
    position: relative;
    overflow: hidden;
}

.cascade-metric-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    border-radius: 10px 10px 0 0;
}

.cascade-metric-card:hover {
    border-color: #58A6FF;
    transform: translateY(-2px);
    box-shadow: 0 4px 20px rgba(88, 166, 255, 0.15);
}

.cascade-metric-card.model { --accent: #58A6FF; }
.cascade-metric-card.source { --accent: #39D353; }
.cascade-metric-card.edge { --accent: #D29922; }
.cascade-metric-card.column { --accent: #8B949E; }

.cascade-metric-card::before {
    background: var(--accent);
}

.cascade-metric-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 32px;
    font-weight: 700;
    color: #E6EDF3;
    line-height: 1;
    margin-bottom: 6px;
}

.cascade-metric-label {
    font-family: 'Inter', sans-serif;
    font-size: 12px;
    font-weight: 500;
    color: #8B949E;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.cascade-metric-sub {
    font-family: 'Inter', sans-serif;
    font-size: 11px;
    color: #58A6FF;
    margin-top: 4px;
}

/* Hero section */
.cascade-hero {
    background: linear-gradient(135deg, #0D1117 0%, #161B22 50%, #0D1117 100%);
    border: 1px solid #30363D;
    border-radius: 16px;
    padding: 60px 32px;
    margin: 20px 0 24px 0;
    position: relative;
    overflow: hidden;
    text-align: center;
}

.cascade-hero-bg {
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(circle at 30% 50%, rgba(88, 166, 255, 0.06) 0%, transparent 50%),
                radial-gradient(circle at 70% 60%, rgba(57, 211, 83, 0.04) 0%, transparent 40%);
    animation: heroPulse 8s ease-in-out infinite;
    pointer-events: none;
}

@keyframes heroPulse {
    0%, 100% { opacity: 0.6; transform: scale(1); }
    50% { opacity: 1; transform: scale(1.05); }
}

.cascade-hero-wave {
    font-size: 56px;
    margin-bottom: 20px;
    position: relative;
    z-index: 1;
}

.cascade-hero-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 30px;
    font-weight: 800;
    color: #E6EDF3;
    margin-bottom: 10px;
    position: relative;
    z-index: 1;
    letter-spacing: -0.5px;
}

.cascade-hero-sub {
    font-family: 'Inter', sans-serif;
    font-size: 15px;
    font-weight: 600;
    color: #8B949E;
    margin-bottom: 8px;
    position: relative;
    z-index: 1;
}

.cascade-hero-stats {
    display: flex;
    justify-content: center;
    gap: 16px;
    flex-wrap: wrap;
    position: relative;
    z-index: 1;
}

/* Info panel */
.cascade-info-panel {
    background: #161B22;
    border: 1px solid #30363D;
    border-radius: 10px;
    padding: 16px;
    margin-bottom: 12px;
}

.cascade-info-panel h4 {
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    color: #58A6FF;
    margin-bottom: 10px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* Risk badges */
.risk-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 4px 10px;
    border-radius: 20px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    font-weight: 600;
}

.risk-badge.low { background: #39D35320; color: #39D353; border: 1px solid #39D35340; }
.risk-badge.medium { background: #D2992220; color: #D29922; border: 1px solid #D2992240; }
.risk-badge.high { background: #F8514920; color: #F85149; border: 1px solid #F8514940; }
.risk-badge.critical { background: #F8514940; color: #FF6B6B; border: 1px solid #F85149; }

/* Resource type badge */
.type-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
}

.type-badge.model { background: #58A6FF20; color: #58A6FF; }
.type-badge.source { background: #39D35320; color: #39D353; }
.type-badge.seed { background: #8B949E20; color: #8B949E; }
.type-badge.snapshot { background: #D2992220; color: #D29922; }

/* Expander styling — Streamlit 1.58+ uses different class names. The expander
   <summary> is identified by data-testid="stExpanderToggleIcon" sibling or
   by being a direct child of <details>. We target via the <details> wrapper. */
details > summary {
    background: #161B22 !important;
    border: 1px solid #30363D !important;
    border-radius: 8px !important;
    color: #E6EDF3 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 13px !important;
    padding-left: 16px !important;
}
/* Hide the broken Material chevron icon — the icon font isn't loaded in our
   dark theme, so the span renders its text content ("keyboard_arrow_right")
   literally and overlaps with our emoji. Make the text invisible; we draw our
   own chevron via a pseudo-element on the parent summary. */
details summary span[data-testid="stIconMaterial"] {
    color: transparent !important;
    font-size: 0 !important;
    width: 18px !important;
    height: 18px !important;
    flex-shrink: 0 !important;
    text-indent: -9999px !important;
    overflow: hidden !important;
}
details > summary > span > span:first-child {
    position: relative !important;
    margin-right: 8px !important;
    flex-shrink: 0 !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
}
details > summary > span > span:first-child::before {
    content: "▶" !important;
    color: #8B949E !important;
    font-size: 12px !important;
    pointer-events: none !important;
}
details[open] > summary > span > span:first-child::before {
    content: "▼" !important;
    color: #58A6FF !important;
}

.streamlit-expanderContent {
    background: #0D1117 !important;
    border: 1px solid #30363D !important;
    border-top: none !important;
    border-radius: 0 0 8px 8px !important;
}

/* ── File uploader (dropzone + button) ──────────────────────────────────
   Same Material font issue: the upload icon span renders 'upload' as text
   on top of the 'Upload' label, producing 'uploadUpload'. Make the icon
   invisible and re-style the whole widget to fit the dark theme. */
[data-testid="stFileUploaderDropzone"] {
    background: #161B22 !important;
    border: 1.5px dashed #30363D !important;
    border-radius: 10px !important;
    padding: 28px 20px !important;
    transition: all 0.2s ease !important;
}
[data-testid="stFileUploaderDropzone"]:hover {
    border-color: #58A6FF !important;
    background: #1A2030 !important;
}
[data-testid="stFileUploaderDropzone"] section {
    padding: 0 !important;
}
[data-testid="stFileUploaderDropzone"] span[data-testid="stIconMaterial"] {
    color: transparent !important;
    font-size: 0 !important;
    width: 24px !important;
    height: 24px !important;
    display: inline-block !important;
    position: relative !important;
}
[data-testid="stFileUploaderDropzone"] span[data-testid="stIconMaterial"]::before {
    content: "⬆" !important;
    color: #58A6FF !important;
    font-size: 22px !important;
    position: absolute !important;
    top: 50% !important;
    left: 50% !important;
    transform: translate(-50%, -50%) !important;
    pointer-events: none !important;
}
/* Style the inner "Drag and drop file here" text */
[data-testid="stFileUploaderDropzone"] span,
[data-testid="stFileUploaderDropzone"] small {
    color: #8B949E !important;
    font-family: 'Inter', sans-serif !important;
}
[data-testid="stFileUploaderDropzone"] small {
    color: #6E7681 !important;
    font-size: 11px !important;
}
/* Style the "Browse files" button */
[data-testid="stFileUploaderDropzone"] button {
    background: #58A6FF !important;
    color: #0D1117 !important;
    border: none !important;
    border-radius: 6px !important;
    padding: 8px 16px !important;
    font-weight: 600 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
    transition: all 0.15s ease !important;
}
[data-testid="stFileUploaderDropzone"] button:hover {
    background: #79B8FF !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px #58A6FF40 !important;
}
/* "Choose File" button shown in collapsed state */
[data-testid="stFileUploaderDropzone"] button[data-testid="baseButton-secondary"] {
    background: transparent !important;
    color: #58A6FF !important;
    border: 1px solid #58A6FF !important;
}
[data-testid="stFileUploaderDropzone"] button[data-testid="baseButton-secondary"]:hover {
    background: #58A6FF20 !important;
    color: #79B8FF !important;
}
/* Hide the icon font text in the secondary "Choose File" button */
[data-testid="stFileUploaderDropzone"] button span[data-testid="stIconMaterial"] {
    color: transparent !important;
    font-size: 0 !important;
}

/* ── Get-Started section cards (Upload / Demo) ───────────────────────────
   Replaces plain markdown headers with a proper card header. */
.cascade-section-card {
    background: #161B22;
    border: 1px solid #30363D;
    border-radius: 10px;
    padding: 16px 18px;
    margin-bottom: 14px;
    display: flex;
    flex-direction: column;
    gap: 4px;
}
.cascade-section-icon {
    font-size: 22px;
    line-height: 1;
    margin-bottom: 2px;
}
.cascade-section-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 15px;
    font-weight: 700;
    color: #E6EDF3;
}
.cascade-section-desc {
    font-family: 'Inter', sans-serif;
    font-size: 12px;
    color: #8B949E;
    line-height: 1.5;
}
.cascade-section-desc code {
    background: #0D1117;
    color: #79B8FF;
    padding: 1px 6px;
    border-radius: 3px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    border: 1px solid #30363D;
}

/* Dataframe styling */
.streamlit-dataframe {
    background: #161B22 !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0D1117; }
::-webkit-scrollbar-thumb { background: #30363D; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #58A6FF; }

/* Button styling */
.stButton > button {
    background: #58A6FF !important;
    color: #0D1117 !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    transition: all 0.2s !important;
}

.stButton > button:hover {
    background: #79B8FF !important;
    transform: translateY(-1px);
}

/* Secondary button */
.stButton.secondary > button {
    background: #21262D !important;
    color: #E6EDF3 !important;
    border: 1px solid #30363D !important;
}

/* Code / mono text */
.mono {
    font-family: 'JetBrains Mono', monospace !important;
}

/* Section dividers */
.cascade-divider {
    border: none;
    border-top: 1px solid #30363D;
    margin: 16px 0;
}

/* Tables */
table {
    width: 100%;
    border-collapse: collapse;
    font-family: 'Inter', sans-serif;
    font-size: 12px;
}

th {
    background: #21262D;
    color: #8B949E;
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 8px 12px;
    text-align: left;
    border-bottom: 1px solid #30363D;
}

td {
    padding: 8px 12px;
    color: #E6EDF3;
    border-bottom: 1px solid #21262D;
}

tr:hover td {
    background: #21262D;
}

/* Search input */
.stTextInput > div > div > input {
    background: #0D1117 !important;
    border: 1px solid #30363D !important;
    color: #E6EDF3 !important;
    border-radius: 8px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important;
}

.stTextInput > div > div > input:focus {
    border-color: #58A6FF !important;
    box-shadow: 0 0 0 2px rgba(88, 166, 255, 0.2) !important;
}

/* Body text + p / span / div default: Inter 600 for legibility */
.stApp, .stApp p, .stApp span, .stApp div, .stApp label, .stMarkdown p, .stMarkdown span {
    font-family: 'Inter', sans-serif;
    font-weight: 600;
}

/* Streamlit "Deploy" / "Get started" / toolbar overlay (top right) is
   injected by hosted Streamlit apps. Push the main content below it so the
   hero title isn't hidden behind the overlay. We add a small top margin to
   the main block container. The hosted toolbar lives inside
   `section[data-testid="stToolbar"]` plus a top-right floating button
   (`button[aria-label="Deploy"]` or class `stAppDeployButton`). */
.stAppDeployButton {
    top: 72px !important;
    right: 16px !important;
    z-index: 999 !important;
}

section[data-testid="stToolbar"] {
    height: 48px !important;
}

.main .block-container,
section.main > div.block-container,
.stApp > header + div .block-container {
    padding-top: 3.5rem !important;
    margin-top: 0 !important;
}

/* Hide the floating hosted "Get started" star/feedback buttons (best-effort) */
#manage-app-button-portal,
#feynman-toolbar-portal {
    top: 72px !important;
}

/* Make sure the title isn't clipped by the toolbar */
h1:first-of-type {
    margin-top: 0.5rem !important;
}
</style>
"""


def inject_dark_theme():
    """Inject the dark theme CSS into the Streamlit page."""
    st.markdown(DARK_CSS, unsafe_allow_html=True)


def render_hero(project_name: str = "", stats: dict = None):
    """Render the hero section with animated background."""
    if stats is None:
        stats = {"models": 0, "sources": 0, "edges": 0, "columns": 0}

    col1, col2, col3, col4 = st.columns(4)

    cards = [
        (col1, stats.get("models", 0), "Models", "model"),
        (col2, stats.get("sources", 0), "Sources", "source"),
        (col3, stats.get("edges", 0), "Edges", "edge"),
        (col4, stats.get("columns", 0), "Columns", "column"),
    ]

    for col, value, label, type_ in cards:
        with col:
            st.markdown(
                f"""
                <div class="cascade-metric-card {type_}">
                    <div class="cascade-metric-value">{value:,}</div>
                    <div class="cascade-metric-label">{label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_summary_stats(graph: LineageGraph):
    """Render interesting summary stats below the hero."""
    most_connected = get_most_connected_nodes(graph, top_n=5)
    deepest_path = get_deepest_lineage_path(graph)

    st.markdown("### Summary Stats")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("**Most Connected**")
        if most_connected:
            for uid, degree in most_connected[:5]:
                node = graph.get_node(uid)
                if node:
                    short_name = node.name
                    st.markdown(
                        f"<span class='mono' style='font-size:12px; color:#E6EDF3;'>{short_name}</span> "
                        f"<span style='color:#8B949E; font-size:11px;'>({degree} connections)</span>",
                        unsafe_allow_html=True,
                    )
        else:
            st.caption("No data")

    with c2:
        st.markdown("**Deepest Lineage**")
        if deepest_path:
            path_len = len(deepest_path)
            st.metric("Path Length", path_len)
            # Show as breadcrumb
            if path_len > 0:
                path_names = [graph.get_node(u).name if graph.get_node(u) else u.split(".")[-1] for u in deepest_path[:5]]
                st.caption(" → ".join(path_names))
                if path_len > 5:
                    st.caption(f"... and {path_len - 5} more")
        else:
            st.caption("No lineage paths found")

    with c3:
        st.markdown("**Resource Types**")
        counts = {"models": 0, "sources": 0, "seeds": 0, "snapshots": 0}
        for uid in graph.nodes:
            node = graph.get_node(uid)
            if node:
                rt = node.resource_type
                if rt in counts:
                    counts[rt] += 1

        for rt, count in counts.items():
            if count > 0:
                color = {"models": "#58A6FF", "sources": "#39D353", "seeds": "#8B949E", "snapshots": "#D29922"}[rt]
                st.markdown(
                    f"<span style='color:{color}; font-family:JetBrains Mono,monospace; font-size:12px;'>{count:3d}</span> "
                    f"<span style='color:#8B949E; font-size:12px;'>{rt.capitalize()}</span>",
                    unsafe_allow_html=True,
                )
