"""
Impact analysis for the lineage graph.

Provides functions to:
- Get all downstream/upstream nodes from any given node
- Trace column-level impact through the graph
- Score the blast radius of changes
- Generate full text impact reports
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from lineage.models import LineageGraph


@dataclass
class ImpactScore:
    """Risk score for a node based on its blast radius."""
    level: str  # LOW | MEDIUM | HIGH | CRITICAL
    downstream_count: int
    upstream_count: int
    total_affected: int

    def __str__(self) -> str:
        return self.level


def get_downstream(node_uid: str, graph: LineageGraph) -> list[str]:
    """
    Get all nodes that depend on (are downstream of) the given node.
    Uses BFS to traverse the graph.

    Args:
        node_uid: The unique_id of the starting node
        graph: The LineageGraph to traverse

    Returns:
        List of downstream unique_ids (excluding the starting node)
    """
    if not graph.has_node(node_uid):
        return []

    downstream: list[str] = []
    queue = deque(graph.successors(node_uid))

    while queue:
        current = queue.popleft()
        if current not in downstream:
            downstream.append(current)
            queue.extend(graph.successors(current))

    return downstream


def get_upstream(node_uid: str, graph: LineageGraph) -> list[str]:
    """
    Get all nodes that the given node depends on (upstream).
    Uses BFS to traverse the graph.

    Args:
        node_uid: The unique_id of the starting node
        graph: The LineageGraph to traverse

    Returns:
        List of upstream unique_ids (excluding the starting node)
    """
    if not graph.has_node(node_uid):
        return []

    upstream: list[str] = []
    queue = deque(graph.predecessors(node_uid))

    while queue:
        current = queue.popleft()
        if current not in upstream:
            upstream.append(current)
            queue.extend(graph.predecessors(current))

    return upstream


def get_column_impact(
    node_uid: str,
    column_name: str,
    graph: LineageGraph,
) -> list[tuple[str, str]]:
    """
    Get all (table_uid, column_name) pairs affected by a change to
    the specified column in the given table.

    Args:
        node_uid: The unique_id of the table containing the changed column
        column_name: The name of the changed column
        graph: The LineageGraph to traverse

    Returns:
        List of (affected_table_uid, affected_column) tuples
    """
    if not graph.has_node(node_uid):
        return []

    affected: list[tuple[str, str]] = []
    downstream = get_downstream(node_uid, graph)

    for ds_uid in downstream:
        node = graph.get_node(ds_uid)
        if not node:
            continue

        # Check if this column flows through via column_deps
        if column_name in node.column_deps:
            for (src_table, src_col) in node.column_deps[column_name]:
                if src_col == column_name and src_table == node_uid:
                    for col_name, col_node in node.columns.items():
                        if column_name in col_node.source_columns or src_col in col_node.source_columns:
                            if (ds_uid, col_name) not in affected:
                                affected.append((ds_uid, col_name))

        # Also check if the column is in the node's column list
        if column_name in node.columns:
            col = node.columns[column_name]
            if any(column_name in src for src in col.source_columns):
                if (ds_uid, column_name) not in affected:
                    affected.append((ds_uid, column_name))

    return affected


def blast_radius_score(node_uid: str, graph: LineageGraph) -> ImpactScore:
    """
    Calculate the blast radius score for a node.

    Scoring:
    - LOW: 1-2 downstream nodes
    - MEDIUM: 3-7 downstream nodes
    - HIGH: 8-20 downstream nodes
    - CRITICAL: 21+ downstream nodes

    Args:
        node_uid: The unique_id of the node to score
        graph: The LineageGraph

    Returns:
        ImpactScore with level and counts
    """
    if not graph.has_node(node_uid):
        return ImpactScore(level="LOW", downstream_count=0, upstream_count=0, total_affected=0)

    downstream = get_downstream(node_uid, graph)
    upstream = get_upstream(node_uid, graph)

    count = len(downstream)

    if count >= 21:
        level = "CRITICAL"
    elif count >= 8:
        level = "HIGH"
    elif count >= 3:
        level = "MEDIUM"
    else:
        level = "LOW"

    return ImpactScore(
        level=level,
        downstream_count=len(downstream),
        upstream_count=len(upstream),
        total_affected=count,
    )


def generate_impact_report(
    node_uid: str,
    graph: LineageGraph,
    column_name: str | None = None,
) -> str:
    """
    Generate a full text impact report for a node.

    Args:
        node_uid: The unique_id of the node to analyze
        graph: The LineageGraph
        column_name: Optional column name to focus the report on

    Returns:
        Formatted text report
    """
    node = graph.get_node(node_uid)
    if not node:
        return f"Node '{node_uid}' not found in graph."

    downstream = get_downstream(node_uid, graph)
    upstream = get_upstream(node_uid, graph)
    score = blast_radius_score(node_uid, graph)

    lines: list[str] = []
    lines.append("=== Impact Analysis Report ===")
    lines.append(f"Node: {node_uid}")
    lines.append(f"Name: {node.name}")
    lines.append(f"Type: {node.resource_type}")
    lines.append(f"Schema: {node.schema}")
    if node.description:
        lines.append(f"Description: {node.description}")
    lines.append("")
    lines.append("--- Blast Radius ---")
    lines.append(f"Risk Level: {score.level}")
    lines.append(f"Downstream nodes: {score.downstream_count}")
    lines.append(f"Upstream nodes: {score.upstream_count}")
    lines.append("")

    # List downstream tables
    if downstream:
        lines.append("--- Affected Tables (Downstream) ---")
        for ds_uid in downstream:
            ds_node = graph.get_node(ds_uid)
            if ds_node:
                col_count = len(ds_node.columns)
                deps = len(ds_node.depends_on)
                lines.append(f"  • {ds_uid} ({ds_node.resource_type})")
                lines.append(f"    Columns: {col_count} | Dependencies: {deps}")
                if ds_node.description:
                    lines.append(f"    {ds_node.description}")
    else:
        lines.append("--- Affected Tables (Downstream) ---")
        lines.append("  None (this is a source or leaf node)")

    # List upstream tables
    if upstream:
        lines.append("")
        lines.append("--- Source Tables (Upstream) ---")
        for up_uid in upstream:
            up_node = graph.get_node(up_uid)
            if up_node:
                lines.append(f"  • {up_uid} ({up_node.resource_type})")
                if up_node.description:
                    lines.append(f"    {up_node.description}")

    # Column-level impact
    if column_name:
        lines.append("")
        lines.append(f"--- Column-Level Impact: {column_name} ---")
        col_impact = get_column_impact(node_uid, column_name, graph)
        if col_impact:
            for (t_uid, col) in col_impact:
                lines.append(f"  • {t_uid}.{col}")
        else:
            lines.append("  No downstream column impact detected.")

    # SQL snippet
    if node.compiled_sql:
        lines.append("")
        lines.append("--- Compiled SQL ---")
        # Show first 500 chars
        sql_preview = node.compiled_sql[:500]
        if len(node.compiled_sql) > 500:
            sql_preview += "\n... (truncated)"
        lines.append(sql_preview)

    lines.append("")
    lines.append(f"Report generated for: {node_uid}")

    return "\n".join(lines)


def get_all_column_impacts(
    node_uid: str,
    graph: LineageGraph,
) -> dict[str, list[tuple[str, str]]]:
    """
    Get column-level impact for all columns in a table.

    Returns:
        Dict mapping column_name -> list of (affected_table, affected_column)
    """
    node = graph.get_node(node_uid)
    if not node:
        return {}

    result: dict[str, list[tuple[str, str]]] = {}
    for col_name in node.columns:
        impact = get_column_impact(node_uid, col_name, graph)
        if impact:
            result[col_name] = impact

    return result


def get_most_connected_nodes(graph: LineageGraph, top_n: int = 10) -> list[tuple[str, int]]:
    """
    Return the top N most connected nodes (by total degree).

    Returns:
        List of (unique_id, degree) tuples, sorted descending
    """
    degrees = []
    for uid in graph.nodes:
        degree = graph.graph.degree(uid)
        degrees.append((uid, degree))
    degrees.sort(key=lambda x: x[1], reverse=True)
    return degrees[:top_n]


def get_deepest_lineage_path(graph: LineageGraph) -> list[str]:
    """
    Find the longest path in the DAG (topological sort longest chain).

    Returns:
        List of unique_ids representing the deepest lineage path
    """
    if not graph.nodes:
        return []

    try:
        # Find the longest path using topological sort
        for uid in graph.nodes:
            node = graph.get_node(uid)
            if node and node.resource_type == "source" and not graph.predecessors(uid):
                # Start from a root source
                path = _longest_path_from(uid, graph)
                if path:
                    return path
    except Exception:
        pass

    # Fallback: use ancestors/descendants for each source node
    longest = []
    for uid in graph.nodes:
        node = graph.get_node(uid)
        if node and node.resource_type == "source":
            desc = graph.descendants(uid)
            path_len = len(desc)
            if path_len > len(longest):
                longest = list(desc)
    return longest[:10]


def _longest_path_from(start_uid: str, graph: LineageGraph) -> list[str]:
    """Find the longest downstream path starting from a node."""
    longest = []
    stack = [(start_uid, [start_uid])]

    while stack:
        current, path = stack.pop()
        successors = graph.successors(current)
        if not successors:
            if len(path) > len(longest):
                longest = path
        else:
            for s in successors:
                if s not in path:  # Avoid cycles
                    stack.append((s, path + [s]))

    return longest
