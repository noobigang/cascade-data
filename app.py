"""
Cascade — Column-level Lineage Dashboard for dbt Projects

A premium Streamlit dashboard for visualizing dbt model lineage,
column-level dependencies, and impact analysis.
"""

from __future__ import annotations

import streamlit as st

# Import lineage engine
from lineage import (
    LineageGraph,
    enrich_graph_with_lineage,
    get_downstream,
    get_upstream,
    parse_manifest_from_dict,
)

# Import UI components
from ui import (
    inject_dark_theme,
    load_demo_manifest,
    render_dag_viewer,
    render_detail_panel,
    render_hero,
    render_impact_panel,
    render_sidebar,
    render_try_demo_button,
    render_upload_zone,
)

# ─── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Cascade — dbt Lineage Dashboard",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom dark theme CSS ─────────────────────────────────────────────────────
inject_dark_theme()


# ─── Session state ─────────────────────────────────────────────────────────────
def _init_session():
    defaults = {
        "graph": None,
        "manifest_data": None,
        "catalog_data": None,
        "selected_node_uid": None,
        "show_blast_radius": None,
        "filters": {"show_models": True, "show_sources": True, "show_seeds": True},
        "dag_graph_data": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


_init_session()


# ─── Helpers ───────────────────────────────────────────────────────────────────
def _compute_stats(graph: LineageGraph) -> dict:
    """Compute dashboard stats from the graph."""
    models = sources = seeds = snapshots = 0
    total_columns = 0
    total_edges = len(graph.edges)

    for uid in graph.nodes:
        node = graph.get_node(uid)
        if not node:
            continue
        rt = node.resource_type
        if rt == "model":
            models += 1
        elif rt == "source":
            sources += 1
        elif rt == "seed":
            seeds += 1
        elif rt == "snapshot":
            snapshots += 1
        total_columns += len(node.columns)

    return {
        "models": models,
        "sources": sources,
        "seeds": seeds,
        "snapshots": snapshots,
        "edges": total_edges,
        "columns": total_columns,
    }


def _build_dag_data(graph: LineageGraph, filters: dict = None) -> dict:
    """
    Build the DAG data structure for D3.js consumption.
    Applies resource type filters.
    """
    if filters is None:
        filters = {"show_models": True, "show_sources": True, "show_seeds": True}

    # Compute downstream counts
    downstream_counts: dict[str, int] = {}
    for uid in graph.nodes:
        downstream_counts[uid] = len(get_downstream(uid, graph))

    # Filter nodes
    visible_node_ids: set[str] = set()
    for uid in graph.nodes:
        node = graph.get_node(uid)
        if not node:
            continue

        rt = node.resource_type
        if rt == "model" and not filters.get("show_models", True):
            continue
        if rt == "source" and not filters.get("show_sources", True):
            continue
        if rt == "seed" and not filters.get("show_seeds", True):
            continue
        if rt == "snapshot" and not filters.get("show_snapshots", True):
            continue

        visible_node_ids.add(uid)

    # Build nodes list
    nodes = []
    for uid in graph.nodes:
        if uid not in visible_node_ids:
            continue
        node = graph.get_node(uid)
        if not node:
            continue

        nodes.append({
            "id": uid,
            "name": node.name,
            "resource_type": node.resource_type,
            "schema": node.schema or "",
            "column_count": len(node.columns),
            "upstream_count": len(get_upstream(uid, graph)),
            "downstream_count": downstream_counts.get(uid, 0),
            "description": node.description or "",
        })

    # Build edges list (only between visible nodes)
    edges = []
    for src, tgt in graph.edges:
        if src in visible_node_ids and tgt in visible_node_ids:
            edges.append({"source": src, "target": tgt})

    return {"nodes": nodes, "edges": edges}


# ─── Main app ─────────────────────────────────────────────────────────────────
def main():
    # ── Sidebar ──────────────────────────────────────────────────────────────
    st.session_state.get("filters", {})
    graph = st.session_state.get("graph")

    def on_model_select(uid):
        st.session_state.selected_node_uid = uid
        st.rerun()

    sidebar_filters = render_sidebar(graph, on_model_select)

    # Update filters in session state
    st.session_state.filters = sidebar_filters

    # ── Main content ────────────────────────────────────────────────────────
    st.title("🌊 Cascade")

    if graph is None:
        # No graph loaded yet — show upload/demo
        _render_empty_state()
        return

    # ── Stats ──────────────────────────────────────────────────────────────
    stats = _compute_stats(graph)
    render_hero(project_name="", stats=stats)

    # ── DAG Viewer + Detail Panel side by side ─────────────────────────────
    st.markdown("### Lineage Graph")

    dag_data = _build_dag_data(graph, sidebar_filters)

    if dag_data["nodes"]:
        # Side-by-side: DAG on left, Detail panel on right
        col_dag, col_detail = st.columns([1, 1], gap="medium")

        with col_dag:
            # Render the D3.js DAG. The component returns a dict with the latest
            # click event from the iframe (or None if no click has happened).
            current_selected = st.session_state.get("selected_node_uid")
            click_event = render_dag_viewer(
                dag_data,
                height=620,
                key="dag_viewer",
                current_selected=current_selected,
            )

            # If the iframe reported a new selection, sync it into session state
            # and rerun so the sidebar highlight + detail panel update.
            if click_event and isinstance(click_event, dict):
                new_uid = click_event.get("selected_node_uid")
                if new_uid != current_selected:
                    st.session_state.selected_node_uid = new_uid
                    st.rerun()

            # DAG controls hint
            st.caption(
                "🖱️ Drag to pan · Scroll to zoom · Click node to select · Toggle filters in top-left"
            )

        with col_detail:
            # Selected node detail panel — always visible alongside the DAG
            selected_uid = st.session_state.get("selected_node_uid")
            if selected_uid and graph.has_node(selected_uid):
                selected_node = graph.get_node(selected_uid)
                with st.container():
                    render_detail_panel(selected_node, graph)
            else:
                # Auto-select first node if none selected
                if dag_data["nodes"]:
                    first_uid = dag_data["nodes"][0]["id"]
                    st.session_state.selected_node_uid = first_uid
                    st.rerun()
                else:
                    st.info("No nodes to display")
    else:
        st.info("No nodes match the current filters.")

    # Auto-scroll + state bridge — listens for DAG node clicks and propagates
    # the selection back to Streamlit session state.
    import json as _json

    from ui.scroll_bridge import poll_pending_node, render_scroll_bridge
    render_scroll_bridge()
    pending = poll_pending_node(default=None)
    if pending:
        try:
            p = _json.loads(pending) if isinstance(pending, str) else pending
        except Exception:
            p = None
        if p and isinstance(p, dict):
            at = p.get("at") or 0
            uid = p.get("uid")
            last_at = st.session_state.get("_bridge_last_at", 0)
            if at > last_at:
                st.session_state._bridge_last_at = at
                # uid may be null (toggle-off)
                if uid != st.session_state.get("selected_node_uid"):
                    st.session_state.selected_node_uid = uid
                    st.rerun()

    st.divider()

    # ── Impact Analysis ─────────────────────────────────────────────────────
    blast_focus = st.session_state.get("show_blast_radius")
    render_impact_panel(graph, initial_focus=blast_focus)

    # Reset blast radius view after rendering
    if st.session_state.get("show_blast_radius"):
        st.session_state.show_blast_radius = None


def _render_empty_state():
    """Render the empty state when no manifest is loaded."""
    st.markdown(
        '<div class="cascade-hero">'
        '<div class="cascade-hero-bg"></div>'
        '<div class="cascade-hero-wave">🌊</div>'
        '<div class="cascade-hero-title">See the full impact of every data change</div>'
        '<div class="cascade-hero-sub">Column-level lineage for dbt projects — know what breaks before you deploy</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Stats placeholder
    c1, c2, c3, c4 = st.columns(4)
    for col, val, label, type_ in [
        (c1, "—", "Models", "model"),
        (c2, "—", "Sources", "source"),
        (c3, "—", "Edges", "edge"),
        (c4, "—", "Columns", "column"),
    ]:
        with col:
            st.markdown(
                f"""
                <div class="cascade-metric-card {type_}">
                    <div class="cascade-metric-value">{val}</div>
                    <div class="cascade-metric-label">{label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.divider()

    # Upload section
    st.markdown("### Get Started")

    col_upload, col_demo = st.columns(2, gap="large")

    with col_upload:
        # Card-style section header
        st.markdown(
            '<div class="cascade-section-card">'
            '<div class="cascade-section-icon">📦</div>'
            '<div class="cascade-section-title">Upload Your Manifest</div>'
            '<div class="cascade-section-desc">Drop your <code>manifest.json</code> here — generated by <code>dbt compile</code> or <code>dbt build</code></div>'
            '</div>',
            unsafe_allow_html=True,
        )

        manifest_data, catalog_data = render_upload_zone()

        if manifest_data is not None:
            _load_manifest(manifest_data, catalog_data)
            st.rerun()

    with col_demo:
        # Card-style section header
        st.markdown(
            '<div class="cascade-section-card">'
            '<div class="cascade-section-icon">🎲</div>'
            '<div class="cascade-section-title">Try the Demo</div>'
            '<div class="cascade-section-desc">Explore a sample e-commerce dbt project instantly — no upload needed</div>'
            '</div>',
            unsafe_allow_html=True,
        )

        if render_try_demo_button():
            demo_manifest, demo_catalog = load_demo_manifest()
            _load_manifest(demo_manifest, demo_catalog)
            st.rerun()


def _load_manifest(manifest_data: dict, catalog_data: dict = None):
    """Parse manifest and populate session state."""
    with st.spinner("Parsing manifest..."):
        graph = parse_manifest_from_dict(manifest_data, catalog_data)

        # Enrich with column-level lineage
        with st.spinner("Extracting column lineage from compiled SQL..."):
            try:
                enrich_graph_with_lineage(graph)
            except Exception as e:
                st.warning(f"Column-level enrichment skipped: {e}")

        st.session_state.graph = graph
        st.session_state.manifest_data = manifest_data
        st.session_state.catalog_data = catalog_data
        st.session_state.selected_node_uid = None
        st.session_state.show_blast_radius = None


# ─── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
