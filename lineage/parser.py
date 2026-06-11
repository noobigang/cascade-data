"""
dbt manifest.json parser — converts manifest nodes into LineageGraph TableNodes.
"""

from __future__ import annotations

import json
from pathlib import Path

from lineage.models import ColumnNode, LineageGraph, TableNode

# Resource types we surface in the lineage graph. dbt also emits test.* and
# metric.* nodes — they're metadata, not data, so we drop them.
_LINEAGE_RESOURCE_TYPES = frozenset({"model", "source", "seed", "snapshot"})


def _parse_resource_type(unique_id: str) -> str:
    """Extract resource type prefix from a dbt unique_id.

    Returns the prefix as-is (model/source/seed/snapshot/test/metric/...).
    Callers should filter against `_LINEAGE_RESOURCE_TYPES` to decide whether
    the node belongs in the lineage graph.
    """
    return unique_id.split(".")[0]


def _build_unique_id_table(manifest: dict) -> dict[str, dict]:
    """
    Build a lookup dict of unique_id -> node dict from the manifest.
    Also includes 'parent_map' references for depends_on resolution.
    """
    nodes = {}
    for uid, node in manifest.get("nodes", {}).items():
        nodes[uid] = node
    for uid, src in manifest.get("sources", {}).items():
        nodes[uid] = src
    return nodes


def _extract_columns_from_node(node_dict: dict) -> dict[str, ColumnNode]:
    """
    Extract column metadata from a manifest node dict.

    dbt manifest v5+ stores columns under 'columns' key as a dict of name -> col dict.
    """
    columns: dict[str, ColumnNode] = {}
    raw_cols = node_dict.get("columns", {})
    if isinstance(raw_cols, dict):
        for col_name, col_dict in raw_cols.items():
            if isinstance(col_dict, dict):
                columns[col_name] = ColumnNode(
                    name=col_name,
                    data_type=str(col_dict.get("data_type", "")),
                    description=str(col_dict.get("description", "")),
                    source_columns=[],
                )
    return columns


def _resolve_depends_on(node_dict: dict) -> list[str]:
    """
    Resolve the depends_on list from a manifest node.
    dbt stores depends_on as a nested object with 'nodes' list.
    """
    depends = node_dict.get("depends_on", {})
    if isinstance(depends, dict):
        return [str(n) for n in depends.get("nodes", [])]
    if isinstance(depends, list):
        return [str(n) for n in depends]
    return []


def parse_manifest(
    manifest_path: str | Path,
    catalog_path: str | Path | None = None,
) -> LineageGraph:
    """
    Parse a dbt manifest.json (and optional catalog.json) into a LineageGraph.

    Args:
        manifest_path: Path to manifest.json
        catalog_path: Optional path to catalog.json for enriched column metadata

    Returns:
        LineageGraph populated with TableNode objects
    """
    manifest_path = Path(manifest_path)
    with open(manifest_path, encoding="utf-8") as f:
        manifest: dict = json.load(f)

    # Load catalog for column descriptions/data types if provided
    catalog: dict[str, dict] = {}
    if catalog_path:
        catalog_path = Path(catalog_path)
        if catalog_path.exists():
            with open(catalog_path, encoding="utf-8") as f:
                catalog_raw: dict = json.load(f)
                # catalog stores nodes under 'nodes' and 'sources'
                catalog = {**catalog_raw.get("nodes", {}), **catalog_raw.get("sources", {})}

    # Build node lookup for depends_on resolution
    _build_unique_id_table(manifest)

    graph = LineageGraph()

    # Parse all nodes (models, seeds, snapshots)
    for uid, node_dict in manifest.get("nodes", {}).items():
        if _parse_resource_type(uid) not in _LINEAGE_RESOURCE_TYPES:
            continue
        _parse_node(uid, node_dict, catalog, graph)

    # Parse sources
    for uid, src_dict in manifest.get("sources", {}).items():
        if _parse_resource_type(uid) not in _LINEAGE_RESOURCE_TYPES:
            continue
        _parse_node(uid, src_dict, catalog, graph)

    # Build edges from depends_on
    for uid, node in graph._node_data.items():
        for dep in node.depends_on:
            if graph.has_node(dep):
                graph.add_edge(dep, uid)

    return graph


def _parse_node(
    uid: str,
    node_dict: dict,
    catalog: dict[str, dict],
    graph: LineageGraph,
) -> TableNode:
    """Parse a single manifest node dict into a TableNode."""
    resource_type = _parse_resource_type(uid)

    # Extract schema (database.schema or just schema)
    relation_name = node_dict.get("relation_name", "")
    schema = ""
    if "." in relation_name:
        parts = relation_name.split(".")
        if len(parts) >= 2:
            schema = parts[-2].strip('"[]`')

    name = node_dict.get("name", uid.split(".")[-1])
    description = str(node_dict.get("description", ""))
    raw_sql = str(node_dict.get("raw_code", node_dict.get("raw_sql", "")))
    compiled_sql = str(node_dict.get("compiled_code", node_dict.get("compiled_code", node_dict.get("compiled_sql", raw_sql))))

    # Extract columns
    columns = _extract_columns_from_node(node_dict)

    # Enrich from catalog if available
    cat_entry = catalog.get(uid)
    if cat_entry:
        cat_cols = cat_entry.get("columns", {})
        if isinstance(cat_cols, dict):
            for col_name, col_info in cat_cols.items():
                if col_name in columns:
                    col = columns[col_name]
                    if not col.data_type and col_info.get("data_type"):
                        col.data_type = str(col_info["data_type"])
                    if not col.description and col_info.get("description"):
                        col.description = str(col_info["description"])
                else:
                    columns[col_name] = ColumnNode(
                        name=col_name,
                        data_type=str(col_info.get("data_type", "")),
                        description=str(col_info.get("description", "")),
                        source_columns=[],
                    )

    depends_on = _resolve_depends_on(node_dict)

    table_node = TableNode(
        unique_id=uid,
        name=name,
        schema=schema,
        resource_type=resource_type,
        columns=columns,
        depends_on=depends_on,
        description=description,
        raw_sql=raw_sql,
        compiled_sql=compiled_sql,
    )

    graph.add_node(table_node)
    return table_node


def parse_manifest_from_dict(manifest: dict, catalog: dict | None = None) -> LineageGraph:
    """
    Parse a manifest dict (already loaded as Python object) into a LineageGraph.
    Useful for programmatic use without file I/O.
    """
    graph = LineageGraph()
    catalog_lookup: dict[str, dict] = {}

    if catalog:
        catalog_lookup = {**catalog.get("nodes", {}), **catalog.get("sources", {})}

    # Parse nodes
    for uid, node_dict in manifest.get("nodes", {}).items():
        if _parse_resource_type(uid) not in _LINEAGE_RESOURCE_TYPES:
            continue
        _parse_node(uid, node_dict, catalog_lookup, graph)

    for uid, src_dict in manifest.get("sources", {}).items():
        if _parse_resource_type(uid) not in _LINEAGE_RESOURCE_TYPES:
            continue
        _parse_node(uid, src_dict, catalog_lookup, graph)

    # Build edges
    for uid, node in graph._node_data.items():
        for dep in node.depends_on:
            if graph.has_node(dep):
                graph.add_edge(dep, uid)

    return graph
