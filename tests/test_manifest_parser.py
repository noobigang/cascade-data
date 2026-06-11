"""
test_manifest_parser.py — Tests for the manifest.json → LineageGraph parser.

Targets the real `lineage.parser` API (the project is now in `lineage/`,
not the legacy `cascade/` package).
"""
from __future__ import annotations

import pytest

from lineage.models import ColumnNode, LineageGraph, TableNode
from lineage.parser import parse_manifest, parse_manifest_from_dict

# ─────────────────────────────────────────────────────────────────
# ColumnNode tests
# ─────────────────────────────────────────────────────────────────

class TestColumnNode:
    def test_defaults(self):
        col = ColumnNode(name="customer_id")
        assert col.name == "customer_id"
        assert col.data_type == ""
        assert col.description == ""
        assert col.source_columns == []

    def test_full_construction(self):
        col = ColumnNode(
            name="net_amount",
            data_type="DECIMAL",
            description="Total after discount",
            source_columns=["raw_orders.total_amount", "raw_orders.discount_amount"],
        )
        assert col.data_type == "DECIMAL"
        assert col.source_columns == ["raw_orders.total_amount", "raw_orders.discount_amount"]

    def test_source_columns_independent_per_instance(self):
        a = ColumnNode(name="x")
        b = ColumnNode(name="y")
        a.source_columns.append("src.x")
        assert b.source_columns == []  # mutable default didn't leak


# ─────────────────────────────────────────────────────────────────
# TableNode tests
# ─────────────────────────────────────────────────────────────────

class TestTableNode:
    def test_basic(self):
        node = TableNode(
            unique_id="model.test.dim_customers",
            name="dim_customers",
            schema="analytics",
            resource_type="model",
            depends_on=["source.test.raw_customers"],
        )
        assert node.unique_id == "model.test.dim_customers"
        assert node.resource_type == "model"
        assert "source.test.raw_customers" in node.depends_on

    def test_add_column(self):
        node = TableNode(unique_id="t", name="t", resource_type="model")
        node.add_column(ColumnNode(name="id", data_type="INTEGER"))
        node.add_column(ColumnNode(name="name", data_type="VARCHAR"))
        assert len(node.columns) == 2
        assert "id" in node.columns

    def test_columns_dict_independent(self):
        a = TableNode(unique_id="a", name="a", resource_type="model")
        b = TableNode(unique_id="b", name="b", resource_type="model")
        a.add_column(ColumnNode(name="x"))
        assert b.columns == {}


# ─────────────────────────────────────────────────────────────────
# parse_manifest_from_dict
# ─────────────────────────────────────────────────────────────────

class TestParseManifestFromDict:
    def test_returns_lineage_graph(self, manifest_data: dict):
        graph = parse_manifest_from_dict(manifest_data)
        assert isinstance(graph, LineageGraph)

    def test_resource_types(self, manifest_data: dict):
        graph = parse_manifest_from_dict(manifest_data)
        types = {graph.get_node(uid).resource_type for uid in graph.nodes}
        assert "model" in types
        assert "source" in types
        assert "seed" in types
        # `test` is a real dbt resource_type, but the parser filters it out
        # of the lineage graph (test nodes aren't data lineage — they're
        # metadata assertions).
        assert "test" not in types

    def test_node_count(self, manifest_data: dict):
        # Fixture has 5 models + 1 source + 1 seed = 7 nodes (test.* filtered)
        graph = parse_manifest_from_dict(manifest_data)
        assert len(graph) == 7

    def test_node_attributes_preserved(self, manifest_data: dict):
        graph = parse_manifest_from_dict(manifest_data)
        customers = graph.get_node("model.my_project.customers")
        assert customers is not None
        assert customers.name == "customers"
        assert customers.resource_type == "model"
        # The fixture manifest doesn't populate relation_name, so the
        # parser leaves schema blank. We test the populated case against
        # the demo manifest in test_lineage.py::test_dim_customers_depends_on_stg_and_int.
        assert "user_id" in customers.columns

    def test_source_attributes(self, manifest_data: dict):
        graph = parse_manifest_from_dict(manifest_data)
        source = graph.get_node("source.my_project.raw_source")
        assert source is not None
        assert source.resource_type == "source"

    def test_seed_attributes(self, manifest_data: dict):
        graph = parse_manifest_from_dict(manifest_data)
        seed = graph.get_node("seed.my_project.seed_countries")
        assert seed is not None
        assert seed.resource_type == "seed"

    def test_test_node_excluded(self, manifest_data: dict):
        graph = parse_manifest_from_dict(manifest_data)
        assert "test.my_project.unique_users" not in graph.nodes

    def test_depends_on_list(self, manifest_data: dict):
        graph = parse_manifest_from_dict(manifest_data)
        # raw_users depends on raw_source
        raw_users = graph.get_node("model.my_project.raw_users")
        assert "source.my_project.raw_source" in raw_users.depends_on

    def test_depends_on_list_form_supported(self):
        # Some toolchains emit depends_on as a list instead of {nodes: [...]}.
        # The parser should accept both.
        manifest = {
            "nodes": {
                "model.x.y": {
                    "unique_id": "model.x.y",
                    "name": "y",
                    "resource_type": "model",
                    "columns": {},
                    "depends_on": ["source.x.a", "source.x.b"],
                },
            },
        }
        graph = parse_manifest_from_dict(manifest)
        y = graph.get_node("model.x.y")
        assert y is not None
        assert y.depends_on == ["source.x.a", "source.x.b"]

    def test_metric_node_excluded(self):
        manifest = {
            "nodes": {
                "model.x.y": {
                    "unique_id": "model.x.y",
                    "name": "y",
                    "resource_type": "model",
                    "columns": {},
                    "depends_on": {"nodes": []},
                },
                "metric.x.revenue": {
                    "unique_id": "metric.x.revenue",
                    "name": "revenue",
                    "resource_type": "metric",
                    "columns": {},
                    "depends_on": {"nodes": []},
                },
            },
        }
        graph = parse_manifest_from_dict(manifest)
        assert "model.x.y" in graph.nodes
        assert "metric.x.revenue" not in graph.nodes

    def test_edges_built_from_depends_on(self, manifest_data: dict):
        graph = parse_manifest_from_dict(manifest_data)
        # raw_source -> raw_users, raw_users -> stg_users, etc.
        assert "model.my_project.raw_users" in graph.successors("source.my_project.raw_source")
        assert "model.my_project.stg_users" in graph.successors("model.my_project.raw_users")
        assert "model.my_project.reports" in graph.successors("model.my_project.customers")

    def test_missing_depends_on_target_does_not_crash(self):
        # A model that depends on a non-existent node (e.g. external table)
        # should still be added to the graph, just without that edge.
        manifest = {
            "nodes": {
                "model.x.y": {
                    "unique_id": "model.x.y",
                    "name": "y",
                    "resource_type": "model",
                    "columns": {},
                    "depends_on": {"nodes": ["source.x.does_not_exist"]},
                },
            },
        }
        graph = parse_manifest_from_dict(manifest)
        assert "model.x.y" in graph.nodes
        # Edge to the missing source is silently dropped.
        assert list(graph.successors("source.x.does_not_exist")) == []


# ─────────────────────────────────────────────────────────────────
# parse_manifest (file path variant)
# ─────────────────────────────────────────────────────────────────

class TestParseManifest:
    def test_parse_file(self, manifest_path):
        graph = parse_manifest(manifest_path)
        assert isinstance(graph, LineageGraph)
        assert len(graph) == 7
        names = {graph.get_node(uid).name for uid in graph.nodes}
        assert "customers" in names
        assert "reports" in names

    def test_parse_nonexistent_file_raises(self, tmp_path):
        # Documents the actual behavior: FileNotFoundError is raised.
        # If we want graceful degradation in the future, switch to a warning
        # and update this test.
        missing = tmp_path / "does_not_exist.json"
        with pytest.raises(FileNotFoundError):
            parse_manifest(missing)
