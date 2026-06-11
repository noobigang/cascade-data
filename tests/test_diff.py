"""
test_diff.py — Tests for the manifest diff engine (lineage/diff.py).
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

from lineage.diff import (
    ChangeType,
    Severity,
    diff_manifest_files,
    diff_manifests,
)

DEMO_MANIFEST = Path(__file__).parent.parent / "demo" / "manifest.json"


def _make_manifest(*, models=None, sources=None, columns_per_model=None, deps=None):
    """Build a minimal manifest dict for testing.

    Args:
        models: list of (uid, name) tuples
        sources: list of (uid, name) tuples
        columns_per_model: dict mapping uid -> dict of {col_name: col_dict}
        deps: dict mapping uid -> list of dependency uids
    """
    models = models or []
    sources = sources or []
    columns_per_model = columns_per_model or {}
    deps = deps or {}

    manifest = {"nodes": {}, "sources": {}}
    for uid, name in models:
        manifest["nodes"][uid] = {
            "unique_id": uid,
            "name": name,
            "resource_type": uid.split(".")[0],
            "relation_name": '"db"."analytics"."' + name + '"',
            "columns": columns_per_model.get(uid, {}),
            "depends_on": {"nodes": deps.get(uid, [])},
        }
    for uid, name in sources:
        manifest["sources"][uid] = {
            "unique_id": uid,
            "name": name,
            "resource_type": "source",
            "relation_name": '"db"."raw"."' + name + '"',
            "columns": columns_per_model.get(uid, {}),
            "depends_on": {"nodes": deps.get(uid, [])},
        }
    return manifest


# ─────────────────────────────────────────────────────────────────
# Identity
# ─────────────────────────────────────────────────────────────────

class TestIdentity:
    def test_identical_manifests_have_no_changes(self):
        manifest = _make_manifest(
            models=[("model.p.m1", "m1")],
            columns_per_model={"model.p.m1": {"id": {"data_type": "int"}}},
        )
        diff = diff_manifests(manifest, copy.deepcopy(manifest))
        assert diff.total_changes == 0
        assert not diff.has_breaking_changes
        assert diff.nodes_added == []
        assert diff.nodes_removed == []
        assert diff.nodes_modified == []

    def test_empty_manifests(self):
        empty = _make_manifest()
        diff = diff_manifests(empty, copy.deepcopy(empty))
        assert diff.total_changes == 0


# ─────────────────────────────────────────────────────────────────
# Node-level changes
# ─────────────────────────────────────────────────────────────────

class TestNodeAdded:
    def test_model_added(self):
        before = _make_manifest()
        after = _make_manifest(models=[("model.p.new_model", "new_model")])
        diff = diff_manifests(before, after)
        assert len(diff.nodes_added) == 1
        assert diff.nodes_added[0].unique_id == "model.p.new_model"
        assert diff.nodes_added[0].severity == Severity.INFO

    def test_source_added(self):
        before = _make_manifest()
        after = _make_manifest(sources=[("source.p.raw_x", "raw_x")])
        diff = diff_manifests(before, after)
        assert len(diff.nodes_added) == 1
        assert diff.nodes_added[0].resource_type == "source"

    def test_addition_not_breaking(self):
        before = _make_manifest()
        after = _make_manifest(models=[("model.p.x", "x")])
        diff = diff_manifests(before, after)
        assert not diff.has_breaking_changes


class TestNodeRemoved:
    def test_model_removed(self):
        before = _make_manifest(models=[("model.p.x", "x")])
        after = _make_manifest()
        diff = diff_manifests(before, after)
        assert len(diff.nodes_removed) == 1
        assert diff.nodes_removed[0].unique_id == "model.p.x"
        assert diff.nodes_removed[0].severity == Severity.BREAKING

    def test_removal_is_breaking(self):
        before = _make_manifest(models=[("model.p.x", "x")])
        after = _make_manifest()
        diff = diff_manifests(before, after)
        assert diff.has_breaking_changes


class TestResourceTypeFilter:
    def test_test_nodes_ignored(self):
        before = _make_manifest()
        after = {
            "nodes": {
                "test.p.t": {
                    "unique_id": "test.p.t",
                    "name": "t",
                    "resource_type": "test",
                    "columns": {},
                    "depends_on": {"nodes": []},
                },
            },
        }
        diff = diff_manifests(before, after)
        # test.* is filtered out — should be no diff
        assert diff.total_changes == 0

    def test_metric_nodes_ignored(self):
        before = _make_manifest()
        after = {
            "nodes": {
                "metric.p.m": {
                    "unique_id": "metric.p.m",
                    "name": "m",
                    "resource_type": "metric",
                    "columns": {},
                    "depends_on": {"nodes": []},
                },
            },
        }
        diff = diff_manifests(before, after)
        assert diff.total_changes == 0


# ─────────────────────────────────────────────────────────────────
# Column-level changes
# ─────────────────────────────────────────────────────────────────

class TestColumnChanges:
    def test_column_added(self):
        before = _make_manifest(
            models=[("model.p.m", "m")],
            columns_per_model={"model.p.m": {"id": {"data_type": "int"}}},
        )
        after = _make_manifest(
            models=[("model.p.m", "m")],
            columns_per_model={
                "model.p.m": {
                    "id": {"data_type": "int"},
                    "new_col": {"data_type": "varchar"},
                },
            },
        )
        diff = diff_manifests(before, after)
        assert len(diff.nodes_modified) == 1
        col_changes = diff.nodes_modified[0].column_changes
        assert any(c.column == "new_col" and c.change_type == ChangeType.COLUMN_ADDED for c in col_changes)

    def test_column_removed_is_breaking(self):
        before = _make_manifest(
            models=[("model.p.m", "m")],
            columns_per_model={
                "model.p.m": {
                    "id": {"data_type": "int"},
                    "deprecated": {"data_type": "varchar"},
                },
            },
        )
        after = _make_manifest(
            models=[("model.p.m", "m")],
            columns_per_model={"model.p.m": {"id": {"data_type": "int"}}},
        )
        diff = diff_manifests(before, after)
        assert diff.has_breaking_changes
        col_changes = diff.nodes_modified[0].column_changes
        removed = [c for c in col_changes if c.change_type == ChangeType.COLUMN_REMOVED]
        assert len(removed) == 1
        assert removed[0].column == "deprecated"
        assert removed[0].severity == Severity.BREAKING

    def test_column_type_changed_is_warning(self):
        before = _make_manifest(
            models=[("model.p.m", "m")],
            columns_per_model={"model.p.m": {"id": {"data_type": "int"}}},
        )
        after = _make_manifest(
            models=[("model.p.m", "m")],
            columns_per_model={"model.p.m": {"id": {"data_type": "bigint"}}},
        )
        diff = diff_manifests(before, after)
        col_changes = diff.nodes_modified[0].column_changes
        type_changes = [c for c in col_changes if c.change_type == ChangeType.COLUMN_TYPE_CHANGED]
        assert len(type_changes) == 1
        assert type_changes[0].severity == Severity.WARNING
        assert type_changes[0].before == "int"
        assert type_changes[0].after == "bigint"

    def test_column_description_changed_is_info(self):
        before = _make_manifest(
            models=[("model.p.m", "m")],
            columns_per_model={"model.p.m": {"id": {"description": "old"}}},
        )
        after = _make_manifest(
            models=[("model.p.m", "m")],
            columns_per_model={"model.p.m": {"id": {"description": "new"}}},
        )
        diff = diff_manifests(before, after)
        col_changes = diff.nodes_modified[0].column_changes
        desc_changes = [c for c in col_changes if c.change_type == ChangeType.COLUMN_DESCRIPTION_CHANGED]
        assert len(desc_changes) == 1
        assert desc_changes[0].severity == Severity.INFO

    def test_multiple_column_changes_in_one_model(self):
        before = _make_manifest(
            models=[("model.p.m", "m")],
            columns_per_model={
                "model.p.m": {
                    "kept": {"data_type": "int"},
                    "dropped": {"data_type": "int"},
                    "renamed": {"data_type": "int"},
                },
            },
        )
        after = _make_manifest(
            models=[("model.p.m", "m")],
            columns_per_model={
                "model.p.m": {
                    "kept": {"data_type": "int"},
                    "renamed": {"data_type": "bigint"},
                    "new_one": {"data_type": "varchar"},
                },
            },
        )
        diff = diff_manifests(before, after)
        cc = diff.nodes_modified[0].column_changes
        types = {c.change_type for c in cc}
        assert ChangeType.COLUMN_ADDED in types
        assert ChangeType.COLUMN_REMOVED in types
        assert ChangeType.COLUMN_TYPE_CHANGED in types


# ─────────────────────────────────────────────────────────────────
# Dependency changes
# ─────────────────────────────────────────────────────────────────

class TestDependencyChanges:
    def test_dep_added(self):
        before = _make_manifest(
            models=[("model.p.a", "a"), ("model.p.b", "b"), ("model.p.c", "c")],
            deps={
                "model.p.b": ["model.p.a"],
                "model.p.c": ["model.p.a"],
            },
        )
        after = _make_manifest(
            models=[("model.p.a", "a"), ("model.p.b", "b"), ("model.p.c", "c")],
            deps={
                "model.p.b": ["model.p.a"],
                "model.p.c": ["model.p.a", "model.p.b"],  # new dep
            },
        )
        diff = diff_manifests(before, after)
        modified = [n for n in diff.nodes_modified if n.unique_id == "model.p.c"]
        assert len(modified) == 1
        assert "model.p.b" in modified[0].deps_added

    def test_dep_removed_is_breaking(self):
        before = _make_manifest(
            models=[("model.p.a", "a"), ("model.p.b", "b")],
            deps={"model.p.b": ["model.p.a"]},
        )
        after = _make_manifest(
            models=[("model.p.a", "a"), ("model.p.b", "b")],
            deps={"model.p.b": []},
        )
        diff = diff_manifests(before, after)
        modified = [n for n in diff.nodes_modified if n.unique_id == "model.p.b"]
        assert len(modified) == 1
        assert "model.p.a" in modified[0].deps_removed
        assert modified[0].severity == Severity.BREAKING
        assert diff.has_breaking_changes


# ─────────────────────────────────────────────────────────────────
# Schema changes
# ─────────────────────────────────────────────────────────────────

class TestSchemaChange:
    def test_schema_change_detected(self):
        before = _make_manifest(models=[("model.p.m", "m")])
        # Mutate schema by hand
        after = _make_manifest(models=[("model.p.m", "m")])
        after["nodes"]["model.p.m"]["relation_name"] = '"db"."staging"."m"'
        diff = diff_manifests(before, after)
        modified = diff.nodes_modified
        assert len(modified) == 1
        assert modified[0].schema_before == "analytics"
        assert modified[0].schema_after == "staging"


# ─────────────────────────────────────────────────────────────────
# Real demo manifest
# ─────────────────────────────────────────────────────────────────

class TestAgainstDemoManifest:
    def test_diffing_demo_against_itself(self):
        with open(DEMO_MANIFEST, encoding="utf-8") as f:
            manifest = json.load(f)
        diff = diff_manifests(manifest, copy.deepcopy(manifest))
        assert diff.total_changes == 0
        assert not diff.has_breaking_changes

    def test_diffing_demo_against_dropped_column(self):
        with open(DEMO_MANIFEST, encoding="utf-8") as f:
            before = json.load(f)
        after = copy.deepcopy(before)

        # Drop a column from stg_orders
        stg = after["nodes"]["model.ecommerce.stg_orders"]
        if "order_status" in stg["columns"]:
            del stg["columns"]["order_status"]

        diff = diff_manifests(before, after)
        assert diff.has_breaking_changes
        modified = [n for n in diff.nodes_modified if n.unique_id == "model.ecommerce.stg_orders"]
        assert len(modified) == 1
        col_changes = modified[0].column_changes
        removed = [c for c in col_changes if c.change_type == ChangeType.COLUMN_REMOVED]
        assert any(c.column == "order_status" for c in removed)


# ─────────────────────────────────────────────────────────────────
# Text summary
# ─────────────────────────────────────────────────────────────────

class TestTextSummary:
    def test_summary_mentions_added(self):
        before = _make_manifest()
        after = _make_manifest(models=[("model.p.x", "x")])
        diff = diff_manifests(before, after)
        text = diff.to_text()
        assert "Manifest Diff" in text
        assert "model.p.x" in text
        assert "+1 added" in text

    def test_summary_mentions_breaking(self):
        before = _make_manifest(models=[("model.p.x", "x")])
        after = _make_manifest()
        diff = diff_manifests(before, after)
        text = diff.to_text()
        assert "Breaking: YES" in text
        assert "BREAKING" in text


# ─────────────────────────────────────────────────────────────────
# File-path convenience
# ─────────────────────────────────────────────────────────────────

class TestFilePath:
    def test_diff_manifest_files(self, tmp_path):
        before = _make_manifest(models=[("model.p.x", "x")])
        after = _make_manifest()
        before_file = tmp_path / "before.json"
        after_file = tmp_path / "after.json"
        before_file.write_text(json.dumps(before), encoding="utf-8")
        after_file.write_text(json.dumps(after), encoding="utf-8")

        diff = diff_manifest_files(str(before_file), str(after_file))
        assert len(diff.nodes_removed) == 1
