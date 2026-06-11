"""
Manifest diff — compare two dbt manifest.json files and surface what
changed at the model and column level.

Detects:
- Models / sources / seeds / snapshots added or removed
- Column additions, removals, type changes, description changes
- Dependency changes (ref() / source() added or removed)
- Schema changes (relation_name schema part)

Each change is tagged with a severity:
- ``breaking``  — downstream consumers will break
- ``warning``   — possible impact, needs review
- ``info``      — additive or cosmetic, no expected impact

This is a pure-data module; it does not require a LineageGraph. Both
manifests are compared as dicts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Severity(StrEnum):
    """How much a change matters for downstream consumers."""

    INFO = "info"
    WARNING = "warning"
    BREAKING = "breaking"


class ChangeType(StrEnum):
    """Kinds of changes we surface."""

    NODE_ADDED = "node_added"
    NODE_REMOVED = "node_removed"
    NODE_MODIFIED = "node_modified"
    COLUMN_ADDED = "column_added"
    COLUMN_REMOVED = "column_removed"
    COLUMN_TYPE_CHANGED = "column_type_changed"
    COLUMN_DESCRIPTION_CHANGED = "column_description_changed"
    DEP_ADDED = "dependency_added"
    DEP_REMOVED = "dependency_removed"
    SCHEMA_CHANGED = "schema_changed"


@dataclass
class ColumnChange:
    """A single column-level change within a node."""

    column: str
    change_type: ChangeType
    severity: Severity
    before: str | None = None  # old value (for type/description)
    after: str | None = None  # new value


@dataclass
class NodeChange:
    """All changes detected for a single node (model / source / seed / snapshot)."""

    unique_id: str
    name: str
    resource_type: str
    severity: Severity
    column_changes: list[ColumnChange] = field(default_factory=list)
    deps_added: list[str] = field(default_factory=list)
    deps_removed: list[str] = field(default_factory=list)
    schema_before: str | None = None
    schema_after: str | None = None

    @property
    def is_added(self) -> bool:
        return not self.column_changes and not self.deps_added and not self.deps_removed

    @property
    def total_column_changes(self) -> int:
        return len(self.column_changes)


@dataclass
class ManifestDiff:
    """The full diff between two manifests."""

    nodes_added: list[NodeChange] = field(default_factory=list)
    nodes_removed: list[NodeChange] = field(default_factory=list)
    nodes_modified: list[NodeChange] = field(default_factory=list)

    @property
    def total_changes(self) -> int:
        return (
            len(self.nodes_added)
            + len(self.nodes_removed)
            + sum(n.total_column_changes for n in self.nodes_modified)
            + sum(len(n.deps_added) + len(n.deps_removed) for n in self.nodes_modified)
        )

    @property
    def has_breaking_changes(self) -> bool:
        if any(n.severity == Severity.BREAKING for n in self.nodes_removed):
            return True
        # A modified node can be BREAKING for two reasons:
        #   1. one of its column changes is BREAKING (column removed)
        #   2. the node itself was escalated to BREAKING (dependency removed)
        for n in self.nodes_modified:
            if n.severity == Severity.BREAKING:
                return True
            if any(c.severity == Severity.BREAKING for c in n.column_changes):
                return True
        return False

    def to_text(self) -> str:
        """Human-readable summary suitable for the impact panel / reports."""
        lines: list[str] = []
        lines.append("=== Manifest Diff ===")
        lines.append(
            f"Summary: +{len(self.nodes_added)} added, "
            f"-{len(self.nodes_removed)} removed, "
            f"~{len(self.nodes_modified)} modified"
        )
        lines.append(
            f"Total: {self.total_changes} change(s). "
            f"Breaking: {'YES' if self.has_breaking_changes else 'no'}"
        )
        lines.append("")

        if self.nodes_added:
            lines.append(f"--- Added ({len(self.nodes_added)}) ---")
            for n in self.nodes_added:
                lines.append(f"  + {n.unique_id} ({n.resource_type})")
            lines.append("")

        if self.nodes_removed:
            lines.append(f"--- Removed ({len(self.nodes_removed)}) [BREAKING] ---")
            for n in self.nodes_removed:
                lines.append(f"  - {n.unique_id} ({n.resource_type})")
            lines.append("")

        if self.nodes_modified:
            lines.append(f"--- Modified ({len(self.nodes_modified)}) ---")
            for n in self.nodes_modified:
                lines.append(f"  ~ {n.unique_id} ({n.resource_type})")
                for c in n.column_changes:
                    marker = "!!" if c.severity == Severity.BREAKING else ("?" if c.severity == Severity.WARNING else "+")
                    detail = ""
                    if c.before is not None or c.after is not None:
                        detail = f" ({c.before!r} -> {c.after!r})"
                    lines.append(f"    {marker} column {c.column!r}: {c.change_type.value}{detail}")
                for d in n.deps_added:
                    lines.append(f"    + dep {d}")
                for d in n.deps_removed:
                    lines.append(f"    - dep {d}")
                if n.schema_before and n.schema_after and n.schema_before != n.schema_after:
                    lines.append(
                        f"    ? schema: {n.schema_before!r} -> {n.schema_after!r}"
                    )
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────

def _iter_all_nodes(manifest: dict) -> dict[str, dict]:
    """Return a unified {unique_id: node_dict} from manifest, skipping tests/metrics.

    Mirrors the filter in lineage.parser._parse_resource_type so we only
    compare resources that would actually appear in the lineage graph.
    """
    from lineage.parser import _LINEAGE_RESOURCE_TYPES, _parse_resource_type

    result: dict[str, dict] = {}
    for uid, node in manifest.get("nodes", {}).items():
        if _parse_resource_type(uid) not in _LINEAGE_RESOURCE_TYPES:
            continue
        result[uid] = node
    for uid, src in manifest.get("sources", {}).items():
        if _parse_resource_type(uid) not in _LINEAGE_RESOURCE_TYPES:
            continue
        result[uid] = src
    return result


def _get_columns(node_dict: dict) -> dict[str, dict]:
    """Extract {col_name: col_dict} from a manifest node, tolerant of shape."""
    cols = node_dict.get("columns", {})
    if not isinstance(cols, dict):
        return {}
    return cols


def _get_depends_on(node_dict: dict) -> list[str]:
    """Return depends_on as a flat list of UIDs."""
    depends = node_dict.get("depends_on", {})
    if isinstance(depends, dict):
        return list(depends.get("nodes", []))
    if isinstance(depends, list):
        return list(depends)
    return []


def _get_schema(node_dict: dict) -> str:
    """Extract the schema name from relation_name, matching lineage.parser semantics."""
    relation_name = node_dict.get("relation_name", "")
    if "." in relation_name:
        parts = relation_name.split(".")
        if len(parts) >= 2:
            return parts[-2].strip('"[]`')
    return ""


# ─────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────

def diff_manifests(before: dict, after: dict) -> ManifestDiff:
    """Compute the diff between two manifest dicts.

    Args:
        before: the earlier manifest.json parsed as a dict
        after: the later manifest.json parsed as a dict

    Returns:
        A ManifestDiff describing every detected change.
    """
    before_nodes = _iter_all_nodes(before)
    after_nodes = _iter_all_nodes(after)

    before_uids = set(before_nodes)
    after_uids = set(after_nodes)

    result = ManifestDiff()

    # ── Added nodes (in after, not in before)
    for uid in sorted(after_uids - before_uids):
        node = after_nodes[uid]
        result.nodes_added.append(
            NodeChange(
                unique_id=uid,
                name=node.get("name", uid.split(".")[-1]),
                resource_type=node.get("resource_type", uid.split(".")[0]),
                severity=Severity.INFO,
            )
        )

    # ── Removed nodes (in before, not in after) — BREAKING
    for uid in sorted(before_uids - after_uids):
        node = before_nodes[uid]
        result.nodes_removed.append(
            NodeChange(
                unique_id=uid,
                name=node.get("name", uid.split(".")[-1]),
                resource_type=node.get("resource_type", uid.split(".")[0]),
                severity=Severity.BREAKING,
            )
        )

    # ── Modified nodes (in both)
    for uid in sorted(before_uids & after_uids):
        before_node = before_nodes[uid]
        after_node = after_nodes[uid]

        node_change = NodeChange(
            unique_id=uid,
            name=after_node.get("name", uid.split(".")[-1]),
            resource_type=after_node.get("resource_type", uid.split(".")[0]),
            severity=Severity.INFO,
        )

        # Columns
        before_cols = _get_columns(before_node)
        after_cols = _get_columns(after_node)

        # Columns added
        for col_name in sorted(after_cols.keys() - before_cols.keys()):
            node_change.column_changes.append(
                ColumnChange(
                    column=col_name,
                    change_type=ChangeType.COLUMN_ADDED,
                    severity=Severity.INFO,
                )
            )
            # Additions don't escalate severity, so nothing to update on node_change.severity.

        # Columns removed — BREAKING
        for col_name in sorted(before_cols.keys() - after_cols.keys()):
            node_change.column_changes.append(
                ColumnChange(
                    column=col_name,
                    change_type=ChangeType.COLUMN_REMOVED,
                    severity=Severity.BREAKING,
                )
            )
            node_change.severity = Severity.BREAKING

        # Columns modified
        for col_name in sorted(before_cols.keys() & after_cols.keys()):
            before_col = before_cols[col_name]
            after_col = after_cols[col_name]
            if not isinstance(before_col, dict) or not isinstance(after_col, dict):
                continue

            before_type = str(before_col.get("data_type", ""))
            after_type = str(after_col.get("data_type", ""))
            before_desc = str(before_col.get("description", ""))
            after_desc = str(after_col.get("description", ""))

            if before_type and after_type and before_type != after_type:
                node_change.column_changes.append(
                    ColumnChange(
                        column=col_name,
                        change_type=ChangeType.COLUMN_TYPE_CHANGED,
                        severity=Severity.WARNING,
                        before=before_type,
                        after=after_type,
                    )
                )
                if node_change.severity != Severity.BREAKING:
                    node_change.severity = Severity.WARNING

            if before_desc != after_desc:
                node_change.column_changes.append(
                    ColumnChange(
                        column=col_name,
                        change_type=ChangeType.COLUMN_DESCRIPTION_CHANGED,
                        severity=Severity.INFO,
                        before=before_desc,
                        after=after_desc,
                    )
                )

        # Dependencies
        before_deps = set(_get_depends_on(before_node))
        after_deps = set(_get_depends_on(after_node))

        for dep in sorted(after_deps - before_deps):
            node_change.deps_added.append(dep)
            if node_change.severity == Severity.INFO:
                node_change.severity = Severity.WARNING

        for dep in sorted(before_deps - after_deps):
            node_change.deps_removed.append(dep)
            # Removing a dep is BREAKING — anything that was depending on the
            # chain through that dep loses data flow.
            node_change.severity = Severity.BREAKING

        # Schema
        before_schema = _get_schema(before_node)
        after_schema = _get_schema(after_node)
        if before_schema and after_schema and before_schema != after_schema:
            node_change.schema_before = before_schema
            node_change.schema_after = after_schema
            if node_change.severity == Severity.INFO:
                node_change.severity = Severity.WARNING

        if (
            node_change.column_changes
            or node_change.deps_added
            or node_change.deps_removed
            or (node_change.schema_before and node_change.schema_before != node_change.schema_after)
        ):
            result.nodes_modified.append(node_change)

    return result


# ─────────────────────────────────────────────────────────────────
# File-path convenience
# ─────────────────────────────────────────────────────────────────

def diff_manifest_files(before_path: str, after_path: str) -> ManifestDiff:
    """Load two manifest.json files and diff them."""
    import json
    from pathlib import Path

    with open(Path(before_path), encoding="utf-8") as f:
        before = json.load(f)
    with open(Path(after_path), encoding="utf-8") as f:
        after = json.load(f)
    return diff_manifests(before, after)
