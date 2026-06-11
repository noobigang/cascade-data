"""
test_impact_analyzer.py — Tests for the impact analyzer (lineage/impact.py).

Targets the real API in `lineage.impact`. Replaces the legacy
`cascade.graph.impact_analyzer` import path that pointed at a now-deleted
package layout.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

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
from lineage.models import LineageGraph
from lineage.parser import parse_manifest_from_dict

DEMO_MANIFEST = Path(__file__).parent.parent / "demo" / "manifest.json"
FIXTURE_MANIFEST = Path(__file__).parent / "fixtures" / "manifest.json"


# ─────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────

@pytest.fixture
def demo_manifest() -> dict:
    with open(DEMO_MANIFEST, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def demo_graph(demo_manifest) -> LineageGraph:
    return parse_manifest_from_dict(demo_manifest)


@pytest.fixture
def fixture_graph() -> LineageGraph:
    with open(FIXTURE_MANIFEST, encoding="utf-8") as f:
        return parse_manifest_from_dict(json.load(f))


# ─────────────────────────────────────────────────────────────────
# get_downstream
# ─────────────────────────────────────────────────────────────────

class TestGetDownstream:
    def test_from_source_reaches_everything(self, demo_graph: LineageGraph):
        downstream = get_downstream("source.ecommerce.raw_orders", demo_graph)
        assert "model.ecommerce.stg_orders" in downstream
        assert "model.ecommerce.int_order_items" in downstream
        assert "model.ecommerce.int_order_enrichment" in downstream
        assert "model.ecommerce.fct_orders" in downstream
        assert "model.ecommerce.fct_revenue" in downstream

    def test_from_intermediate_stg_orders(self, demo_graph: LineageGraph):
        downstream = get_downstream("model.ecommerce.stg_orders", demo_graph)
        assert "model.ecommerce.int_order_items" in downstream
        assert "model.ecommerce.int_order_enrichment" in downstream

    def test_from_terminal_node_is_empty(self, fixture_graph: LineageGraph):
        assert get_downstream("model.my_project.reports", fixture_graph) == []

    def test_from_missing_node_is_empty(self, fixture_graph: LineageGraph):
        # Should not raise — just return []
        assert get_downstream("model.my_project.does_not_exist", fixture_graph) == []

    def test_excludes_self(self, demo_graph: LineageGraph):
        downstream = get_downstream("source.ecommerce.raw_orders", demo_graph)
        assert "source.ecommerce.raw_orders" not in downstream

    def test_returns_list_type(self, fixture_graph: LineageGraph):
        result = get_downstream("source.my_project.raw_source", fixture_graph)
        assert isinstance(result, list)


# ─────────────────────────────────────────────────────────────────
# get_upstream
# ─────────────────────────────────────────────────────────────────

class TestGetUpstream:
    def test_from_terminal_walks_full_chain(self, fixture_graph: LineageGraph):
        up = get_upstream("model.my_project.reports", fixture_graph)
        assert "model.my_project.customers" in up
        assert "model.my_project.orders" in up
        assert "model.my_project.stg_users" in up
        assert "model.my_project.raw_users" in up
        assert "source.my_project.raw_source" in up

    def test_from_source_is_empty(self, fixture_graph: LineageGraph):
        assert get_upstream("source.my_project.raw_source", fixture_graph) == []

    def test_from_fct_orders(self, demo_graph: LineageGraph):
        up = get_upstream("model.ecommerce.fct_orders", demo_graph)
        assert "source.ecommerce.raw_orders" in up
        assert "model.ecommerce.stg_orders" in up
        assert "model.ecommerce.int_order_enrichment" in up

    def test_from_missing_node_is_empty(self, fixture_graph: LineageGraph):
        assert get_upstream("model.my_project.does_not_exist", fixture_graph) == []

    def test_excludes_self(self, demo_graph: LineageGraph):
        up = get_upstream("source.ecommerce.raw_orders", demo_graph)
        assert "source.ecommerce.raw_orders" not in up


# ─────────────────────────────────────────────────────────────────
# blast_radius_score
# ─────────────────────────────────────────────────────────────────

class TestBlastRadiusScore:
    def test_returns_impact_score_object(self, fixture_graph: LineageGraph):
        score = blast_radius_score("model.my_project.orders", fixture_graph)
        # Real API returns an ImpactScore dataclass with `.level` and counts.
        assert hasattr(score, "level")
        assert hasattr(score, "downstream_count")
        assert hasattr(score, "upstream_count")

    def test_low_for_source_with_few_downstream(self, fixture_graph: LineageGraph):
        # raw_source has ~5 downstream nodes — within LOW/MEDIUM band
        score = blast_radius_score("source.my_project.raw_source", fixture_graph)
        assert score.level in ("LOW", "MEDIUM")
        assert score.downstream_count >= 1

    def test_low_for_terminal_node(self, demo_graph: LineageGraph):
        score = blast_radius_score("model.ecommerce.dim_products", demo_graph)
        assert score.downstream_count == 0
        assert score.level == "LOW"

    def test_high_for_central_source(self, demo_graph: LineageGraph):
        # raw_orders feeds nearly the whole pipeline
        score = blast_radius_score("source.ecommerce.raw_orders", demo_graph)
        assert score.downstream_count >= 5
        assert score.level in ("MEDIUM", "HIGH", "CRITICAL")

    def test_intermediate_radius(self, demo_graph: LineageGraph):
        score = blast_radius_score("model.ecommerce.int_order_enrichment", demo_graph)
        assert score.downstream_count >= 2

    def test_missing_node_returns_low(self, demo_graph: LineageGraph):
        score = blast_radius_score("nonexistent.node", demo_graph)
        assert score.level == "LOW"
        assert score.downstream_count == 0

    def test_thresholds_boundaries(self, demo_graph: LineageGraph):
        # All nodes should fall into one of the four defined levels
        for uid in demo_graph.nodes:
            score = blast_radius_score(uid, demo_graph)
            assert score.level in ("LOW", "MEDIUM", "HIGH", "CRITICAL")


# ─────────────────────────────────────────────────────────────────
# generate_impact_report
# ─────────────────────────────────────────────────────────────────

class TestGenerateImpactReport:
    def test_report_has_header(self, demo_graph: LineageGraph):
        report = generate_impact_report("source.ecommerce.raw_orders", demo_graph)
        assert "Impact Analysis Report" in report
        assert "raw_orders" in report
        assert "Risk Level" in report
        assert "Downstream" in report

    def test_report_with_column_focus(self, demo_graph: LineageGraph):
        report = generate_impact_report(
            "model.ecommerce.stg_orders",
            demo_graph,
            column_name="net_amount",
        )
        assert "net_amount" in report
        assert "Column-Level Impact" in report

    def test_report_for_missing_node(self, demo_graph: LineageGraph):
        report = generate_impact_report("nonexistent.node", demo_graph)
        assert "not found" in report.lower()

    def test_report_includes_compiled_sql_section(self, demo_graph: LineageGraph):
        report = generate_impact_report("model.ecommerce.stg_orders", demo_graph)
        assert "Compiled SQL" in report


# ─────────────────────────────────────────────────────────────────
# get_column_impact + get_all_column_impacts
# ─────────────────────────────────────────────────────────────────

class TestColumnImpact:
    def test_returns_list_of_tuples(self, demo_graph: LineageGraph):
        # Column impact requires the graph to be enriched with column_deps.
        from lineage.sql_lineage import enrich_graph_with_lineage
        enrich_graph_with_lineage(demo_graph)

        impact = get_column_impact("source.ecommerce.raw_orders", "order_id", demo_graph)
        assert isinstance(impact, list)
        # Each entry is (table_uid, column_name)
        for entry in impact:
            assert isinstance(entry, tuple)
            assert len(entry) == 2

    def test_change_to_source_column_reaches_consumers(self, demo_graph: LineageGraph):
        from lineage.sql_lineage import enrich_graph_with_lineage
        enrich_graph_with_lineage(demo_graph)

        impact = get_column_impact("source.ecommerce.raw_orders", "order_id", demo_graph)
        # Should at least affect stg_orders.order_id
        affected_cols = {col for _uid, col in impact}
        assert "order_id" in affected_cols

    def test_direct_consumer_appears(self, demo_graph: LineageGraph):
        """A column in a directly downstream model is in the impact set."""
        from lineage.sql_lineage import enrich_graph_with_lineage
        enrich_graph_with_lineage(demo_graph)

        impact = get_column_impact("source.ecommerce.raw_orders", "order_id", demo_graph)
        affected = {(uid, col) for uid, col in impact}
        # stg_orders.order_id is derived from raw_orders.order_id
        assert ("model.ecommerce.stg_orders", "order_id") in affected

    def test_transitive_propagation(self, demo_graph: LineageGraph):
        """A column change in a source reaches all transitive consumers.

        e.g. raw_orders.order_id -> stg_orders.order_id -> int_order_items.order_id.
        Both stg_orders.order_id AND int_order_items.order_id should be in the
        impact set. The old (broken) implementation only walked one hop.
        """
        from lineage.sql_lineage import enrich_graph_with_lineage
        enrich_graph_with_lineage(demo_graph)

        impact = get_column_impact("source.ecommerce.raw_orders", "order_id", demo_graph)
        affected = {(uid, col) for uid, col in impact}
        # Direct consumer
        assert ("model.ecommerce.stg_orders", "order_id") in affected
        # Transitive consumer (2 hops down) where the column name is preserved
        assert ("model.ecommerce.int_order_items", "order_id") in affected

    def test_transitive_propagation_through_aliased_column(self, demo_graph: LineageGraph):
        """Propagation also reaches columns that are aliased through
        intermediate models.

        raw_orders.order_id -> stg_orders.order_id -> int_order_enrichment.o.order_id
        (the int_order_enrichment model aliases the column to `o.order_id`).
        """
        from lineage.sql_lineage import enrich_graph_with_lineage
        enrich_graph_with_lineage(demo_graph)

        impact = get_column_impact("source.ecommerce.raw_orders", "order_id", demo_graph)
        affected = {(uid, col) for uid, col in impact}
        assert ("model.ecommerce.int_order_enrichment", "o.order_id") in affected

    def test_unrelated_column_not_affected(self, demo_graph: LineageGraph):
        """A column that doesn't flow from the source is NOT in the impact set."""
        from lineage.sql_lineage import enrich_graph_with_lineage
        enrich_graph_with_lineage(demo_graph)

        impact = get_column_impact("source.ecommerce.raw_orders", "order_id", demo_graph)
        affected = {(uid, col) for uid, col in impact}
        # stg_customers has full_name, which comes from first_name + last_name,
        # NOT from raw_orders.order_id. Even though stg_customers is in the
        # graph, (stg_customers, full_name) should not be in the impact set.
        assert ("model.ecommerce.stg_customers", "full_name") not in affected

    def test_column_with_derived_expression(self, demo_graph: LineageGraph):
        """net_amount in stg_orders derives from total_amount + discount_amount.

        Changing raw_orders.total_amount should affect stg_orders.net_amount
        (and transitively any downstream that consumes net_amount).
        """
        from lineage.sql_lineage import enrich_graph_with_lineage
        enrich_graph_with_lineage(demo_graph)

        impact = get_column_impact(
            "source.ecommerce.raw_orders", "total_amount", demo_graph
        )
        affected = {(uid, col) for uid, col in impact}
        assert ("model.ecommerce.stg_orders", "net_amount") in affected

    def test_impact_is_deduplicated(self, demo_graph: LineageGraph):
        """Same (table, column) should never appear twice even with cycles or
        multi-source convergence."""
        from lineage.sql_lineage import enrich_graph_with_lineage
        enrich_graph_with_lineage(demo_graph)

        impact = get_column_impact("source.ecommerce.raw_orders", "order_id", demo_graph)
        # No duplicates allowed
        assert len(impact) == len(set(impact))

    def test_does_not_affect_upstream(self, demo_graph: LineageGraph):
        """Column impact only flows DOWNSTREAM, not upstream."""
        from lineage.sql_lineage import enrich_graph_with_lineage
        enrich_graph_with_lineage(demo_graph)

        impact = get_column_impact("model.ecommerce.stg_orders", "order_id", demo_graph)
        affected_uids = {uid for uid, _col in impact}
        # raw_orders is upstream of stg_orders — must not appear
        assert "source.ecommerce.raw_orders" not in affected_uids

    def test_missing_node_returns_empty(self, demo_graph: LineageGraph):
        impact = get_column_impact("nonexistent.node", "x", demo_graph)
        assert impact == []

    def test_column_with_no_consumers_returns_empty(self, demo_graph: LineageGraph):
        """A column on a leaf node has no downstream impact."""
        from lineage.sql_lineage import enrich_graph_with_lineage
        enrich_graph_with_lineage(demo_graph)

        # dim_products is a leaf (no downstream)
        impact = get_column_impact(
            "model.ecommerce.dim_products", "product_name", demo_graph
        )
        assert impact == []


class TestGetAllColumnImpacts:
    def test_returns_dict(self, demo_graph: LineageGraph):
        impacts = get_all_column_impacts("source.ecommerce.raw_orders", demo_graph)
        assert isinstance(impacts, dict)

    def test_missing_node_returns_empty_dict(self, demo_graph: LineageGraph):
        impacts = get_all_column_impacts("nonexistent.node", demo_graph)
        assert impacts == {}


# ─────────────────────────────────────────────────────────────────
# get_most_connected_nodes
# ─────────────────────────────────────────────────────────────────

class TestMostConnectedNodes:
    def test_returns_top_n(self, demo_graph: LineageGraph):
        top = get_most_connected_nodes(demo_graph, top_n=3)
        assert len(top) <= 3
        assert all(isinstance(uid, str) and isinstance(deg, int) for uid, deg in top)

    def test_sorted_descending(self, demo_graph: LineageGraph):
        top = get_most_connected_nodes(demo_graph, top_n=5)
        degrees = [deg for _uid, deg in top]
        assert degrees == sorted(degrees, reverse=True)

    def test_empty_graph(self):
        empty = LineageGraph()
        assert get_most_connected_nodes(empty) == []


# ─────────────────────────────────────────────────────────────────
# get_deepest_lineage_path
# ─────────────────────────────────────────────────────────────────

class TestDeepestLineagePath:
    def test_returns_list(self, demo_graph: LineageGraph):
        path = get_deepest_lineage_path(demo_graph)
        assert isinstance(path, list)

    def test_empty_graph(self):
        assert get_deepest_lineage_path(LineageGraph()) == []
