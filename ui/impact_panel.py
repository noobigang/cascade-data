"""
Impact analysis panel — blast-radius, risk scoring, and column impact
for the currently selected node.

The panel renders below the DAG. It uses the functions in `lineage.impact`
to compute:
- Risk score for changing this node (model, column, or any dependency)
- Full downstream tree (every affected model and column)
- Plain-language "why this score" reasons
- Aggregate stats (most connected nodes, deepest lineage path)
"""
from __future__ import annotations

import streamlit as st

from lineage.impact import (
    blast_radius_score,
    generate_impact_report,
    get_all_column_impacts,
    get_deepest_lineage_path,
    get_most_connected_nodes,
)
from lineage.models import LineageGraph


def render_impact_panel(
    graph: LineageGraph,
    initial_focus: str | None = None,
) -> None:
    """Render the impact / blast-radius panel.

    Args:
        graph: the parsed LineageGraph
        initial_focus: optional uid of a node to focus on (from "View Full
            Blast Radius" button in the detail panel)
    """
    st.markdown("### 💥 Impact Analysis")

    focus = initial_focus or st.session_state.get("selected_node_uid")

    if focus and graph.has_node(focus):
        _render_focused_impact(graph, focus)
    else:
        _render_overview_impact(graph)


def _render_focused_impact(graph: LineageGraph, focus_uid: str) -> None:
    """Render blast-radius analysis for a specific node."""
    score = blast_radius_score(focus_uid, graph)
    node = graph.get_node(focus_uid)
    if not node:
        st.warning(f"Node `{focus_uid}` not found.")
        return

    # Risk badge — score.level is a string like "LOW" / "MEDIUM" / "HIGH" / "CRITICAL"
    risk_class = score.level.lower()
    risk_emoji = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴", "CRITICAL": "🔴"}.get(
        score.level, "🟢"
    )
    risk_label = {
        "LOW": "Low",
        "MEDIUM": "Medium",
        "HIGH": "High",
        "CRITICAL": "Critical",
    }.get(score.level, "Low")

    # Column count via per-column impacts
    col_impacts = get_all_column_impacts(focus_uid, graph)
    # col_impacts is dict[col_name, list[(table, column)]]
    total_col_relations = sum(len(v) for v in col_impacts.values())

    st.markdown(
        f"""
        <div class="cascade-impact-card {risk_class}">
            <div class="cascade-impact-header">
                <span class="cascade-impact-emoji">{risk_emoji}</span>
                <div>
                    <div class="cascade-impact-title">Risk: {risk_label}</div>
                    <div class="cascade-impact-target">
                        Changing <code>{node.name}</code> would impact:
                    </div>
                </div>
            </div>
            <div class="cascade-impact-stats">
                <div class="cascade-impact-stat">
                    <div class="cascade-impact-stat-value">{score.downstream_count}</div>
                    <div class="cascade-impact-stat-label">Models affected</div>
                </div>
                <div class="cascade-impact-stat">
                    <div class="cascade-impact-stat-value">{total_col_relations}</div>
                    <div class="cascade-impact-stat-label">Column relations</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Detailed report
    with st.expander("Full blast-radius report", expanded=False):
        report = generate_impact_report(focus_uid, graph)
        st.code(report, language="text")

    # Column-level impacts
    if col_impacts:
        with st.expander(
            f"Per-column impact ({len(col_impacts)} columns affected)", expanded=False
        ):
            for col_name, relations in list(col_impacts.items())[:20]:
                # relations is a list of (downstream_table, downstream_column)
                downstream_tables = list({t for t, _c in relations})
                downstream_list = ", ".join(
                    f"`{t}`" for t in downstream_tables[:5]
                )
                if len(downstream_tables) > 5:
                    downstream_list += f" (+{len(downstream_tables) - 5} more)"
                st.markdown(
                    f"- **`{col_name}`** — affects {len(downstream_tables)} model(s): "
                    f"{downstream_list}"
                )


def _render_overview_impact(graph: LineageGraph) -> None:
    """Render aggregate stats when no node is selected."""
    most_connected = get_most_connected_nodes(graph, top_n=5)
    deepest = get_deepest_lineage_path(graph)

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("#### Most Connected Nodes")
        st.caption(
            "Models or sources referenced by the most other resources. "
            "Changing these has the highest blast radius."
        )
        if most_connected:
            for uid, degree in most_connected:
                node = graph.get_node(uid)
                if node:
                    st.markdown(
                        f"- **`{node.name}`** — {degree} connections"
                    )
        else:
            st.info("No connections to display.")

    with c2:
        st.markdown("#### Deepest Lineage Path")
        st.caption(
            "The longest chain of dependencies in this project. "
            "The deeper the chain, the more transformations a value goes through."
        )
        if deepest:
            path_names = []
            for u in deepest[:5]:
                n = graph.get_node(u)
                path_names.append(n.name if n else u.split(".")[-1])
            st.markdown(" → ".join(f"`{n}`" for n in path_names))
            if len(deepest) > 5:
                st.caption(f"... and {len(deepest) - 5} more models in this chain")
        else:
            st.info("No lineage chain found.")
