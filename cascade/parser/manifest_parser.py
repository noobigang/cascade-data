"""
manifest_parser.py — Parse dbt manifest.json into ModelNode dataclasses.

Extracts:
- All nodes with resource_type in (model, source, seed)
- Each node's columns dict (name -> {dtype, description, tests})
- Each node's depends_on (list of parent node unique_ids)
- Builds a flat list of ModelNode dataclasses
"""

import json
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Allowed resource types for Cascade
ALLOWED_RESOURCE_TYPES = {"model", "source", "seed"}


@dataclass
class ColumnInfo:
    """Column metadata from a dbt manifest node."""
    name: str
    dtype: str | None = None
    description: str | None = None
    tests: list = field(default_factory=list)

    @classmethod
    def from_manifest(cls, col_name: str, col_data: dict) -> "ColumnInfo":
        """Parse a column entry from manifest.json columns dict."""
        tests = []
        # dbt stores tests under 'tests' key or nested in meta
        if isinstance(col_data, dict):
            tests = col_data.get("tests", [])
        return cls(
            name=col_name,
            dtype=col_data.get("dtype") if isinstance(col_data, dict) else None,
            description=col_data.get("description") if isinstance(col_data, dict) else None,
            tests=tests,
        )


@dataclass
class ModelNode:
    """
    A flattened representation of a dbt node (model, source, or seed).

    Attributes:
        name: Short model name (e.g., "customers")
        unique_id: Full dbt unique_id (e.g., "model.my_project.customers")
        resource_type: "model", "source", or "seed"
        schema: Target schema name (if available)
        description: Node description from dbt docs
        columns: Dict of column_name -> ColumnInfo
        depends_on: List of parent node unique_ids (from depends_on.nodes)
    """
    name: str
    unique_id: str
    resource_type: str
    schema: str | None = None
    description: str | None = None
    columns: dict = field(default_factory=dict)
    depends_on: list = field(default_factory=list)

    @classmethod
    def from_manifest_node(cls, node_data: dict) -> Optional["ModelNode"]:
        """
        Create a ModelNode from a manifest.json node dict.

        Returns None if the node is not a model/source/seed or is a test/metric/snapshot.
        """
        resource_type = node_data.get("resource_type", "")

        # Skip non-allowed resource types
        if resource_type not in ALLOWED_RESOURCE_TYPES:
            return None

        unique_id = node_data.get("unique_id", "")
        name = node_data.get("name", "")

        # Extract columns
        columns = {}
        raw_columns = node_data.get("columns", {})
        if isinstance(raw_columns, dict):
            for col_name, col_data in raw_columns.items():
                columns[col_name] = ColumnInfo.from_manifest(col_name, col_data)

        # Extract depends_on
        depends_on_list = []
        depends_on = node_data.get("depends_on", {})
        if isinstance(depends_on, dict):
            depends_on_list = depends_on.get("nodes", [])
        elif isinstance(depends_on, list):
            depends_on_list = depends_on

        # Extract schema (stored in 'schema' or 'database'/'schema' fields)
        schema = node_data.get("schema")
        if not schema:
            # Try to extract from database.schema package name
            database = node_data.get("database")
            if database and "." in database:
                schema = database.split(".")[-1]

        # Extract description
        description = node_data.get("description", "")

        return cls(
            name=name,
            unique_id=unique_id,
            resource_type=resource_type,
            schema=schema,
            description=description,
            columns=columns,
            depends_on=depends_on_list,
        )


def parse_manifest(manifest_path: str | Path) -> list[ModelNode]:
    """
    Parse a dbt manifest.json file and return a flat list of ModelNode objects.

    Args:
        manifest_path: Path to manifest.json (from dbt build's target/manifest.json)

    Returns:
        List of ModelNode objects for all models, sources, and seeds.
        Empty list if file not found or invalid.

    Example:
        >>> nodes = parse_manifest("target/manifest.json")
        >>> print(len(nodes), "nodes parsed")
    """
    manifest_path = Path(manifest_path)

    if not manifest_path.exists():
        warnings.warn(f"Manifest file not found: {manifest_path}", stacklevel=2)
        return []

    try:
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        warnings.warn(f"Invalid JSON in manifest file: {e}", stacklevel=2)
        return []

    nodes_list = manifest.get("nodes", {})

    model_nodes = []
    for _node_key, node_data in nodes_list.items():
        model_node = ModelNode.from_manifest_node(node_data)
        if model_node is not None:
            model_nodes.append(model_node)

    return model_nodes


def parse_manifest_from_dict(manifest: dict) -> list[ModelNode]:
    """
    Parse a manifest dict directly (useful for testing or memory-based parsing).

    Args:
        manifest: Parsed manifest dict (already loaded JSON)

    Returns:
        List of ModelNode objects.
    """
    nodes_list = manifest.get("nodes", {})

    model_nodes = []
    for _node_key, node_data in nodes_list.items():
        model_node = ModelNode.from_manifest_node(node_data)
        if model_node is not None:
            model_nodes.append(model_node)

    return model_nodes


# ---- Simple test ----
if __name__ == "__main__":
    import sys

    # Test with a sample manifest if provided as argument
    if len(sys.argv) > 1:
        nodes = parse_manifest(sys.argv[1])
        print(f"Parsed {len(nodes)} nodes")
        for node in nodes[:5]:
            print(f"  - {node.unique_id}: {len(node.columns)} columns, depends on {len(node.depends_on)} nodes")
    else:
        # Minimal smoke test: create a dummy node
        dummy_manifest = {
            "nodes": {
                "model.my_project.my_model": {
                    "unique_id": "model.my_project.my_model",
                    "name": "my_model",
                    "resource_type": "model",
                    "schema": "analytics",
                    "description": "A test model",
                    "columns": {
                        "id": {"dtype": "int", "description": "Primary key"},
                        "name": {"dtype": "varchar", "description": "Model name"},
                    },
                    "depends_on": {"nodes": ["model.my_project.source_model"]},
                }
            }
        }
        nodes = parse_manifest_from_dict(dummy_manifest)
        assert len(nodes) == 1
        assert nodes[0].name == "my_model"
        assert len(nodes[0].columns) == 2
        print("manifest_parser.py smoke test passed.")
