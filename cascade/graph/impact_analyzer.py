"""
impact_analyzer.py — Blast-radius analysis for Cascade lineage graph.

Provides:
- get_downstream_nodes: BFS to find all downstream models
- get_upstream_nodes: reverse BFS to find all upstream models
- get_downstream_columns: column-level downstream traversal
- get_upstream_columns: column-level upstream traversal
- blast_radius_score: count terminal downstream -> LOW/MEDIUM/HIGH
- get_column_lineage: trace full column lineage path
"""

import warnings
from collections import deque

import networkx as nx


def get_downstream_nodes(graph: nx.DiGraph, node_id: str) -> list[str]:
    """
    Find all downstream models reachable from the given node using BFS.

    Args:
        graph: NetworkX DiGraph from build_lineage_graph
        node_id: Source node unique_id

    Returns:
        List of all downstream node unique_ids (excluding the source itself).
        Returns empty list if node_id not in graph.

    Example:
        >>> downstream = get_downstream_nodes(graph, "model.my_project.customers")
        >>> print(f"{len(downstream)} models depend on customers")
    """
    if node_id not in graph:
        warnings.warn(f"Node not found in graph: {node_id}", stacklevel=2)
        return []

    visited = set()
    queue = deque([node_id])

    while queue:
        current = queue.popleft()
        for successor in graph.successors(current):
            if successor not in visited:
                visited.add(successor)
                queue.append(successor)

    # Remove source node from result
    visited.discard(node_id)
    return list(visited)


def get_upstream_nodes(graph: nx.DiGraph, node_id: str) -> list[str]:
    """
    Find all upstream models that feed into the given node using reverse BFS.

    Args:
        graph: NetworkX DiGraph from build_lineage_graph
        node_id: Target node unique_id

    Returns:
        List of all upstream node unique_ids (excluding the source itself).
        Returns empty list if node_id not in graph.

    Example:
        >>> upstream = get_upstream_nodes(graph, "model.my_project.customers")
        >>> print(f"customers has {len(upstream)} upstream dependencies")
    """
    if node_id not in graph:
        warnings.warn(f"Node not found in graph: {node_id}", stacklevel=2)
        return []

    visited = set()
    queue = deque([node_id])

    while queue:
        current = queue.popleft()
        for predecessor in graph.predecessors(current):
            if predecessor not in visited:
                visited.add(predecessor)
                queue.append(predecessor)

    # Remove source node from result
    visited.discard(node_id)
    return list(visited)


def get_downstream_columns(
    graph: nx.DiGraph, node_id: str, column_name: str
) -> list[str]:
    """
    Find all downstream column references for a specific column.

    Traverses the graph and finds all downstream columns that share
    the same column name (matched by name, not by explicit lineage).

    Args:
        graph: NetworkX DiGraph from build_lineage_graph
        node_id: Starting node unique_id
        column_name: Column name to trace

    Returns:
        List of downstream column refs in format "node_id.column_name".
        Returns empty list if node_id not found or column doesn't exist.

    Example:
        >>> cols = get_downstream_columns(graph, "model.my_project.raw_users", "user_id")
        >>> print(f"user_id flows to: {cols}")
    """
    if node_id not in graph:
        warnings.warn(f"Node not found in graph: {node_id}", stacklevel=2)
        return []

    downstream = []
    visited = set()
    queue = deque([node_id])

    while queue:
        current = queue.popleft()
        for successor in graph.successors(current):
            if successor in visited:
                continue
            visited.add(successor)

            # Check if this node has the column
            cols = graph.nodes[successor].get("columns", {})
            if column_name in cols:
                downstream.append(f"{successor}.{column_name}")

            queue.append(successor)

    return downstream


def get_upstream_columns(
    graph: nx.DiGraph, node_id: str, column_name: str
) -> list[str]:
    """
    Find all upstream column sources for a specific column.

    Traverses the graph in reverse and finds all upstream columns
    that share the same column name.

    Args:
        graph: NetworkX DiGraph from build_lineage_graph
        node_id: Target node unique_id
        column_name: Column name to trace

    Returns:
        List of upstream column refs in format "node_id.column_name".
        Returns empty list if node_id not found or column doesn't exist.

    Example:
        >>> cols = get_upstream_columns(graph, "model.my_project.customers", "user_id")
        >>> print(f"user_id originates from: {cols}")
    """
    if node_id not in graph:
        warnings.warn(f"Node not found in graph: {node_id}", stacklevel=2)
        return []

    upstream = []
    visited = set()
    queue = deque([node_id])

    while queue:
        current = queue.popleft()
        for predecessor in graph.predecessors(current):
            if predecessor in visited:
                continue
            visited.add(predecessor)

            # Check if this node has the column
            cols = graph.nodes[predecessor].get("columns", {})
            if column_name in cols:
                upstream.append(f"{predecessor}.{column_name}")

            queue.append(predecessor)

    return upstream


def blast_radius_score(graph: nx.DiGraph, node_id: str) -> str:
    """
    Calculate the blast radius risk score for a node.

    Counts terminal downstream nodes (models with no further downstream
    dependents) and returns a risk category:

    - LOW: 1-3 terminal downstream nodes
    - MEDIUM: 4-20 terminal downstream nodes
    - HIGH: 20+ terminal downstream nodes

    Terminal nodes represent the "end of the line" — dashboards, reports,
    or final tables that would break if this model changes.

    Args:
        graph: NetworkX DiGraph from build_lineage_graph
        node_id: Node to analyze

    Returns:
        "LOW", "MEDIUM", or "HIGH"
        Returns "UNKNOWN" if node not found.

    Example:
        >>> score = blast_radius_score(graph, "model.my_project.raw_users")
        >>> print(f"Blast radius: {score}")
    """
    if node_id not in graph:
        warnings.warn(f"Node not found in graph: {node_id}", stacklevel=2)
        return "UNKNOWN"

    all_downstream = get_downstream_nodes(graph, node_id)

    if not all_downstream:
        # No downstream at all — low blast radius
        return "LOW"

    # Count terminal nodes (nodes with out_degree == 0, excluding source)
    terminal_count = sum(
        1 for node in all_downstream if graph.out_degree(node) == 0
    )

    if terminal_count <= 3:
        return "LOW"
    elif terminal_count <= 20:
        return "MEDIUM"
    else:
        return "HIGH"


def get_column_lineage(
    graph: nx.DiGraph, node_id: str, column_name: str
) -> dict | None:
    """
    Trace the full lineage path for a specific column.

    Returns a structured dict with:
    - upstream: list of all upstream columns feeding this one
    - downstream: list of all downstream columns that depend on this one
    - path: the traversal path (for visualization)

    Args:
        graph: NetworkX DiGraph from build_lineage_graph
        node_id: Starting node unique_id
        column_name: Column name to trace

    Returns:
        Dict with keys: upstream (list), downstream (list), path (list of node_ids),
        or None if node not found.

    Example:
        >>> lineage = get_column_lineage(graph, "model.my_project.raw_users", "user_id")
        >>> print(f"Upstream sources: {lineage['upstream']}")
        >>> print(f"Downstream dependents: {lineage['downstream']}")
    """
    if node_id not in graph:
        warnings.warn(f"Node not found in graph: {node_id}", stacklevel=2)
        return None

    upstream = get_upstream_columns(graph, node_id, column_name)
    downstream = get_downstream_columns(graph, node_id, column_name)

    # Build path: trace all ancestors and descendants
    path = [node_id]
    visited = {node_id}

    # Walk upstream
    queue = deque([node_id])
    while queue:
        current = queue.popleft()
        for predecessor in graph.predecessors(current):
            if predecessor not in visited:
                visited.add(predecessor)
                path.append(predecessor)
                queue.append(predecessor)

    # Walk downstream
    queue = deque([node_id])
    while queue:
        current = queue.popleft()
        for successor in graph.successors(current):
            if successor not in visited:
                visited.add(successor)
                path.append(successor)
                queue.append(successor)

    return {
        "upstream": upstream,
        "downstream": downstream,
        "path": path,
    }


def get_impact_summary(graph: nx.DiGraph, node_id: str) -> dict | None:
    """
    Get a full impact summary for a node — upstream/downstream counts,
    blast radius score, and column-level summary.

    Args:
        graph: NetworkX DiGraph from build_lineage_graph
        node_id: Node to analyze

    Returns:
        Dict with: node_id, upstream_count, downstream_count,
        terminal_downstream, blast_radius, columns (with upstream/downstream per column),
        or None if node not found.
    """
    if node_id not in graph:
        warnings.warn(f"Node not found in graph: {node_id}", stacklevel=2)
        return None

    upstream_nodes = get_upstream_nodes(graph, node_id)
    downstream_nodes = get_downstream_nodes(graph, node_id)
    terminal_count = sum(
        1 for n in downstream_nodes if graph.out_degree(n) == 0
    )
    blast = blast_radius_score(graph, node_id)

    # Per-column summary
    node_cols = graph.nodes[node_id].get("columns", {})
    column_summary = {}
    for col_name in node_cols:
        col_up = get_upstream_columns(graph, node_id, col_name)
        col_down = get_downstream_columns(graph, node_id, col_name)
        column_summary[col_name] = {
            "upstream": col_up,
            "downstream": col_down,
            "upstream_count": len(col_up),
            "downstream_count": len(col_down),
        }

    return {
        "node_id": node_id,
        "node_name": graph.nodes[node_id].get("name", ""),
        "resource_type": graph.nodes[node_id].get("resource_type", ""),
        "upstream_count": len(upstream_nodes),
        "upstream_nodes": upstream_nodes,
        "downstream_count": len(downstream_nodes),
        "downstream_nodes": downstream_nodes,
        "terminal_downstream": terminal_count,
        "blast_radius": blast,
        "columns": column_summary,
    }


# ---- Simple test ----
if __name__ == "__main__":
    from cascade.graph.lineage_graph import build_lineage_graph
    from cascade.parser.manifest_parser import parse_manifest_from_dict

    # Build a mini graph
    dummy_manifest = {
        "nodes": {
            "source.my_project.raw_source": {
                "unique_id": "source.my_project.raw_source",
                "name": "raw_source",
                "resource_type": "source",
                "schema": "public",
                "description": "DB source",
                "columns": {"user_id": {"dtype": "int"}},
                "depends_on": {"nodes": []},
            },
            "model.my_project.raw_users": {
                "unique_id": "model.my_project.raw_users",
                "name": "raw_users",
                "resource_type": "model",
                "schema": "staging",
                "description": "Raw users",
                "columns": {"user_id": {"dtype": "int"}},
                "depends_on": {"nodes": ["source.my_project.raw_source"]},
            },
            "model.my_project.customers": {
                "unique_id": "model.my_project.customers",
                "name": "customers",
                "resource_type": "model",
                "schema": "analytics",
                "description": "Cleaned customers",
                "columns": {"user_id": {"dtype": "int"}, "name": {"dtype": "varchar"}},
                "depends_on": {"nodes": ["model.my_project.raw_users"]},
            },
            "model.my_project.reports": {
                "unique_id": "model.my_project.reports",
                "name": "reports",
                "resource_type": "model",
                "schema": "reporting",
                "description": "Final report",
                "columns": {"user_id": {"dtype": "int"}},
                "depends_on": {"nodes": ["model.my_project.customers"]},
            },
        }
    }

    nodes = parse_manifest_from_dict(dummy_manifest)
    graph = build_lineage_graph(nodes)

    # Test blast radius
    score = blast_radius_score(graph, "model.my_project.raw_users")
    print(f"raw_users blast radius: {score} (expected MEDIUM, 2 terminal)")

    # Test downstream
    down = get_downstream_nodes(graph, "model.my_project.raw_users")
    print(f"raw_users downstream: {down} (expected 2: customers, reports)")

    # Test upstream
    up = get_upstream_nodes(graph, "model.my_project.reports")
    print(f"reports upstream: {up} (expected 3: customers, raw_users, raw_source)")

    # Test column lineage
    lineage = get_column_lineage(graph, "model.my_project.customers", "user_id")
    print(f"customers.user_id lineage: upstream={lineage['upstream']}, downstream={lineage['downstream']}")  # type: ignore[index]

    # Test impact summary
    summary = get_impact_summary(graph, "model.my_project.customers")
    print(f"customers impact: {summary['blast_radius']}, {summary['downstream_count']} downstream, {summary['upstream_count']} upstream")  # type: ignore[index]

    print("\nimpact_analyzer.py smoke test passed.")
