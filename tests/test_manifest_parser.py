"""
test_manifest_parser.py — Tests for manifest_parser.py.
"""

import warnings

from cascade.parser.manifest_parser import (
    ALLOWED_RESOURCE_TYPES,
    ColumnInfo,
    ModelNode,
    parse_manifest,
    parse_manifest_from_dict,
)


class TestColumnInfo:
    def test_from_manifest_full(self):
        col_data = {"dtype": "int", "description": "Primary key", "tests": ["unique"]}
        col = ColumnInfo.from_manifest("id", col_data)
        assert col.name == "id"
        assert col.dtype == "int"
        assert col.description == "Primary key"
        assert col.tests == ["unique"]

    def test_from_manifest_minimal(self):
        col = ColumnInfo.from_manifest("name", {})
        assert col.name == "name"
        assert col.dtype is None
        assert col.description is None
        assert col.tests == []

    def test_from_manifest_non_dict(self):
        col = ColumnInfo.from_manifest("x", "not a dict")
        assert col.name == "x"
        assert col.dtype is None


class TestModelNode:
    def test_from_manifest_node_model(self):
        node_data = {
            "unique_id": "model.my_project.orders",
            "name": "orders",
            "resource_type": "model",
            "schema": "analytics",
            "description": "Order table",
            "columns": {
                "id": {"dtype": "int", "description": "PK"},
            },
            "depends_on": {"nodes": ["source.my_project.raw"]},
        }
        node = ModelNode.from_manifest_node(node_data)
        assert node is not None
        assert node.name == "orders"
        assert node.unique_id == "model.my_project.orders"
        assert node.resource_type == "model"
        assert node.schema == "analytics"
        assert len(node.columns) == 1
        assert "id" in node.columns
        assert node.depends_on == ["source.my_project.raw"]

    def test_from_manifest_node_source(self):
        node_data = {
            "unique_id": "source.my_project.raw_source",
            "name": "raw_source",
            "resource_type": "source",
            "schema": "public",
            "description": "",
            "columns": {},
            "depends_on": {"nodes": []},
        }
        node = ModelNode.from_manifest_node(node_data)
        assert node is not None
        assert node.resource_type == "source"

    def test_from_manifest_node_seed(self):
        node_data = {
            "unique_id": "seed.my_project.countries",
            "name": "countries",
            "resource_type": "seed",
            "columns": {},
            "depends_on": {"nodes": []},
        }
        node = ModelNode.from_manifest_node(node_data)
        assert node is not None
        assert node.resource_type == "seed"

    def test_from_manifest_node_skips_test(self):
        node_data = {
            "unique_id": "test.my_project.unique_id",
            "name": "unique_id",
            "resource_type": "test",
            "columns": {},
            "depends_on": {"nodes": []},
        }
        node = ModelNode.from_manifest_node(node_data)
        assert node is None

    def test_from_manifest_node_skips_metric(self):
        node_data = {
            "unique_id": "metric.my_project.revenue",
            "name": "revenue",
            "resource_type": "metric",
            "columns": {},
            "depends_on": {"nodes": []},
        }
        node = ModelNode.from_manifest_node(node_data)
        assert node is None

    def test_from_manifest_node_depends_on_list(self):
        node_data = {
            "unique_id": "model.my_project.x",
            "name": "x",
            "resource_type": "model",
            "columns": {},
            "depends_on": ["source.my_project.a", "source.my_project.b"],
        }
        node = ModelNode.from_manifest_node(node_data)
        assert node is not None
        assert node.depends_on == ["source.my_project.a", "source.my_project.b"]

    def test_from_manifest_node_schema_from_database(self):
        node_data = {
            "unique_id": "model.my_project.y",
            "name": "y",
            "resource_type": "model",
            "database": "mywarehouse.analytics",
            "columns": {},
            "depends_on": {"nodes": []},
        }
        node = ModelNode.from_manifest_node(node_data)
        assert node is not None
        assert node.schema == "analytics"


class TestParseManifest:
    def test_parse_manifest_from_dict(self, manifest_data):
        nodes = parse_manifest_from_dict(manifest_data)
        # Only model/source/seed — excludes test node
        resource_types = {n.resource_type for n in nodes}
        assert "model" in resource_types
        assert "source" in resource_types
        assert "seed" in resource_types
        assert "test" not in resource_types
        assert len(nodes) == 7  # 5 models + 1 source + 1 seed

    def test_parse_manifest_file(self, manifest_path):
        nodes = parse_manifest(manifest_path)
        assert len(nodes) == 7
        names = {n.name for n in nodes}
        assert "customers" in names
        assert "reports" in names

    def test_parse_manifest_file_not_found(self):
        with warnings.catch_warnings(record=True) as w:
            nodes = parse_manifest("/nonexistent/path/manifest.json")
            assert nodes == []
            assert any("not found" in str(warning.message) for warning in w)

    def test_parse_manifest_invalid_json(self, tmp_path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("{ invalid json }", encoding="utf-8")
        with warnings.catch_warnings(record=True) as w:
            nodes = parse_manifest(bad_file)
            assert nodes == []
            assert any("Invalid JSON" in str(warning.message) for warning in w)


class TestAllowedResourceTypes:
    def test_allowed_types(self):
        assert {"model", "source", "seed"} == ALLOWED_RESOURCE_TYPES
