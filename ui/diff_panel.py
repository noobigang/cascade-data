"""
Manifest diff panel — upload a "before" and "after" manifest.json and
see what changed at the model, column, and dependency level.

The panel renders below the impact analysis. It uses the engine in
`lineage.diff` to compute the diff, then displays it as a list of
added/removed/modified nodes with their column-level changes.
"""
from __future__ import annotations

import json

import streamlit as st

from lineage.diff import (
    ChangeType,
    Severity,
    diff_manifests,
)


def _load_manifest_file(uploaded_file) -> dict | None:
    """Parse an uploaded manifest.json, returning None on validation failure."""
    if uploaded_file is None:
        return None
    try:
        data = json.load(uploaded_file)
    except json.JSONDecodeError as e:
        st.error(f"Invalid JSON: {e}")
        return None
    if "nodes" not in data and "sources" not in data:
        st.error("Invalid manifest.json: missing 'nodes' or 'sources' key.")
        return None
    return data


def _render_node_change(node, prefix: str) -> None:
    """Render one NodeChange with all its sub-changes."""
    # Severity color
    sev_colors = {
        Severity.BREAKING: "#F85149",
        Severity.WARNING: "#D29922",
        Severity.INFO: "#39D353",
    }
    sev_color = sev_colors.get(node.severity, "#8B949E")
    sev_label = node.severity.value.upper()

    st.markdown(
        f"""
        <div style="
            background: #161B22;
            border: 1px solid #30363D;
            border-left: 4px solid {sev_color};
            border-radius: 6px;
            padding: 10px 14px;
            margin: 8px 0;
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
        ">
            <div style="font-weight: 600; color: #E6EDF3; margin-bottom: 4px;">
                {prefix} {node.unique_id}
            </div>
            <div style="color: {sev_color}; font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px;">
                {sev_label} · {node.resource_type}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Column changes
    for c in node.column_changes:
        marker = {
            ChangeType.COLUMN_ADDED: "+",
            ChangeType.COLUMN_REMOVED: "-",
            ChangeType.COLUMN_TYPE_CHANGED: "~",
            ChangeType.COLUMN_DESCRIPTION_CHANGED: "i",
        }.get(c.change_type, "?")
        marker_color = sev_colors.get(c.severity, "#8B949E")
        detail = ""
        if c.before is not None or c.after is not None:
            detail = f" `{c.before or ''}` → `{c.after or ''}`"
        st.markdown(
            f"<div style='margin-left: 24px; color: {marker_color}; "
            f"font-family: JetBrains Mono, monospace; font-size: 11px;'>"
            f"{marker} column <code>{c.column}</code>: {c.change_type.value}{detail}</div>",
            unsafe_allow_html=True,
        )

    # Deps
    for d in node.deps_added:
        st.markdown(
            f"<div style='margin-left: 24px; color: #D29922; "
            f"font-family: JetBrains Mono, monospace; font-size: 11px;'>"
            f"+ dep <code>{d}</code></div>",
            unsafe_allow_html=True,
        )
    for d in node.deps_removed:
        st.markdown(
            f"<div style='margin-left: 24px; color: #F85149; "
            f"font-family: JetBrains Mono, monospace; font-size: 11px;'>"
            f"- dep <code>{d}</code></div>",
            unsafe_allow_html=True,
        )

    # Schema
    if node.schema_before and node.schema_after and node.schema_before != node.schema_after:
        st.markdown(
            f"<div style='margin-left: 24px; color: #D29922; "
            f"font-family: JetBrains Mono, monospace; font-size: 11px;'>"
            f"? schema <code>{node.schema_before}</code> → <code>{node.schema_after}</code></div>",
            unsafe_allow_html=True,
        )


def render_diff_panel() -> None:
    """Render the manifest diff panel.

    Two uploaders (before / after). When both are loaded, computes the
    diff and displays a categorized list of changes.
    """
    st.markdown("### 🔀 Manifest Diff")
    st.caption(
        "Upload a **before** and **after** `manifest.json` to see what "
        "changed — new models, dropped columns, renamed fields, broken deps."
    )

    cols = st.columns(2)
    with cols[0]:
        before_file = st.file_uploader(
            "Before (older manifest)",
            type=["json"],
            key="diff_before_uploader",
        )
    with cols[1]:
        after_file = st.file_uploader(
            "After (newer manifest)",
            type=["json"],
            key="diff_after_uploader",
        )

    before = _load_manifest_file(before_file)
    after = _load_manifest_file(after_file)

    if before is None or after is None:
        st.info("Upload both files to see the diff.")
        return

    diff = diff_manifests(before, after)

    # Summary
    summary_color = "#F85149" if diff.has_breaking_changes else "#39D353"
    st.markdown(
        f"""
        <div style="
            background: #0D1117;
            border: 1px solid {summary_color};
            border-radius: 8px;
            padding: 12px 16px;
            margin: 12px 0;
            font-family: 'Inter', sans-serif;
        ">
            <div style="font-size: 14px; font-weight: 600; color: #E6EDF3;">
                {diff.total_changes} change(s) detected
            </div>
            <div style="font-size: 12px; color: {summary_color}; margin-top: 4px;">
                {'⚠ Breaking changes present' if diff.has_breaking_changes else '✓ No breaking changes'}
            </div>
            <div style="font-size: 11px; color: #8B949E; margin-top: 4px;">
                +{len(diff.nodes_added)} added · -{len(diff.nodes_removed)} removed · ~{len(diff.nodes_modified)} modified
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Sections
    if diff.nodes_added:
        st.markdown("#### Added")
        for n in diff.nodes_added:
            _render_node_change(n, "+")

    if diff.nodes_removed:
        st.markdown("#### Removed")
        for n in diff.nodes_removed:
            _render_node_change(n, "−")

    if diff.nodes_modified:
        st.markdown("#### Modified")
        for n in diff.nodes_modified:
            _render_node_change(n, "~")

    if diff.total_changes == 0:
        st.success("No changes detected — manifests are functionally identical.")

    # Raw text option
    with st.expander("Raw text summary"):
        st.code(diff.to_text(), language="text")
