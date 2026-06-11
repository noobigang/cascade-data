"""
Column-level lineage extraction engine for Cascade.
"""

from lineage.diff import (
    ChangeType,
    ColumnChange,
    ManifestDiff,
    NodeChange,
    Severity,
    diff_manifest_files,
    diff_manifests,
)
from lineage.impact import (
    blast_radius_score,
    generate_impact_report,
    get_all_column_impacts,
    get_column_impact,
    get_deepest_lineage_path,
    get_downstream,
    get_most_connected_nodes,
    get_upstream,
)
from lineage.models import ColumnLineage, ColumnNode, LineageGraph, TableNode
from lineage.parser import parse_manifest, parse_manifest_from_dict
from lineage.sql_lineage import enrich_graph_with_lineage, extract_sql_lineage, get_column_lineage

__all__ = [
    "ColumnNode",
    "TableNode",
    "ColumnLineage",
    "LineageGraph",
    "parse_manifest",
    "parse_manifest_from_dict",
    "extract_sql_lineage",
    "enrich_graph_with_lineage",
    "get_column_lineage",
    "get_downstream",
    "get_upstream",
    "get_column_impact",
    "blast_radius_score",
    "generate_impact_report",
    "get_all_column_impacts",
    "get_most_connected_nodes",
    "get_deepest_lineage_path",
    # Manifest diff
    "ChangeType",
    "ColumnChange",
    "ManifestDiff",
    "NodeChange",
    "Severity",
    "diff_manifest_files",
    "diff_manifests",
]
