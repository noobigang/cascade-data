"""
lineage_graph.py — Build a NetworkX DiGraph from parsed ModelNode objects.

Provides:
- Graph construction from ModelNode list
- Node and edge attributes (column info, resource type)
- Both model-level and column-level graph support
"""

import warnings

import networkx as nx

from cascade.parser.manifest_parser import ModelNode


def build_lineage_graph(nodes: list[ModelNode]) -> nx.DiGraph:
    """
    Build a directed graph from a list of ModelNode objects.

    Each node in the graph corresponds to a dbt model/source/seed.
    Edges represent parent -> child relationships (from depends_on).

    Node attributes stored:
        - name: model name
        - unique_id: dbt unique_id
        - resource_type: model / source / seed
        - schema: target schema
        - description: model description
        - columns: dict of column_name -> ColumnInfo
        - upstream_columns: dict mapping column_name -> [parent_column_names]
        - downstream_columns: dict mapping column_name -> [child_column_names]

    Args:
        nodes: List of ModelNode objects from manifest_parser

    Returns:
        NetworkX DiGraph with nodes and edges configured

    Example:
        >>> from cascade.parser.manifest_parser import parse_manifest
        >>> from cascade.graph.lineage_graph import build_lineage_graph
        >>> nodes = parse_manifest("target/manifest.json")
        >>> graph = build_lineage_graph(nodes)
        >>> print(f"Graph has {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges")
    """
    graph: nx.DiGraph = nx.DiGraph()

    # Add all nodes first
    node_map = {}  # unique_id -> ModelNode for quick lookup
    for node in nodes:
        graph.add_node(
            node.unique_id,
            name=node.name,
            unique_id=node.unique_id,
            resource_type=node.resource_type,
            schema=node.schema,
            description=node.description,
            columns=node.columns,
            depends_on=node.depends_on,
            upstream_columns={},  # col_name -> [parent_col_names]
            downstream_columns={},  # col_name -> [child_col_names]
        )
        node_map[node.unique_id] = node

    # Add edges (parent -> child), i.e., if node A depends on node B, B -> A
    for node in nodes:
        for parent_id in node.depends_on:
            if parent_id in node_map or parent_id in graph:
                # parent -> child direction (upstream feeds downstream)
                graph.add_edge(parent_id, node.unique_id)

    # Build column-level edges
    _build_column_edges(graph, node_map)

    return graph


def _build_column_edges(graph: nx.DiGraph, node_map: dict) -> None:
    """
    Populate upstream_columns and downstream_columns for each node in the graph.

    For each edge parent -> child, match columns by name and record the relationship.
    """
    for parent_id, child_id in graph.edges():
        parent_node = node_map.get(parent_id)
        child_node = node_map.get(child_id)

        if parent_node is None or child_node is None:
            warnings.warn(
                f"Edge references missing node: {parent_id} -> {child_id}", stacklevel=2
            )
            continue

        # Find matching column names
        parent_cols = set(parent_node.columns.keys())
        child_cols = set(child_node.columns.keys())
        common_cols = parent_cols & child_cols

        for col_name in common_cols:
            # Record upstream: child_col has parent_col as upstream
            upstream = graph.nodes[child_id]["upstream_columns"]
            if col_name not in upstream:
                upstream[col_name] = []
            upstream[col_name].append(f"{parent_id}.{col_name}")

            # Record downstream: parent_col has child_col as downstream
            downstream = graph.nodes[parent_id]["downstream_columns"]
            if col_name not in downstream:
                downstream[col_name] = []
            downstream[col_name].append(f"{child_id}.{col_name}")


def add_column_edges(graph: nx.DiGraph, source_id: str, target_id: str,
                     source_col: str, target_col: str) -> None:
    """
    Manually add a column-level edge to the graph.

    Use this when you have explicit column-level refs not captured by name matching.
    """
    if source_id not in graph or target_id not in graph:
        warnings.warn(f"Cannot add column edge: node not found ({source_id} -> {target_id})", stacklevel=2)
        return

    upstream = graph.nodes[target_id]["upstream_columns"]
    if target_col not in upstream:
        upstream[target_col] = []
    upstream[target_col].append(f"{source_id}.{source_col}")

    downstream = graph.nodes[source_id]["downstream_columns"]
    if source_col not in downstream:
        downstream[source_col] = []
    downstream[source_col].append(f"{target_id}.{target_col}")


def get_node_columns(graph: nx.DiGraph, node_id: str) -> dict:
    """Return the columns dict for a node, or empty dict if node not found."""
    if node_id not in graph:
        return {}
    return graph.nodes[node_id].get("columns", {})  # type: ignore[no-any-return]


def get_upstream_columns(graph: nx.DiGraph, node_id: str, column_name: str) -> list:
    """Return list of upstream column refs for a specific column."""
    if node_id not in graph:
        return []
    return graph.nodes[node_id].get("upstream_columns", {}).get(column_name, [])  # type: ignore[no-any-return]


def get_downstream_columns(graph: nx.DiGraph, node_id: str, column_name: str) -> list:
    """Return list of downstream column refs for a specific column."""
    if node_id not in graph:
        return []
    return graph.nodes[node_id].get("downstream_columns", {}).get(column_name, [])  # type: ignore[no-any-return]


def graph_stats(graph: nx.DiGraph) -> dict:
    """Return a dict of basic graph statistics."""
    return {
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "models": sum(1 for n in graph.nodes() if graph.nodes[n].get("resource_type") == "model"),
        "sources": sum(1 for n in graph.nodes() if graph.nodes[n].get("resource_type") == "source"),
        "seeds": sum(1 for n in graph.nodes() if graph.nodes[n].get("resource_type") == "seed"),
        "terminal_nodes": len([n for n in graph.nodes() if graph.out_degree(n) == 0]),
        "root_nodes": len([n for n in graph.nodes() if graph.in_degree(n) == 0]),
    }


# ---- Simple test ----
if __name__ == "__main__":
    from cascade.parser.manifest_parser import ModelNode, parse_manifest_from_dict

    # Build a mini graph from dummy data
    dummy_manifest = {
        "nodes": {
            "model.my_project.raw_users": {
                "unique_id": "model.my_project.raw_users",
                "name": "raw_users",
                "resource_type": "model",
                "schema": "staging",
                "description": "Raw users table",
                "columns": {"user_id": {"dtype": "int", "description": "User ID"}},
                "depends_on": {"nodes": ["source.my_project.raw_source"]},
            },
            "model.my_project.customers": {
                "unique_id": "model.my_project.customers",
                "name": "customers",
                "resource_type": "model",
                "schema": "analytics",
                "description": "Cleaned customers",
                "columns": {"user_id": {"dtype": "int", "description": "User ID"}, "name": {"dtype": "varchar"}},
                "depends_on": {"nodes": ["model.my_project.raw_users"]},
            },
            "source.my_project.raw_source": {
                "unique_id": "source.my_project.raw_source",
                "name": "raw_source",
                "resource_type": "source",
                "schema": "public",
                "description": "DB source",
                "columns": {"user_id": {"dtype": "int"}},
                "depends_on": {"nodes": []},
            },
        }
    }
    nodes = parse_manifest_from_dict(dummy_manifest)
    graph = build_lineage_graph(nodes)

    stats = graph_stats(graph)
    print(f"Graph: {stats['nodes']} nodes, {stats['edges']} edges")
    print(f"  Models: {stats['models']}, Sources: {stats['sources']}, Seeds: {stats['seeds']}")
    print(f"  Terminal: {stats['terminal_nodes']}, Root: {stats['root_nodes']}")

    # Check column edges
    customers_cols = get_downstream_columns(graph, "model.my_project.raw_users", "user_id")
    print(f"  raw_users.user_id downstream: {customers_cols}")

    print("lineage_graph.py smoke test passed.")
