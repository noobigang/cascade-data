"""
Cascade — Data Lineage & Impact Analysis
Streamlit application entrypoint — dark-themed with glow effects.
"""

import sys
from pathlib import Path

# Add repo root so 'cascade' subdirectory is importable on Streamlit Cloud
FILE = Path(__file__).resolve()
REPO_ROOT = FILE.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import networkx as nx
import streamlit as st

from cascade.ui.dag_viewer import render_dag
from cascade.ui.detail_panel import render_detail_panel
from cascade.ui.search_panel import render_blast_radius, render_search_panel
from cascade.ui.share_card import render_share_card
from cascade.ui.upload_zone import UploadZone
from cascade.utils.state_encoder import extract_state_from_url

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Cascade — Data Lineage",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={},
)

# ---------------------------------------------------------------------------
# Extended dark theme CSS — JetBrains Mono, glow effects, animations
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Inter:wght@300;400;500;600&display=swap');

    :root {
        --bg: #0D1117;
        --surface: #161B22;
        --surface-2: #21262D;
        --border: #30363D;
        --primary: #58A6FF;
        --accent: #39D353;
        --warning: #D29922;
        --danger: #F85149;
        --text: #E6EDF3;
        --text-muted: #8B949E;
        --glow-primary: rgba(88, 166, 255, 0.4);
        --glow-accent: rgba(57, 211, 83, 0.3);
    }

    /* Base */
    .stApp { background-color: var(--bg); color: var(--text); }
    .main { background-color: var(--bg); }

    /* Sidebar */
    [data-testid="stSidebar] { background-color: var(--surface); border-right: 1px solid var(--border); }
    [data-testid="stSidebar"] { background-color: var(--surface) !important; border-right: 1px solid var(--border); }

    /* Expanders / collapsibles */
    [data-testid="stExpander"] {
        background-color: var(--surface);
        border: 1px solid var(--border);
        border-radius: 8px;
    }
    [data-testid="stExpander"] summary {
        border-radius: 8px;
    }

    /* Headings — JetBrains Mono */
    h1, h2, h3, h4 {
        font-family: 'JetBrains Mono', monospace !important;
        color: var(--text) !important;
        letter-spacing: -0.02em;
    }

    /* Body text */
    p, span, div, label { font-family: 'Inter', sans-serif !important; }

    /* Code */
    code, pre, [data-testid="stCodeBlock"] {
        font-family: 'JetBrains Mono', monospace !important;
        background-color: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: 6px !important;
        color: var(--primary) !important;
    }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #58A6FF 0%, #388BFD 100%) !important;
        color: #0D1117 !important;
        border: none !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        transition: all 150ms ease-out !important;
        box-shadow: 0 0 0 0 var(--glow-primary) !important;
    }
    .stButton > button:hover {
        opacity: 0.9 !important;
        box-shadow: 0 0 16px var(--glow-primary) !important;
        transform: translateY(-1px);
    }
    .stButton > button:active { transform: translateY(0) !important; }

    /* Secondary buttons */
    .stButton[data-baseweb="button"][kind="secondary"] > button,
    button[data-testid="stBaseButton-secondary"] {
        background-color: var(--surface) !important;
        border: 1px solid var(--border) !important;
        color: var(--primary) !important;
    }

    /* Metric values */
    [data-testid="stMetricValue"] {
        font-family: 'JetBrains Mono', monospace !important;
        color: var(--primary) !important;
        font-size: 28px !important;
        font-weight: 600 !important;
    }
    [data-testid="stMetricLabel"] {
        font-family: 'Inter', sans-serif !important;
        color: var(--text-muted) !important;
    }

    /* Metric container cards with glow */
    [data-testid="stHorizontalBlock"] [data-testid="stMetric"] {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 16px;
        transition: all 200ms ease-out;
    }
    [data-testid="stHorizontalBlock"] [data-testid="stMetric"]:hover {
        border-color: var(--primary);
        box-shadow: 0 0 20px var(--glow-primary);
    }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: var(--bg); }
    ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }

    /* Upload zone */
    [data-testid="stFileUploaderDropzone"] {
        background-color: var(--surface) !important;
        border: 2px dashed var(--border) !important;
        border-radius: 12px !important;
        transition: all 200ms ease-out !important;
    }
    [data-testid="stFileUploaderDropzone]:hover {
        border-color: var(--primary) !important;
        box-shadow: 0 0 16px var(--glow-primary) !important;
    }

    /* Text inputs */
    .stTextInput > div > div > input,
    .stTextInput input {
        background-color: var(--surface) !important;
        border: 1px solid var(--border) !important;
        color: var(--text) !important;
        border-radius: 8px !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 13px !important;
        transition: border-color 150ms ease-out, box-shadow 150ms ease-out !important;
    }
    .stTextInput input:focus {
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 3px var(--glow-primary) !important;
    }

    /* Checkboxes */
    .stCheckbox label, .stCheckbox span {
        font-family: 'Inter', sans-serif !important;
        color: var(--text-muted) !important;
    }

    /* Tabs */
    .stTabs [data-testid="stTab"] {
        font-family: 'JetBrains Mono', monospace !important;
        color: var(--text-muted) !important;
    }
    .stTabs [data-testid="stTab"][aria-selected="true"] {
        color: var(--primary) !important;
        border-bottom: 2px solid var(--primary) !important;
    }

    /* Divider */
    hr { border-color: var(--border) !important; }

    /* DataFrames */
    .stDataFrame { font-family: 'Inter', sans-serif !important; }
    [data-testid="stDataFrame"] thead th {
        background-color: var(--surface-2) !important;
        color: var(--primary) !important;
        font-family: 'JetBrains Mono', monospace !important;
        border-bottom: 2px solid var(--border) !important;
    }
    [data-testid="stDataFrame"] tbody tr:hover {
        background-color: var(--surface) !important;
    }

    /* Alert boxes */
    .stAlert { border-radius: 8px !important; border-left: 4px solid !important; }
    .stAlert[data-baseweb="notification"] { border-radius: 8px !important; }

    /* Footer */
    .cascade-footer {
        position: fixed; bottom: 0; left: 0; right: 0;
        padding: 12px 24px;
        background-color: var(--surface);
        border-top: 1px solid var(--border);
        text-align: center;
        font-family: 'Inter', sans-serif;
        font-size: 13px;
        color: var(--text-muted);
        z-index: 100;
    }

    /* ── Hero section ─────────────────────────────────────────────────── */
    .hero-container {
        background: linear-gradient(135deg, #0D1117 0%, #161B22 50%, #0D1117 100%);
        border: 1px solid #30363D;
        border-radius: 16px;
        padding: 40px 48px;
        margin: 16px 0 32px 0;
        text-align: center;
        position: relative;
        overflow: hidden;
    }
    .hero-container::before {
        content: '';
        position: absolute;
        top: -50%; left: -50%;
        width: 200%; height: 200%;
        background: radial-gradient(ellipse at center, rgba(88,166,255,0.06) 0%, transparent 60%);
        animation: hero-glow 6s ease-in-out infinite;
    }
    @keyframes hero-glow {
        0%, 100% { opacity: 0.5; transform: scale(1); }
        50% { opacity: 1; transform: scale(1.05); }
    }
    .hero-title {
        font-family: 'JetBrains Mono', monospace;
        font-size: 42px;
        font-weight: 700;
        color: #E6EDF3;
        margin: 0 0 8px 0;
        position: relative;
        letter-spacing: -0.03em;
    }
    .hero-title .accent { color: #58A6FF; }
    .hero-subtitle {
        font-family: 'Inter', sans-serif;
        font-size: 18px;
        color: #8B949E;
        margin: 0 0 28px 0;
        position: relative;
        animation: fadeSlideUp 600ms ease-out;
    }
    @keyframes fadeSlideUp {
        from { opacity: 0; transform: translateY(12px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .hero-cta {
        display: inline-block;
        background: linear-gradient(135deg, #58A6FF 0%, #388BFD 100%);
        color: #0D1117;
        font-family: 'JetBrains Mono', monospace;
        font-weight: 600;
        font-size: 14px;
        padding: 10px 28px;
        border-radius: 8px;
        text-decoration: none;
        position: relative;
        transition: all 150ms ease-out;
        box-shadow: 0 0 20px rgba(88,166,255,0.3);
        animation: hero-btn-glow 3s ease-in-out infinite;
    }
    @keyframes hero-btn-glow {
        0%, 100% { box-shadow: 0 0 20px rgba(88,166,255,0.3); }
        50% { box-shadow: 0 0 32px rgba(88,166,255,0.6); }
    }
    .hero-cta:hover {
        transform: translateY(-2px);
        box-shadow: 0 0 40px rgba(88,166,255,0.5);
    }

    /* ── How it works cards ──────────────────────────────────────────── */
    .hiw-section {
        margin: 24px 0 36px 0;
    }
    .hiw-section h3 {
        font-family: 'JetBrains Mono', monospace;
        font-size: 20px;
        color: #E6EDF3;
        margin-bottom: 20px;
        text-align: center;
    }
    .hiw-cards {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 16px;
    }
    .hiw-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 24px 20px;
        text-align: center;
        transition: all 200ms ease-out;
        position: relative;
        overflow: hidden;
    }
    .hiw-card::after {
        content: '';
        position: absolute;
        inset: 0;
        background: radial-gradient(ellipse at top, rgba(88,166,255,0.04) 0%, transparent 70%);
    }
    .hiw-card:hover {
        border-color: var(--primary);
        box-shadow: 0 0 24px var(--glow-primary);
        transform: translateY(-2px);
    }
    .hiw-step {
        display: inline-block;
        width: 36px; height: 36px;
        background: linear-gradient(135deg, #58A6FF, #388BFD);
        border-radius: 50%;
        line-height: 36px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 14px;
        font-weight: 700;
        color: #0D1117;
        margin-bottom: 12px;
    }
    .hiw-icon { font-size: 32px; margin-bottom: 8px; }
    .hiw-title {
        font-family: 'JetBrains Mono', monospace;
        font-size: 15px;
        font-weight: 600;
        color: #E6EDF3;
        margin-bottom: 8px;
    }
    .hiw-desc {
        font-family: 'Inter', sans-serif;
        font-size: 13px;
        color: #8B949E;
        line-height: 1.5;
    }

    /* ── Sidebar polish ──────────────────────────────────────────────── */
    .sidebar-section {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 12px 16px;
        margin-bottom: 12px;
    }
    .sidebar-section-header {
        font-family: 'JetBrains Mono', monospace;
        font-size: 13px;
        font-weight: 600;
        color: #E6EDF3;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .sidebar-stat-card {
        background: var(--surface-2);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 12px;
        text-align: center;
        margin-bottom: 8px;
        transition: all 200ms ease-out;
        animation: statPulse 2s ease-in-out infinite;
    }
    .sidebar-stat-card:hover {
        border-color: var(--primary);
        box-shadow: 0 0 12px var(--glow-primary);
    }
    @keyframes statPulse {
        0%, 100% { box-shadow: 0 0 0 0 transparent; }
        50% { box-shadow: 0 0 8px rgba(88,166,255,0.15); }
    }
    .sidebar-stat-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 24px;
        font-weight: 700;
        color: var(--primary);
    }
    .sidebar-stat-label {
        font-family: 'Inter', sans-serif;
        font-size: 11px;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* ── Loading skeleton ────────────────────────────────────────────── */
    .skeleton {
        background: linear-gradient(
            90deg,
            var(--surface) 25%,
            var(--surface-2) 50%,
            var(--surface) 75%
        );
        background-size: 200% 100%;
        animation: shimmer 1.5s infinite;
        border-radius: 6px;
    }
    @keyframes shimmer {
        0% { background-position: 200% 0; }
        100% { background-position: -200% 0; }
    }
    .skeleton-dag {
        height: 500px;
        background: var(--surface);
        border: 1px dashed var(--border);
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-direction: column;
        gap: 12px;
    }
    .skeleton-bars {
        display: flex;
        align-items: end;
        gap: 4px;
        height: 60px;
    }
    .skeleton-bar {
        width: 12px;
        background: linear-gradient(
            90deg,
            var(--surface-2) 25%,
            var(--border) 50%,
            var(--surface-2) 75%
        );
        background-size: 200% 100%;
        animation: shimmer 1.5s infinite;
        border-radius: 3px;
    }

    /* Responsive */
    @media (max-width: 768px) {
        .hiw-cards { grid-template-columns: 1fr; }
        .hero-container { padding: 24px 20px; }
        .hero-title { font-size: 28px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
def init_state():
    if "dag" not in st.session_state:
        st.session_state.dag = None
    if "manifest" not in st.session_state:
        st.session_state.manifest = None
    if "selected_node" not in st.session_state:
        st.session_state.selected_node = None
    if "loading" not in st.session_state:
        st.session_state.loading = False
    if "physics_enabled" not in st.session_state:
        st.session_state.physics_enabled = True
    if "filters" not in st.session_state:
        st.session_state.filters = {"model": True, "source": True, "seed": True}


init_state()


# ---------------------------------------------------------------------------
# Restore state from URL on first load
# ---------------------------------------------------------------------------
def _restore_from_url():
    """Decode state from URL params and restore session."""
    try:
        query_params = st.experimental_get_query_params()
        state = extract_state_from_url(query_params)
        if state:
            st.session_state.selected_node = state.get("selected_node")
            st.session_state.physics_enabled = state.get("physics_enabled", True)
            st.session_state.filters = state.get("filters", {"model": True, "source": True, "seed": True})
    except Exception:
        pass  # Silently fail on URL decode errors


_restore_from_url()


# ---------------------------------------------------------------------------
# Hero section
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="hero-container">
        <div class="hero-title">
            See the <span class="accent">full impact</span><br>of every data change
        </div>
        <div class="hero-subtitle">
            Column-level lineage for dbt projects — know what breaks before you deploy
        </div>
        <a class="hero-cta" href="#upload" onclick="document.querySelector('[data-testid=&quot;stFileUploaderDropzone&quot;]').click(); return false;">
            ↑ Upload manifest.json
        </a>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# How it works — 3-step section
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="hiw-section">
        <h3>How it works</h3>
        <div class="hiw-cards">
            <div class="hiw-card">
                <div class="hiw-step">1</div>
                <div class="hiw-icon">📦</div>
                <div class="hiw-title">Upload manifest.json</div>
                <div class="hiw-desc">Drop your dbt <code>target/manifest.json</code> — parsed in seconds, even for 10k+ node projects.</div>
            </div>
            <div class="hiw-card">
                <div class="hiw-step">2</div>
                <div class="hiw-icon">🔗</div>
                <div class="hiw-title">Explore lineage</div>
                <div class="hiw-desc">Navigate your full DAG interactively. Click any node to see column-level upstream and downstream dependencies.</div>
            </div>
            <div class="hiw-card">
                <div class="hiw-step">3</div>
                <div class="hiw-icon">📤</div>
                <div class="hiw-title">Share findings</div>
                <div class="hiw-desc">Generate a shareable link or export the graph as PNG — share the exact view with your team.</div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Sidebar state helper
# ---------------------------------------------------------------------------

has_dag = st.session_state.dag is not None and len(st.session_state.dag.nodes) > 0


# ---------------------------------------------------------------------------
# Helper components (defined before use)
# ---------------------------------------------------------------------------

def _render_animated_stats(dag) -> None:
    """Render animated stat cards in the sidebar."""
    if dag is None or len(dag.nodes) == 0:
        st.caption("No data loaded.")
        return
    nodes = list(dag.nodes)
    edges = list(dag.edges)
    resource_counts: dict[str, int] = {}
    for node in nodes:
        rtype = dag.nodes[node].get("resource_type", "unknown")
        resource_counts[rtype] = resource_counts.get(rtype, 0) + 1
    stats = [
        ("Models", resource_counts.get("model", 0), "#58A6FF"),
        ("Sources", resource_counts.get("source", 0), "#39D353"),
        ("Seeds", resource_counts.get("seed", 0), "#D29922"),
        ("Edges", len(edges), "#8B949E"),
    ]
    for label, value, color in stats:
        st.markdown(
            f"""<div class="sidebar-stat-card">
            <div class="sidebar-stat-value" style="color: {color};">{value:,}</div>
            <div class="sidebar-stat-label">{label}</div>
            </div>""",
            unsafe_allow_html=True,
        )
    st.markdown("**By type**")
    type_colors = {"model": "#58A6FF", "source": "#39D353", "seed": "#8B949E", "snapshot": "#D29922"}
    for rtype, count in sorted(resource_counts.items()):
        c = type_colors.get(rtype, "#8B949E")
        st.markdown(
            f'<span style="color: {c};">●</span> {rtype}: '
            f'<code style="color: {c};">{count}</code>',
            unsafe_allow_html=True,
        )


def _render_skeleton_loader() -> None:
    """Render an animated skeleton loader while waiting for DAG data."""
    st.markdown(
        """<div class="skeleton-dag">
        <div style="font-size: 36px; animation: float 2s ease-in-out infinite;">🌊</div>
        <div style="font-family: 'JetBrains Mono', monospace; color: #58A6FF; font-size: 14px;">
            Loading lineage graph…
        </div>
        <div class="skeleton-bars">
            <div class="skeleton-bar" style="height: 20px; animation-delay: 0.0s;"></div>
            <div class="skeleton-bar" style="height: 35px; animation-delay: 0.1s;"></div>
            <div class="skeleton-bar" style="height: 50px; animation-delay: 0.2s;"></div>
            <div class="skeleton-bar" style="height: 40px; animation-delay: 0.3s;"></div>
            <div class="skeleton-bar" style="height: 55px; animation-delay: 0.4s;"></div>
            <div class="skeleton-bar" style="height: 30px; animation-delay: 0.5s;"></div>
            <div class="skeleton-bar" style="height: 45px; animation-delay: 0.6s;"></div>
            <div class="skeleton-bar" style="height: 25px; animation-delay: 0.7s;"></div>
        </div>
        <div style="font-family: 'Inter', sans-serif; color: #8B949E; font-size: 13px;">
            Upload a manifest.json to get started
        </div>
        </div>
        <style>
        @keyframes float { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-8px); } }
        </style>""",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Sidebar — layout
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        '<div class="sidebar-section-header">🌊 Cascade</div>',
        unsafe_allow_html=True,
    )
    st.divider()

    # ── Try Demo ─────────────────────────────────────────────────────────
    DEMO_MANIFEST_PATH = REPO_ROOT / "demo" / "manifest.json"
    if DEMO_MANIFEST_PATH.exists():
        if st.button("🎲 Try Demo", use_container_width=True, type="primary"):
            import json
            with open(DEMO_MANIFEST_PATH, encoding="utf-8") as f:
                demo_data = json.load(f)
            st.session_state.manifest = demo_data
            st.session_state.loading = True
            st.rerun()

    # ── Upload section (collapsible) ─────────────────────────────────────
    with st.expander("📦 Upload manifest", expanded=not has_dag):
        uploader = UploadZone()
        manifest = uploader.render()
        if manifest is not None:
            st.session_state.manifest = manifest
            st.session_state.loading = True

            # Build DAG
            dag: nx.DiGraph = nx.DiGraph()
            nodes_data = manifest.get("nodes", {})

            for node_id, node_info in nodes_data.items():
                resource_type = node_info.get("resource_type", "unknown")
                if resource_type in ("model", "source", "seed", "snapshot"):
                    dag.add_node(
                        node_id,
                        resource_type=resource_type,
                        description=node_info.get("description", ""),
                        schema=node_info.get("schema", ""),
                        columns=node_info.get("columns", {}),
                    )

            for node_id, node_info in nodes_data.items():
                if node_id in dag:
                    depends_on = node_info.get("depends_on", {}).get("nodes", [])
                    for dep in depends_on:
                        if dep in dag:
                            dag.add_edge(dep, node_id)

            st.session_state.dag = dag
            st.session_state.loading = False
            st.rerun()

    # ── Stats section (collapsible) ───────────────────────────────────────
    with st.expander("📊 Stats", expanded=has_dag):
        _render_animated_stats(st.session_state.dag)

    st.divider()

    # ── Filters section (collapsible) ─────────────────────────────────────
    with st.expander("🔎 Filters", expanded=True):
        st.markdown("**Resource types**")
        show_models = st.checkbox(
            "Models",
            value=st.session_state.filters.get("model", True),
            key="filter_model",
        )
        show_sources = st.checkbox(
            "Sources",
            value=st.session_state.filters.get("source", True),
            key="filter_source",
        )
        show_seeds = st.checkbox(
            "Seeds",
            value=st.session_state.filters.get("seed", True),
            key="filter_seed",
        )
        st.session_state.filters = {
            "model": show_models,
            "source": show_sources,
            "seed": show_seeds,
        }

    # ── Model list (collapsible) ──────────────────────────────────────────
    if has_dag:
        with st.expander("📋 Models", expanded=False):
            sidebar_query = st.text_input(
                "Search",
                placeholder="dim_customers",
                key="sidebar_search_input",
                label_visibility="collapsed",
            )

            dag = st.session_state.dag
            shown = 0
            for node in sorted(dag.nodes):
                rtype = dag.nodes[node].get("resource_type", "?")
                if rtype == "model" and not show_models:
                    continue
                if rtype == "source" and not show_sources:
                    continue
                if rtype == "seed" and not show_seeds:
                    continue
                label = node.split(".")[-1] if "." in node else node
                if sidebar_query and sidebar_query.lower() not in node.lower():
                    continue
                if st.button(
                    f"`{label}`",
                    key=f"node_{node}",
                    use_container_width=True,
                ):
                    st.session_state.selected_node = node
                shown += 1
                if shown >= 50:
                    st.caption(f"... and {len(dag.nodes) - shown} more")
                    break


# ---------------------------------------------------------------------------
# Main content
# ---------------------------------------------------------------------------
st.markdown("### 🌐 Lineage Graph")

# Physics toggle row
physics_col, dag_info_col = st.columns([1, 3])
with physics_col:
    physics_enabled = st.checkbox(
        "⚡ Physics simulation",
        value=st.session_state.physics_enabled,
        key="physics_toggle",
        help="Toggle force-directed physics on/off.",
    )
    st.session_state.physics_enabled = physics_enabled

if has_dag:
    with dag_info_col:
        node_count = len(st.session_state.dag.nodes)
        edge_count = len(st.session_state.dag.edges)
        st.caption(
            f"Showing {node_count:,} nodes · {edge_count:,} edges · "
            "scroll to zoom · drag to pan · click node for details"
        )

# ── DAG viewer ─────────────────────────────────────────────────────────────
if st.session_state.dag and len(st.session_state.dag.nodes) > 0:
    render_dag(
        st.session_state.dag,
        height=580,
        physics_enabled=st.session_state.physics_enabled,
        selected_node=st.session_state.selected_node,
    )
else:
    _render_skeleton_loader()


# ── Share card (shown when DAG is loaded) ────────────────────────────────────
if has_dag:
    with st.expander("🔗 Share & Export", expanded=False):
        render_share_card(
            dag=st.session_state.dag,
            selected_node=st.session_state.selected_node,
            physics_enabled=st.session_state.physics_enabled,
            filters=st.session_state.filters,
        )


st.divider()

# ── Impact search ────────────────────────────────────────────────────────────
st.markdown("### 🔍 Impact Analysis")
selected_model = render_search_panel(st.session_state.dag, key="main_search")

# Handle sidebar node click
if st.session_state.selected_node:
    selected_model = st.session_state.selected_node

if selected_model:
    render_blast_radius(st.session_state.dag, selected_model)
    render_detail_panel(st.session_state.dag, selected_model)


# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="cascade-footer">
        🌊 Cascade — Open Source Data Lineage &nbsp;|&nbsp;
        Built with Streamlit + PyVis &nbsp;|&nbsp;
        <a href="https://github.com" target="_blank" style="color: #58A6FF;">
            View on GitHub
        </a>
    </div>
    """,
    unsafe_allow_html=True,
)
