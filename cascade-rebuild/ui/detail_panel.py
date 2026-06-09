"""
Node detail panel — shows columns, SQL, upstream/downstream for a selected node.

Includes the killer feature: column-level lineage table with:
- Column name, data type, description, lineage status (dot indicator)
- Click a column to see its upstream + downstream column-level sub-tree
- Anchor (`id="cascade-detail-panel"`) for auto-scroll from the DAG
"""

import streamlit as st
import pandas as pd
from lineage.models import TableNode, LineageGraph
from lineage.impact import get_downstream, get_upstream, blast_radius_score


# ─── CSS for the column table ───────────────────────────────────────────────
COLUMN_TABLE_CSS = """
<style>
/* Column lineage table */
.col-table {
    width: 100%;
    border-collapse: collapse;
    font-family: 'Inter', -apple-system, sans-serif;
    font-size: 12px;
    background: #161B22;
    border: 1px solid #30363D;
    border-radius: 8px;
    overflow: hidden;
}
.col-table thead th {
    background: #21262D;
    color: #8B949E;
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 10px 12px;
    text-align: left;
    border-bottom: 1px solid #30363D;
    font-weight: 600;
}
.col-table tbody tr {
    border-bottom: 1px solid #21262D;
    transition: background 0.12s;
}
.col-table tbody tr:last-child { border-bottom: none; }
.col-table tbody tr:hover { background: #1C2128; }
.col-table tbody tr.col-selected { background: rgba(88, 166, 255, 0.08); }
.col-table td {
    padding: 8px 12px;
    color: #E6EDF3;
    vertical-align: top;
}
.col-name {
    font-family: 'JetBrains Mono', 'Consolas', monospace;
    font-size: 12px;
    color: #E6EDF3;
    font-weight: 500;
}
.col-type-pill {
    display: inline-block;
    padding: 2px 8px;
    background: #21262D;
    color: #79B8FF;
    border: 1px solid #30363D;
    border-radius: 10px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    font-weight: 500;
    letter-spacing: 0.3px;
    white-space: nowrap;
}
.col-type-pill.inferred {
    color: #8B949E;
    background: transparent;
    border-style: dashed;
}
.col-desc {
    color: #8B949E;
    font-size: 11px;
    line-height: 1.4;
    max-width: 280px;
    overflow: hidden;
    text-overflow: ellipsis;
}
.col-status {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: #8B949E;
    white-space: nowrap;
}
.lineage-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
}
.lineage-dot.both { background: #58A6FF; box-shadow: 0 0 4px #58A6FF80; }
.lineage-dot.up   { background: #39D353; }
.lineage-dot.down { background: #D29922; }
.lineage-dot.none { background: #30363D; }

/* Column sub-tree */
.col-subtree {
    background: #0D1117;
    border: 1px solid #30363D;
    border-left: 3px solid #58A6FF;
    border-radius: 6px;
    padding: 14px 16px;
    margin: 12px 0 8px 0;
    font-family: 'Inter', sans-serif;
    font-size: 12px;
}
.col-subtree-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;
    padding-bottom: 8px;
    border-bottom: 1px solid #30363D;
}
.col-subtree-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    font-weight: 600;
    color: #E6EDF3;
}
.col-subtree-section {
    margin-top: 10px;
}
.col-subtree-section-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    color: #8B949E;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    gap: 6px;
}
.col-subtree-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 5px 8px;
    border-radius: 4px;
    font-size: 12px;
    color: #E6EDF3;
    margin: 2px 0;
}
.col-subtree-row:hover { background: #161B22; }
.col-subtree-table {
    color: #79B8FF;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
}
.col-subtree-col {
    color: #E6EDF3;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
}
.col-subtree-arrow {
    color: #30363D;
    font-family: 'JetBrains Mono', monospace;
    font-size: 14px;
}
.col-subtree-empty {
    color: #8B949E;
    font-size: 11px;
    font-style: italic;
    padding: 4px 8px;
}
.col-subtree-close {
    background: transparent;
    border: 1px solid #30363D;
    color: #8B949E;
    border-radius: 4px;
    padding: 2px 8px;
    font-family: 'Inter', sans-serif;
    font-size: 10px;
    cursor: pointer;
}
.col-subtree-close:hover { color: #E6EDF3; border-color: #58A6FF; }

.col-table-clickable {
    cursor: pointer;
    user-select: none;
}
</style>
"""


# ─── Helpers ────────────────────────────────────────────────────────────────

def _classify_lineage_status(node: TableNode, col_name: str, graph: LineageGraph) -> str:
    """
    Classify a column's lineage status: 'both', 'up', 'down', or 'none'.

    - 'up': column has upstream dependencies (i.e., it inherits from source cols)
    - 'down': column is referenced by downstream nodes
    - 'both': has both
    - 'none': no lineage info (e.g., a leaf source column with no downstream refs)
    """
    has_up = False
    has_down = False

    # Upstream: this node's column_deps for this column, OR the ColumnNode.source_columns
    col_node = node.columns.get(col_name)
    if col_node and col_node.source_columns:
        has_up = True
    if col_name in node.column_deps and node.column_deps[col_name]:
        has_up = True

    # Downstream: any downstream node that references this column in their column_deps
    for dn_uid in get_downstream(node.unique_id, graph):
        dn = graph.get_node(dn_uid)
        if not dn:
            continue
        # Check downstream's column_deps for (this_node.unique_id, col_name)
        for tgt_col, sources in dn.column_deps.items():
            for (src_uid, src_col) in sources:
                if src_uid == node.unique_id and src_col == col_name:
                    has_down = True
                    break
            if has_down:
                break
        if has_down:
            break

    if has_up and has_down:
        return "both"
    if has_up:
        return "up"
    if has_down:
        return "down"
    return "none"


def _get_column_upstream(node: TableNode, col_name: str, graph: LineageGraph) -> list[tuple[str, str, str]]:
    """
    Get upstream column dependencies for a column.
    Returns: list of (source_table_name, source_column, source_uid)
    """
    results: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str]] = set()

    # From ColumnNode.source_columns (fully-qualified strings like "raw_orders.order_id")
    col_node = node.columns.get(col_name)
    if col_node and col_node.source_columns:
        for src_str in col_node.source_columns:
            # Parse "table.col" or "schema.table.col"
            if "." in src_str:
                parts = src_str.split(".")
                src_col = parts[-1]
                src_table = parts[-2] if len(parts) >= 2 else "?"
                key = (src_table, src_col)
                if key not in seen:
                    seen.add(key)
                    # Try to find uid
                    src_uid = _resolve_table_uid(src_table, graph)
                    results.append((src_table, src_col, src_uid or ""))

    # From node.column_deps[col_name] (list of (uid, col))
    if col_name in node.column_deps:
        for (src_uid, src_col) in node.column_deps[col_name]:
            key = (src_uid, src_col)
            if key not in seen:
                seen.add(key)
                src_table_node = graph.get_node(src_uid)
                src_table_name = src_table_node.name if src_table_node else src_uid.split(".")[-1]
                results.append((src_table_name, src_col, src_uid))

    return results


def _get_column_downstream(node: TableNode, col_name: str, graph: LineageGraph) -> list[tuple[str, str, str]]:
    """
    Get downstream column dependencies (which downstream nodes/columns depend on this one).
    Returns: list of (target_table_name, target_column, target_uid)
    """
    results: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str]] = set()

    for dn_uid in get_downstream(node.unique_id, graph):
        dn = graph.get_node(dn_uid)
        if not dn:
            continue
        # Check each target column in downstream's column_deps
        for tgt_col, sources in dn.column_deps.items():
            for (src_uid, src_col) in sources:
                if src_uid == node.unique_id and src_col == col_name:
                    key = (dn_uid, tgt_col)
                    if key not in seen:
                        seen.add(key)
                        results.append((dn.name, tgt_col, dn_uid))

    return results


def _resolve_table_uid(table_name: str, graph: LineageGraph) -> str | None:
    """Try to resolve a short table name to a unique_id in the graph."""
    for uid in graph.nodes:
        node = graph.get_node(uid)
        if node and node.name == table_name:
            return uid
    return None


# ─── Main render ───────────────────────────────────────────────────────────

def render_detail_panel(node: TableNode, graph: LineageGraph):
    """
    Render the detail panel for a selected node.
    Includes the anchor `id="cascade-detail-panel"` for auto-scroll.
    """
    if not node:
        st.info("Select a node in the graph to see details")
        return

    # Inject CSS for column table once per render
    st.markdown(COLUMN_TABLE_CSS, unsafe_allow_html=True)

    # Anchor for auto-scroll from the DAG
    st.markdown('<div id="cascade-detail-panel"></div>', unsafe_allow_html=True)

    # Header
    col1, col2 = st.columns([1, 4])
    with col1:
        st.markdown(
            f"<span class='type-badge {node.resource_type}'>{node.resource_type.upper()}</span>",
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(f"**{node.name}**")
        if node.schema:
            st.caption(f"Schema: `{node.schema}`")

    # Description
    if node.description:
        st.markdown(
            f"<div style='color:#8B949E; font-size:13px; margin:8px 0;'>{node.description}</div>",
            unsafe_allow_html=True,
        )

    # Risk score
    score = blast_radius_score(node.unique_id, graph)
    risk_class = score.level.lower()
    risk_emoji = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴", "CRITICAL": "⚫"}.get(score.level, "")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("Risk Level", f"{risk_emoji} {score.level}", help="Based on downstream impact count")
    with col_b:
        st.metric("Upstream", score.upstream_count)
    with col_c:
        st.metric("Downstream", score.downstream_count)

    st.divider()

    # ── Columns section (the killer feature) ──────────────────────────────
    _render_columns_section(node, graph)

    st.divider()

    # ── Compiled SQL ─────────────────────────────────────────────────────
    if node.compiled_sql:
        with st.expander("📝 Compiled SQL"):
            st.code(node.compiled_sql[:2000], language="sql", line_numbers=False)
            if len(node.compiled_sql) > 2000:
                st.caption(f"(truncated — full SQL has {len(node.compiled_sql)} chars)")

    # Raw SQL
    if node.raw_sql and node.raw_sql != node.compiled_sql:
        with st.expander("📄 Raw SQL"):
            st.code(node.raw_sql[:2000], language="sql", line_numbers=False)

    st.divider()

    # ── Upstream and Downstream tables ──────────────────────────────────
    up_ids = get_upstream(node.unique_id, graph)
    down_ids = get_downstream(node.unique_id, graph)

    col_up, col_down = st.columns(2)

    with col_up:
        st.markdown(f"**Upstream ({len(up_ids)})**")
        if up_ids:
            for uid in up_ids:
                up_node = graph.get_node(uid)
                if up_node:
                    short = up_node.name
                    color = {"model": "#58A6FF", "source": "#39D353", "seed": "#8B949E"}.get(up_node.resource_type, "#58A6FF")
                    st.markdown(
                        f"<span style='color:{color}; font-size:11px;'>●</span> "
                        f"<span style='font-family:JetBrains Mono,monospace; font-size:12px; color:#E6EDF3;'>{short}</span> "
                        f"<span style='color:#8B949E; font-size:10px;'> ({up_node.resource_type})</span>",
                        unsafe_allow_html=True,
                    )
                    if node.column_deps:
                        matching_cols = [c for c, srcs in node.column_deps.items()
                                         if any(s[0] == uid for s in srcs)]
                        if matching_cols:
                            cols_str = ", ".join(f"`{c}`" for c in matching_cols[:5])
                            st.caption(f"  ← {cols_str}", unsafe_allow_html=False)
        else:
            st.caption("No upstream dependencies (source node)")

    with col_down:
        st.markdown(f"**Downstream ({len(down_ids)})**")
        if down_ids:
            for uid in down_ids:
                dn_node = graph.get_node(uid)
                if dn_node:
                    short = dn_node.name
                    color = {"model": "#58A6FF", "source": "#39D353", "seed": "#8B949E"}.get(dn_node.resource_type, "#58A6FF")
                    st.markdown(
                        f"<span style='color:{color}; font-size:11px;'>●</span> "
                        f"<span style='font-family:JetBrains Mono,monospace; font-size:12px; color:#E6EDF3;'>{short}</span> "
                        f"<span style='color:#8B949E; font-size:10px;'> ({dn_node.resource_type})</span>",
                        unsafe_allow_html=True,
                    )
        else:
            st.caption("No downstream dependents (terminal node)")

    # View blast radius button
    st.divider()
    if st.button("🔍 View Full Blast Radius", use_container_width=True, key="blast_radius_btn"):
        st.session_state["view_blast_radius"] = node.unique_id
        st.rerun()


# ─── Columns table ──────────────────────────────────────────────────────────

def _render_columns_section(node: TableNode, graph: LineageGraph) -> None:
    """Render the column-level table with lineage status indicators + click-to-expand sub-tree."""
    if not node.columns:
        st.markdown(
            "<div style='color:#8B949E; font-size:12px; padding:8px 0;'>"
            "No column metadata available"
            "</div>",
            unsafe_allow_html=True,
        )
        return

    st.markdown(f"#### Columns ({len(node.columns)})")

    # Initialize selected column state for this node
    selected_column_key = f"selected_column_{node.unique_id}"
    if selected_column_key not in st.session_state:
        st.session_state[selected_column_key] = None

    selected_column = st.session_state[selected_column_key]

    # Build the column table HTML
    rows_html = []
    for col_name, col_node in node.columns.items():
        status = _classify_lineage_status(node, col_name, graph)
        status_label = {
            "both": "↕ both",
            "up": "↑ upstream",
            "down": "↓ downstream",
            "none": "— none",
        }[status]
        is_selected = (col_name == selected_column)
        row_class = "col-selected" if is_selected else ""
        data_type = col_node.data_type or "inferred"
        type_pill_class = "inferred" if not col_node.data_type else ""
        description = col_node.description or "—"

        # Truncate description to ~80 chars
        if len(description) > 80:
            description = description[:77] + "…"

        rows_html.append(
            '<tr class="' + row_class + ' col-table-clickable" data-col="' + col_name + '">'
            '<td><span class="col-name">' + col_name + '</span></td>'
            '<td><span class="col-type-pill ' + type_pill_class + '">' + data_type + '</span></td>'
            '<td><span class="col-desc">' + description + '</span></td>'
            '<td><span class="col-status">'
            '<span class="lineage-dot ' + status + '"></span>'
            '<span>' + status_label + '</span>'
            '</span></td>'
            '</tr>'
        )

    table_html = (
        '<table class="col-table">'
        '<thead><tr>'
        '<th>Column</th><th>Type</th><th>Description</th><th>Lineage</th>'
        '</tr></thead>'
        '<tbody>' + ''.join(rows_html) + '</tbody>'
        '</table>'
    )
    st.html(table_html)

    # Click-to-select for a column: use buttons below the table for reliable state updates.
    # Streamlit can't bind clicks to table rows, so we use one button per column.
    # Render the buttons inline (compact) so they're next to the table visually.
    st.markdown(
        "<div style='color:#8B949E; font-size:11px; margin: 4px 0 6px 0;'>"
        "Click a column to view its lineage sub-tree:</div>",
        unsafe_allow_html=True,
    )

    # Render buttons in a flow layout
    cols_to_render = list(node.columns.keys())
    # Use 3 buttons per row
    for i in range(0, len(cols_to_render), 3):
        chunk = cols_to_render[i:i + 3]
        btn_cols = st.columns(len(chunk))
        for j, cname in enumerate(chunk):
            with btn_cols[j]:
                is_sel = (cname == selected_column)
                btn_label = f"● {cname}" if is_sel else cname
                if st.button(
                    btn_label,
                    key=f"colbtn_{node.unique_id}_{cname}",
                    use_container_width=True,
                ):
                    # Toggle: clicking the same one deselects
                    if is_sel:
                        st.session_state[selected_column_key] = None
                    else:
                        st.session_state[selected_column_key] = cname
                    st.rerun()

    # Render the sub-tree if a column is selected
    if selected_column:
        _render_column_subtree(node, selected_column, graph, selected_column_key)


def _render_column_subtree(
    node: TableNode,
    col_name: str,
    graph: LineageGraph,
    selected_column_key: str,
) -> None:
    """Render upstream + downstream column sub-tree for a selected column."""
    upstream = _get_column_upstream(node, col_name, graph)
    downstream = _get_column_downstream(node, col_name, graph)

    # Header
    st.markdown(
        f"""
        <div class="col-subtree">
            <div class="col-subtree-header">
                <div class="col-subtree-title">📊 Column Lineage: <span style="color:#79B8FF;">{col_name}</span></div>
            </div>
        """,
        unsafe_allow_html=True,
    )

    # Upstream section
    st.markdown(
        """
        <div class="col-subtree-section">
            <div class="col-subtree-section-title">↑ Upstream Sources</div>
        """,
        unsafe_allow_html=True,
    )
    if upstream:
        for (src_table, src_col, src_uid) in upstream:
            type_color = "#39D353"  # default upstream is green (source)
            if src_uid:
                src_node = graph.get_node(src_uid)
                if src_node:
                    type_color = {"model": "#58A6FF", "source": "#39D353", "seed": "#8B949E", "snapshot": "#D29922"}.get(
                        src_node.resource_type, "#58A6FF"
                    )
            st.markdown(
                f"""
                <div class="col-subtree-row">
                    <span style="color:{type_color}; font-size:10px;">●</span>
                    <span class="col-subtree-table">{src_table}</span>
                    <span class="col-subtree-arrow">.</span>
                    <span class="col-subtree-col">{src_col}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            "<div class='col-subtree-empty'>No upstream columns detected.</div>",
            unsafe_allow_html=True,
        )

    # Downstream section
    st.markdown(
        """
        <div class="col-subtree-section">
            <div class="col-subtree-section-title">↓ Downstream Dependents</div>
        """,
        unsafe_allow_html=True,
    )
    if downstream:
        for (tgt_table, tgt_col, tgt_uid) in downstream:
            type_color = "#58A6FF"
            if tgt_uid:
                tgt_node = graph.get_node(tgt_uid)
                if tgt_node:
                    type_color = {"model": "#58A6FF", "source": "#39D353", "seed": "#8B949E", "snapshot": "#D29922"}.get(
                        tgt_node.resource_type, "#58A6FF"
                    )
            st.markdown(
                f"""
                <div class="col-subtree-row">
                    <span style="color:{type_color}; font-size:10px;">●</span>
                    <span class="col-subtree-table">{tgt_table}</span>
                    <span class="col-subtree-arrow">.</span>
                    <span class="col-subtree-col">{tgt_col}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            "<div class='col-subtree-empty'>No downstream dependents.</div>",
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

    # Close button
    if st.button("✕ Close column lineage", key=f"close_subtree_{node.unique_id}_{col_name}"):
        st.session_state[selected_column_key] = None
        st.rerun()
