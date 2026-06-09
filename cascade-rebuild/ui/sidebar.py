"""
Sidebar component — filters, resource list, stats.
"""

import streamlit as st
from lineage.models import LineageGraph
from typing import Callable


def render_sidebar(graph: LineageGraph, on_model_select: Callable[[str], None]) -> dict:
    """
    Render the sidebar with filters, resource list, and stats.

    Args:
        graph: The LineageGraph to render
        on_model_select: Callback(node_uid) when a model is selected

    Returns:
        Dict with filter state: {show_models, show_sources, show_seeds, search_query}
    """
    with st.sidebar:
        # Logo / header
        st.markdown(
            "<div style='text-align:center; margin-bottom:24px;'>"
            "<div style='font-size:28px;'>🌊</div>"
            "<div style='font-family:JetBrains Mono,monospace; font-size:18px; font-weight:700; color:#E6EDF3;'>Cascade</div>"
            "<div style='font-size:11px; color:#8B949E; margin-top:2px;'>Column-level lineage</div>"
            "</div>",
            unsafe_allow_html=True,
        )

        st.divider()

        # ── Empty state: hide filters / search / resource list ──────────────
        # When no manifest is loaded, those sections are useless. Show a hint
        # telling the user how to load one.
        if graph is None:
            st.markdown(
                """
                <div style="
                    background: #0D1117;
                    border: 1px dashed #30363D;
                    border-radius: 10px;
                    padding: 20px 16px;
                    text-align: center;
                    color: #8B949E;
                    font-family: 'Inter', sans-serif;
                    font-size: 12px;
                    line-height: 1.6;
                    margin-bottom: 12px;
                ">
                    <div style="font-size: 32px; margin-bottom: 8px;">📦</div>
                    <div style="color: #E6EDF3; font-weight: 600; font-family: 'JetBrains Mono', monospace; font-size: 13px; margin-bottom: 6px;">
                        No manifest loaded
                    </div>
                    <div>Upload a <code style="background:#21262D;padding:1px 5px;border-radius:3px;color:#58A6FF;">manifest.json</code> in the main panel
                    <br>or click <strong style="color:#58A6FF;">Try Demo</strong> to explore.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            return {
                "show_models": True,
                "show_sources": True,
                "show_seeds": True,
                "search_query": "",
            }

        # Stats summary (only if graph is loaded)
        _render_sidebar_stats(graph)

        st.divider()

        # Filters
        st.markdown("### 🔎 Filters")

        show_models = st.checkbox("Models", value=True, key="filter_models")
        show_sources = st.checkbox("Sources", value=True, key="filter_sources")
        show_seeds = st.checkbox("Seeds", value=True, key="filter_seeds")

        search_query = st.text_input(
            "Search models & columns",
            placeholder="e.g. customers, order_date...",
            key="search_query",
        )

        st.divider()

        # Resource list
        st.markdown("### 📋 Resources")

        filtered_nodes = _get_filtered_nodes(graph, show_models, show_sources, show_seeds, search_query)

        st.caption(f"{len(filtered_nodes)} of {len(graph.nodes)} resources")

        # Highlight the currently selected node
        selected_uid = st.session_state.get("selected_node_uid")

        # Scrollable list
        with st.container():
            for uid in sorted(filtered_nodes, key=lambda x: x.split(".")[-1].lower()):
                node = graph.get_node(uid)
                if not node:
                    continue

                color = {"model": "#58A6FF", "source": "#39D353", "seed": "#8B949E", "snapshot": "#D29922"}.get(
                    node.resource_type, "#58A6FF"
                )

                rt_abbr = node.resource_type[:3].upper()
                schema_label = node.schema or ""
                is_selected = (uid == selected_uid)

                # Highlight the selected row
                if is_selected:
                    st.markdown(
                        f"""
                        <div style="
                            display:flex; align-items:center; gap:6px;
                            padding:6px 8px;
                            background: rgba(88, 166, 255, 0.12);
                            border-left: 3px solid #58A6FF;
                            border-radius: 4px;
                            margin: 2px 0;
                        ">
                            <span style='color:{color}; font-size:10px; font-family:JetBrains Mono,monospace;'>{rt_abbr}</span>
                            <span style='font-family:JetBrains Mono,monospace; font-size:12px; color:#FFFFFF; font-weight:600;'>{node.name}</span>
                            <span style='color:#8B949E; font-size:10px; margin-left:auto;'>{schema_label}</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    # Selected node: render a deselect button instead of "Select"
                    if st.button("✕ Deselect", key=f"sel_{uid}", use_container_width=True):
                        on_model_select(None)
                else:
                    st.markdown(
                        f"<div style='display:flex; align-items:center; gap:6px; padding:2px 0;'>"
                        f"<span style='color:{color}; font-size:10px; font-family:JetBrains Mono,monospace;'>{rt_abbr}</span>"
                        f"<span style='font-family:JetBrains Mono,monospace; font-size:12px; color:#E6EDF3;'>{node.name}</span>"
                        f"<span style='color:#8B949E; font-size:10px; margin-left:auto;'>{schema_label}</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                    if st.button("Select", key=f"sel_{uid}", use_container_width=True):
                        on_model_select(uid)

        return {
            "show_models": show_models,
            "show_sources": show_sources,
            "show_seeds": show_seeds,
            "search_query": search_query,
        }


def _render_sidebar_stats(graph: LineageGraph):
    """Render compact stats in the sidebar."""
    counts = {"models": 0, "sources": 0, "seeds": 0, "snapshots": 0}
    total_cols = 0

    for uid in graph.nodes:
        node = graph.get_node(uid)
        if node:
            rt = node.resource_type
            if rt in counts:
                counts[rt] += 1
            total_cols += len(node.columns)

    st.markdown("### 📊 Stats")
    for label, key in [("Models", "models"), ("Sources", "sources"), ("Seeds", "seeds")]:
        count = counts[key]
        color = {"models": "#58A6FF", "sources": "#39D353", "seeds": "#8B949E"}[key]
        st.markdown(
            f"<span style='color:{color}; font-family:JetBrains Mono,monospace; font-size:13px;'>{count:4d}</span> "
            f"<span style='color:#8B949E; font-size:12px;'>{label}</span>",
            unsafe_allow_html=True,
        )


def _get_filtered_nodes(graph: LineageGraph, show_models: bool, show_sources: bool, show_seeds: bool, search_query: str) -> list[str]:
    """Filter nodes by resource type and search query."""
    result = []

    for uid in graph.nodes:
        node = graph.get_node(uid)
        if not node:
            continue

        # Resource type filter
        if node.resource_type == "model" and not show_models:
            continue
        if node.resource_type == "source" and not show_sources:
            continue
        if node.resource_type == "seed" and not show_seeds:
            continue

        # Search filter
        if search_query:
            q = search_query.lower()
            name_match = q in node.name.lower()
            desc_match = q in node.description.lower()
            col_match = any(q in col.name.lower() for col in node.columns.values())
            schema_match = q in (node.schema or "").lower()

            if not (name_match or desc_match or col_match or schema_match):
                continue

        result.append(uid)

    return result