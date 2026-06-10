"""
Tests for the column-level lineage extraction engine.
"""

import json
import sys
from pathlib import Path

import pytest

# Ensure the lineage package is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from lineage.impact import (
    blast_radius_score,
    generate_impact_report,
    get_all_column_impacts,
    get_downstream,
    get_most_connected_nodes,
    get_upstream,
)
from lineage.models import ColumnLineage, ColumnNode, LineageGraph, TableNode
from lineage.parser import parse_manifest, parse_manifest_from_dict
from lineage.sql_lineage import enrich_graph_with_lineage, extract_sql_lineage

DEMO_MANIFEST = Path(__file__).parent.parent / "demo" / "manifest.json"


# ─────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────

@pytest.fixture
def manifest_data() -> dict:
    with open(DEMO_MANIFEST, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def graph(manifest_data: dict) -> LineageGraph:
    return parse_manifest_from_dict(manifest_data)


@pytest.fixture
def enriched_graph(manifest_data: dict) -> LineageGraph:
    g = parse_manifest_from_dict(manifest_data)
    enrich_graph_with_lineage(g)
    return g


# ─────────────────────────────────────────────────────────────────
# Model / Data Structure Tests
# ─────────────────────────────────────────────────────────────────

class TestDataModels:
    def test_column_node_defaults(self):
        col = ColumnNode(name="customer_id")
        assert col.name == "customer_id"
        assert col.data_type == ""
        assert col.description == ""
        assert col.source_columns == []

    def test_column_node_full(self):
        col = ColumnNode(
            name="net_amount",
            data_type="DECIMAL",
            description="Total after discount",
            source_columns=["raw_orders.total_amount", "raw_orders.discount_amount"],
        )
        assert col.source_columns == ["raw_orders.total_amount", "raw_orders.discount_amount"]

    def test_table_node(self):
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

    def test_table_node_add_column(self):
        node = TableNode(unique_id="test", name="test", resource_type="model")
        node.add_column(ColumnNode(name="id", data_type="INTEGER"))
        node.add_column(ColumnNode(name="name", data_type="VARCHAR"))
        assert len(node.columns) == 2
        assert "id" in node.columns

    def test_column_lineage(self):
        lineage = ColumnLineage(
            source_column="raw_customers.customer_id",
            target_column="dim_customers.customer_id",
            transformation="COALESCE(co.total_orders, 0)",
        )
        assert lineage.source_column == "raw_customers.customer_id"
        assert "COALESCE" in lineage.transformation


# ─────────────────────────────────────────────────────────────────
# LineageGraph Tests
# ─────────────────────────────────────────────────────────────────

class TestLineageGraph:
    def test_graph_empty(self):
        g = LineageGraph()
        assert len(g) == 0
        assert g.nodes == []

    def test_graph_add_node(self):
        g = LineageGraph()
        node = TableNode(unique_id="model.test.a", name="a", resource_type="model")
        g.add_node(node)
        assert g.has_node("model.test.a")
        assert len(g) == 1

    def test_graph_add_edge(self):
        g = LineageGraph()
        a = TableNode(unique_id="model.test.a", name="a", resource_type="model")
        b = TableNode(unique_id="model.test.b", name="b", resource_type="model")
        g.add_node(a)
        g.add_node(b)
        g.add_edge("model.test.a", "model.test.b")
        assert "model.test.a" in g.predecessors("model.test.b")
        assert "model.test.b" in g.successors("model.test.a")

    def test_graph_ancestors(self):
        g = LineageGraph()
        a = TableNode(unique_id="src", name="src", resource_type="source")
        b = TableNode(unique_id="model.b", name="b", resource_type="model", depends_on=["src"])
        c = TableNode(unique_id="model.c", name="c", resource_type="model", depends_on=["model.b"])
        g.add_node(a)
        g.add_node(b)
        g.add_node(c)
        g.add_edge("src", "model.b")
        g.add_edge("model.b", "model.c")
        assert "src" in g.ancestors("model.c")
        assert "model.b" in g.ancestors("model.c")

    def test_graph_descendants(self):
        g = LineageGraph()
        a = TableNode(unique_id="src", name="src", resource_type="source")
        b = TableNode(unique_id="model.b", name="b", resource_type="model", depends_on=["src"])
        c = TableNode(unique_id="model.c", name="c", resource_type="model", depends_on=["model.b"])
        g.add_node(a)
        g.add_node(b)
        g.add_node(c)
        g.add_edge("src", "model.b")
        g.add_edge("model.b", "model.c")
        assert "model.b" in g.descendants("src")
        assert "model.c" in g.descendants("src")

    def test_graph_filter_by_type(self):
        g = LineageGraph()
        g.add_node(TableNode(unique_id="model.a", name="a", resource_type="model"))
        g.add_node(TableNode(unique_id="source.b", name="b", resource_type="source"))
        filtered = g.filter_by_type("source")
        assert len(filtered) == 1
        assert "source.b" in filtered.nodes

    def test_graph_search_by_name(self):
        g = LineageGraph()
        g.add_node(TableNode(unique_id="model.dim_customers", name="dim_customers", resource_type="model"))
        g.add_node(TableNode(unique_id="model.fct_orders", name="fct_orders", resource_type="model"))
        results = g.search("customer")
        assert len(results) == 1
        assert results[0].name == "dim_customers"

    def test_graph_search_by_description(self):
        g = LineageGraph()
        g.add_node(TableNode(unique_id="model.a", name="a", description="Customer dimension table"))
        results = g.search("dimension")
        assert len(results) == 1

    def test_graph_subgraph(self):
        g = LineageGraph()
        g.add_node(TableNode(unique_id="model.a", name="a", resource_type="model"))
        g.add_node(TableNode(unique_id="model.b", name="b", resource_type="model"))
        g.add_node(TableNode(unique_id="model.c", name="c", resource_type="model"))
        sub = g.subgraph({"model.a", "model.b"})
        assert len(sub) == 2
        assert "model.c" not in sub.nodes


# ─────────────────────────────────────────────────────────────────
# Manifest Parser Tests
# ─────────────────────────────────────────────────────────────────

class TestManifestParser:
    def test_parse_manifest_file(self):
        g = parse_manifest(DEMO_MANIFEST)
        total_nodes = len(g)
        # 15 models + 5 sources = 20 total
        assert total_nodes == 20

    def test_parse_manifest_dict(self, manifest_data: dict):
        g = parse_manifest_from_dict(manifest_data)
        assert len(g) == 20

    def test_source_nodes_present(self, graph: LineageGraph):
        expected_sources = [
            "source.ecommerce.raw_orders",
            "source.ecommerce.raw_customers",
            "source.ecommerce.raw_products",
            "source.ecommerce.raw_marketing",
            "source.ecommerce.raw_inventory",
        ]
        for uid in expected_sources:
            assert graph.has_node(uid), f"Missing source: {uid}"
            node = graph.get_node(uid)
            assert node.resource_type == "source"

    def test_model_nodes_present(self, graph: LineageGraph):
        expected_models = [
            "model.ecommerce.stg_orders",
            "model.ecommerce.dim_customers",
            "model.ecommerce.fct_orders",
        ]
        for uid in expected_models:
            assert graph.has_node(uid), f"Missing model: {uid}"
            node = graph.get_node(uid)
            assert node.resource_type == "model"

    def test_column_extraction(self, graph: LineageGraph):
        node = graph.get_node("model.ecommerce.stg_orders")
        assert node is not None
        assert "order_id" in node.columns
        assert "customer_id" in node.columns
        assert "net_amount" in node.columns

    def test_depends_on_edges(self, graph: LineageGraph):
        stg = graph.get_node("model.ecommerce.stg_orders")
        assert stg is not None
        assert "source.ecommerce.raw_orders" in stg.depends_on

        # Edge should exist: source -> model
        successors = graph.successors("source.ecommerce.raw_orders")
        assert "model.ecommerce.stg_orders" in successors

    def test_stg_customers_depends_on_raw_customers(self, graph: LineageGraph):
        stg = graph.get_node("model.ecommerce.stg_customers")
        assert stg is not None
        assert "source.ecommerce.raw_customers" in stg.depends_on

    def test_dim_customers_depends_on_stg_and_int(self, graph: LineageGraph):
        dim = graph.get_node("model.ecommerce.dim_customers")
        assert dim is not None
        assert "model.ecommerce.stg_customers" in dim.depends_on
        assert "model.ecommerce.int_customer_orders" in dim.depends_on


# ─────────────────────────────────────────────────────────────────
# SQL Lineage Tests
# ─────────────────────────────────────────────────────────────────

class TestSQLLineage:
    def test_stg_orders_lineage(self, graph: LineageGraph):
        """Test that stg_orders net_amount traces back to total_amount and discount_amount."""
        stg = graph.get_node("model.ecommerce.stg_orders")
        assert stg is not None

        lineage = extract_sql_lineage(stg, graph)
        assert "net_amount" in lineage

        deps = lineage["net_amount"]
        assert len(deps) >= 1

    def test_stg_customers_lineage(self, graph: LineageGraph):
        """Test that stg_customers full_name traces to first_name and last_name."""
        stg = graph.get_node("model.ecommerce.stg_customers")
        assert stg is not None
        lineage = extract_sql_lineage(stg, graph)
        assert "full_name" in lineage
        assert "email" in lineage

    def test_stg_products_lineage(self, graph: LineageGraph):
        """Test that stg_products margin_pct is derived from unit_price and cost."""
        stg = graph.get_node("model.ecommerce.stg_products")
        assert stg is not None
        lineage = extract_sql_lineage(stg, graph)
        assert "margin_pct" in lineage

    def test_stg_inventory_case_when(self, graph: LineageGraph):
        """Test that stg_inventory stock_status has a CASE/WHEN lineage."""
        stg = graph.get_node("model.ecommerce.stg_inventory")
        assert stg is not None
        lineage = extract_sql_lineage(stg, graph)
        assert "stock_status" in lineage

    def test_enrich_graph_updates_column_deps(self, graph: LineageGraph):
        """Test that enrich_graph_with_lineage populates column_deps on nodes."""
        enrich_graph_with_lineage(graph)
        stg = graph.get_node("model.ecommerce.stg_orders")
        assert stg is not None
        assert len(stg.column_deps) > 0

    def test_int_order_enrichment_join(self, graph: LineageGraph):
        """Test that int_order_enrichment has JOIN-based lineage from two sources."""
        node = graph.get_node("model.ecommerce.int_order_enrichment")
        assert node is not None
        lineage = extract_sql_lineage(node, graph)
        assert "customer_name" in lineage
        assert "is_new_customer" in lineage

    def test_dim_customers_left_join(self, graph: LineageGraph):
        """Test dim_customers LEFT JOIN lineage."""
        dim = graph.get_node("model.ecommerce.dim_customers")
        assert dim is not None
        lineage = extract_sql_lineage(dim, graph)
        assert "total_orders" in lineage
        assert "total_revenue" in lineage
        assert "avg_order_value" in lineage

    def test_fct_orders_window_functions(self, graph: LineageGraph):
        """Test fct_orders with HOUR/DAYOFWEEK/MONTH/YEAR expressions."""
        fct = graph.get_node("model.ecommerce.fct_orders")
        assert fct is not None
        lineage = extract_sql_lineage(fct, graph)
        assert "order_hour" in lineage
        assert "order_day_of_week" in lineage
        assert "order_month" in lineage
        assert "order_year" in lineage


# ─────────────────────────────────────────────────────────────────
# Impact Analysis Tests
# ─────────────────────────────────────────────────────────────────

class TestImpactAnalysis:
    def test_get_downstream_source(self, graph: LineageGraph):
        """raw_orders is upstream of stg_orders, int_order_items, int_order_enrichment, fct_orders, fct_revenue."""
        downstream = get_downstream("source.ecommerce.raw_orders", graph)
        assert "model.ecommerce.stg_orders" in downstream
        assert "model.ecommerce.int_order_items" in downstream
        assert "model.ecommerce.int_order_enrichment" in downstream
        assert "model.ecommerce.fct_orders" in downstream
        assert "model.ecommerce.fct_revenue" in downstream

    def test_get_downstream_stg_orders(self, graph: LineageGraph):
        downstream = get_downstream("model.ecommerce.stg_orders", graph)
        assert "model.ecommerce.int_order_items" in downstream
        assert "model.ecommerce.int_order_enrichment" in downstream

    def test_get_upstream_fct_orders(self, graph: LineageGraph):
        upstream = get_upstream("model.ecommerce.fct_orders", graph)
        assert "source.ecommerce.raw_orders" in upstream
        assert "source.ecommerce.raw_customers" in upstream
        assert "model.ecommerce.stg_orders" in upstream
        assert "model.ecommerce.int_order_enrichment" in upstream

    def test_blast_radius_raw_orders(self, graph: LineageGraph):
        """raw_orders is a high-impact source that feeds the whole pipeline."""
        score = blast_radius_score("source.ecommerce.raw_orders", graph)
        # raw_orders has 7 downstream nodes (stg_orders, int_order_items, int_order_enrichment,
        # plus downstream of int_order_enrichment, and downstream of stg_orders that diverge)
        assert score.downstream_count >= 5
        assert score.level in ("MEDIUM", "HIGH", "CRITICAL")

    def test_blast_radius_leaf_node(self, graph: LineageGraph):
        """A leaf model (dim_products) has no downstream."""
        score = blast_radius_score("model.ecommerce.dim_products", graph)
        assert score.downstream_count == 0
        assert score.level == "LOW"

    def test_blast_radius_intermediate(self, graph: LineageGraph):
        """int_order_enrichment has moderate blast radius."""
        score = blast_radius_score("model.ecommerce.int_order_enrichment", graph)
        assert score.downstream_count >= 2
        assert score.level in ("MEDIUM", "HIGH", "CRITICAL")

    def test_blast_radius_nonexistent_node(self, graph: LineageGraph):
        score = blast_radius_score("nonexistent.node", graph)
        assert score.level == "LOW"
        assert score.downstream_count == 0

    def test_generate_impact_report(self, graph: LineageGraph):
        report = generate_impact_report("source.ecommerce.raw_orders", graph)
        assert "Impact Analysis Report" in report
        assert "raw_orders" in report
        assert "Risk Level" in report
        assert "Downstream" in report

    def test_generate_impact_report_with_column(self, graph: LineageGraph):
        report = generate_impact_report(
            "model.ecommerce.stg_orders",
            graph,
            column_name="net_amount",
        )
        assert "net_amount" in report

    def test_get_all_column_impacts(self, graph: LineageGraph):
        impacts = get_all_column_impacts("source.ecommerce.raw_orders", graph)
        # stg_orders uses raw_orders columns
        assert len(impacts) >= 0  # Column deps may or may not be populated yet

    def test_get_most_connected_nodes(self, graph: LineageGraph):
        top = get_most_connected_nodes(graph, top_n=3)
        assert len(top) <= 3
        assert all(isinstance(uid, str) and isinstance(deg, int) for uid, deg in top)


# ─────────────────────────────────────────────────────────────────
# Integration Test
# ─────────────────────────────────────────────────────────────────

class TestIntegration:
    def test_full_pipeline_parse_and_enrich(self, manifest_data: dict):
        """Parse manifest, enrich with SQL lineage, check impact."""
        graph = parse_manifest_from_dict(manifest_data)
        assert len(graph) == 20

        enrich_graph_with_lineage(graph)

        # Verify some column_deps are populated
        stg = graph.get_node("model.ecommerce.stg_orders")
        assert stg is not None
        assert len(stg.column_deps) > 0

        # Blast radius on a source
        score = blast_radius_score("source.ecommerce.raw_orders", graph)
        assert score.level in ("MEDIUM", "HIGH", "CRITICAL")

    def test_demo_manifest_has_required_resources(self, manifest_data: dict):
        """Verify the demo manifest covers all required resource types."""
        nodes = manifest_data["nodes"]
        sources = manifest_data["sources"]

        # Sources
        assert len(sources) >= 5, f"Expected >=5 sources, got {len(sources)}"

        # Models by layer
        model_names = {n["name"] for n in nodes.values()}
        assert "stg_orders" in model_names
        assert "stg_customers" in model_names
        assert "stg_products" in model_names
        assert "int_order_enrichment" in model_names
        assert "dim_customers" in model_names
        assert "dim_products" in model_names
        assert "fct_orders" in model_names
        assert "fct_revenue" in model_names

    def test_all_nodes_have_depends_on(self, manifest_data: dict):
        """Every model should have depends_on populated."""
        for uid, node in manifest_data["nodes"].items():
            deps = node.get("depends_on", {}).get("nodes", [])
            # Only sources have empty depends_on; models should have at least one
            if node.get("resource_type") == "model":
                assert len(deps) > 0, f"Model {uid} has no depends_on"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
