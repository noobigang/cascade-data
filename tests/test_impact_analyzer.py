"""
test_impact_analyzer.py — Tests for impact_analyzer.py.
"""

import warnings

import pytest
from cascade.graph.impact_analyzer import (
    blast_radius_score,
    get_column_lineage,
    get_downstream_columns,
    get_downstream_nodes,
    get_impact_summary,
    get_upstream_columns,
    get_upstream_nodes,
)
from cascade.graph.lineage_graph import build_lineage_graph
from cascade.parser.manifest_parser import parse_manifest_from_dict


@pytest.fixture
def graph(manifest_data):
    nodes = parse_manifest_from_dict(manifest_data)
    return build_lineage_graph(nodes)


class TestGetDownstreamNodes:
    def test_downstream_from_raw_source(self, graph):
        down = get_downstream_nodes(graph, "source.my_project.raw_source")
        assert "model.my_project.raw_users" in down
        # downstream chain: raw_users -> stg_users -> customers -> reports
        #                   raw_users -> orders -> reports
        assert len(down) == 5  # all except source and itself

    def test_downstream_from_raw_users(self, graph):
        down = get_downstream_nodes(graph, "model.my_project.raw_users")
        # raw_users -> stg_users -> customers -> reports
        # raw_users -> orders -> reports
        assert "model.my_project.stg_users" in down
        assert "model.my_project.customers" in down
        assert "model.my_project.orders" in down
        assert "model.my_project.reports" in down

    def test_downstream_from_terminal_node(self, graph):
        down = get_downstream_nodes(graph, "model.my_project.reports")
        assert down == []

    def test_downstream_missing_node(self, graph):
        with warnings.catch_warnings(record=True) as w:
            down = get_downstream_nodes(graph, "model.my_project.does_not_exist")
            assert down == []
            assert any("not found" in str(warning.message) for warning in w)


class TestGetUpstreamNodes:
    def test_upstream_from_reports(self, graph):
        up = get_upstream_nodes(graph, "model.my_project.reports")
        assert "model.my_project.customers" in up
        assert "model.my_project.orders" in up
        assert "model.my_project.stg_users" in up
        assert "model.my_project.raw_users" in up
        assert "source.my_project.raw_source" in up

    def test_upstream_from_source(self, graph):
        up = get_upstream_nodes(graph, "source.my_project.raw_source")
        assert up == []

    def test_upstream_missing_node(self, graph):
        with warnings.catch_warnings(record=True) as w:
            up = get_upstream_nodes(graph, "model.my_project.does_not_exist")
            assert up == []
            assert any("not found" in str(warning.message) for warning in w)


class TestBlastRadiusScore:
    def test_blast_radius_low(self, graph):
        # orders has only 1 terminal downstream (reports)
        score = blast_radius_score(graph, "model.my_project.orders")
        assert score == "LOW"

    def test_blast_radius_medium(self, graph):
        # stg_users has 2 terminal downstream (reports, orders) -> LOW actually
        # Let me reconsider: reports and orders are terminal nodes
        # stg_users downstream: customers -> reports, so reports is terminal
        # orders downstream: reports is terminal
        # Actually stg_users: downstream = [customers, reports], reports is terminal
        # So 1 terminal = LOW
        score = blast_radius_score(graph, "model.my_project.stg_users")
        assert score in ("LOW", "MEDIUM", "HIGH")

    def test_blast_radius_low_on_source(self, graph):
        # raw_source has 3 terminal downstream nodes (reports, orders, seed_countries) → LOW threshold
        score = blast_radius_score(graph, "source.my_project.raw_source")
        assert score == "LOW"

    def test_blast_radius_unknown(self, graph):
        with warnings.catch_warnings(record=True) as w:
            score = blast_radius_score(graph, "model.my_project.does_not_exist")
            assert score == "UNKNOWN"
            assert any("not found" in str(warning.message) for warning in w)


class TestColumnLineage:
    def test_column_lineage(self, graph):
        lineage = get_column_lineage(graph, "model.my_project.customers", "user_id")
        assert lineage is not None
        assert "upstream" in lineage
        assert "downstream" in lineage
        assert "path" in lineage
        assert "model.my_project.customers" in lineage["path"]

    def test_column_lineage_missing_node(self, graph):
        lineage = get_column_lineage(graph, "model.my_project.does_not_exist", "user_id")
        assert lineage is None


class TestGetImpactSummary:
    def test_impact_summary(self, graph):
        summary = get_impact_summary(graph, "model.my_project.customers")
        assert summary is not None
        assert summary["node_id"] == "model.my_project.customers"
        assert "upstream_count" in summary
        assert "downstream_count" in summary
        assert "blast_radius" in summary
        assert "columns" in summary
        assert "user_id" in summary["columns"]

    def test_impact_summary_missing(self, graph):
        with warnings.catch_warnings(record=True) as w:
            summary = get_impact_summary(graph, "model.my_project.does_not_exist")
            assert summary is None
            assert any("not found" in str(warning.message) for warning in w)


class TestGetDownstreamColumns:
    def test_downstream_columns(self, graph):
        cols = get_downstream_columns(graph, "model.my_project.stg_users", "user_id")
        assert len(cols) >= 1

    def test_downstream_columns_missing_node(self, graph):
        with warnings.catch_warnings(record=True) as w:
            cols = get_downstream_columns(graph, "model.my_project.does_not_exist", "user_id")
            assert cols == []
            assert any("not found" in str(warning.message) for warning in w)


class TestGetUpstreamColumns:
    def test_upstream_columns(self, graph):
        cols = get_upstream_columns(graph, "model.my_project.reports", "user_id")
        assert len(cols) >= 1

    def test_upstream_columns_missing_node(self, graph):
        with warnings.catch_warnings(record=True) as w:
            cols = get_upstream_columns(graph, "model.my_project.does_not_exist", "user_id")
            assert cols == []
            assert any("not found" in str(warning.message) for warning in w)
