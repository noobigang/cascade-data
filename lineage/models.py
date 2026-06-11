"""
Core data models for the column-level lineage extraction engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import networkx as nx


@dataclass
class ColumnNode:
    """
    Represents a single column in a table.

    Attributes:
        name: Column name (e.g., 'customer_id', 'order_total')
        data_type: SQL data type (e.g., 'VARCHAR', 'INTEGER', 'TIMESTAMP')
        description: Human-readable description of the column
        source_columns: List of source column names this column is derived from
    """
    name: str
    data_type: str = ""
    description: str = ""
    source_columns: list[str] = field(default_factory=list)


@dataclass
class TableNode:
    """
    Represents a table (model, source, seed, or snapshot) in the lineage graph.

    Attributes:
        unique_id: dbt unique_id (e.g., 'model.my_project.dim_customers')
        name: Short table name (e.g., 'dim_customers')
        schema: Schema/database name (e.g., 'analytics', 'raw')
        resource_type: One of 'model', 'source', 'seed', 'snapshot'
        columns: Dict of column_name -> ColumnNode
        depends_on: List of unique_ids this table depends on
        description: Human-readable description
        raw_sql: Original SQL before compilation
        compiled_sql: Compiled SQL from dbt
    """
    unique_id: str
    name: str
    schema: str = ""
    resource_type: str = "model"
    columns: dict[str, ColumnNode] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    description: str = ""
    raw_sql: str = ""
    compiled_sql: str = ""
    # column-level lineage: target_column -> list of (source_table, source_column)
    column_deps: dict[str, list[tuple[str, str]]] = field(default_factory=dict)

    def add_column(self, col: ColumnNode) -> None:
        self.columns[col.name] = col

    def __repr__(self) -> str:
        return f"TableNode({self.resource_type}.{self.name})"


@dataclass
class ColumnLineage:
    """
    Represents a single column-to-column lineage relationship.

    Attributes:
        source_column: Fully qualified source column (e.g., 'raw_customers.customer_id')
        target_column: Fully qualified target column (e.g., 'dim_customers.customer_id')
        transformation: SQL expression or description of the transformation
    """
    source_column: str
    target_column: str
    transformation: str = ""


class LineageGraph:
    """
    Wraps a NetworkX DiGraph with helper methods for lineage operations.

    Nodes: unique_id strings
    Edges: dependency relationships (source -> target means source is upstream of target)
    """

    def __init__(self) -> None:
        self._graph: nx.DiGraph = nx.DiGraph()
        self._node_data: dict[str, TableNode] = {}

    def add_node(self, node: TableNode) -> None:
        """Add a table node to the graph."""
        self._graph.add_node(node.unique_id)
        self._node_data[node.unique_id] = node

    def add_edge(self, source: str, target: str) -> None:
        """Add a dependency edge (source is upstream of target)."""
        self._graph.add_edge(source, target)

    def get_node(self, unique_id: str) -> TableNode | None:
        """Get a table node by its unique_id."""
        return self._node_data.get(unique_id)

    def has_node(self, unique_id: str) -> bool:
        return unique_id in self._node_data

    def remove_node(self, unique_id: str) -> None:
        """Remove a node and all its edges."""
        if unique_id in self._node_data:
            del self._node_data[unique_id]
        self._graph.remove_node(unique_id)

    def predecessors(self, unique_id: str) -> list[str]:
        """Get direct upstream dependencies (predecessors in DAG).

        Returns an empty list if the node isn't in the graph, rather than
        raising — this matches the contract of get_upstream/get_downstream
        in lineage.impact and keeps callers from having to guard.
        """
        if unique_id not in self._node_data:
            return []
        return list(self._graph.predecessors(unique_id))

    def successors(self, unique_id: str) -> list[str]:
        """Get direct downstream dependents (successors in DAG).

        Returns an empty list if the node isn't in the graph.
        """
        if unique_id not in self._node_data:
            return []
        return list(self._graph.successors(unique_id))

    def ancestors(self, unique_id: str) -> set[str]:
        """Get all ancestors (full upstream tree)."""
        return nx.ancestors(self._graph, unique_id)

    def descendants(self, unique_id: str) -> set[str]:
        """Get all descendants (full downstream tree)."""
        return nx.descendants(self._graph, unique_id)

    @property
    def nodes(self) -> list[str]:
        """All node unique_ids."""
        return list(self._graph.nodes())

    @property
    def edges(self) -> list[tuple[str, str]]:
        """All directed edges as (source, target) tuples."""
        return list(self._graph.edges())

    @property
    def graph(self) -> nx.DiGraph:
        """Expose the underlying NetworkX graph for advanced operations."""
        return self._graph

    def subgraph(self, node_ids: set[str]) -> LineageGraph:
        """Return a new LineageGraph containing only the specified nodes."""
        sub = LineageGraph()
        subgraph_view = self._graph.subgraph(node_ids)
        for nid in subgraph_view.nodes:
            sub.add_node(self._node_data[nid])
        for src, tgt in subgraph_view.edges:
            sub.add_edge(src, tgt)
        return sub

    def filter_by_type(self, resource_type: str) -> LineageGraph:
        """Return a new LineageGraph containing only nodes of the given type."""
        filtered = {
            nid for nid, node in self._node_data.items()
            if node.resource_type == resource_type
        }
        return self.subgraph(filtered)

    def filter_by_schema(self, schema: str) -> LineageGraph:
        """Return a new LineageGraph containing only nodes in the given schema."""
        filtered = {
            nid for nid, node in self._node_data.items()
            if node.schema == schema
        }
        return self.subgraph(filtered)

    def search(self, query: str) -> list[TableNode]:
        """Full-text search across node names and column names."""
        query_lower = query.lower()
        results: list[TableNode] = []
        for node in self._node_data.values():
            if query_lower in node.name.lower():
                results.append(node)
                continue
            if query_lower in node.description.lower():
                results.append(node)
                continue
            for col in node.columns.values():
                if query_lower in col.name.lower() or query_lower in col.description.lower():
                    results.append(node)
                    break
        return results

    def __len__(self) -> int:
        return len(self._graph)

    def __repr__(self) -> str:
        return f"LineageGraph(nodes={len(self)}, edges={len(self._graph.edges())})"
