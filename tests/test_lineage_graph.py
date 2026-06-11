"""
test_lineage_graph.py — Tests for the LineageGraph data structure.

The legacy version of this file imported a `cascade.graph.lineage_graph`
module that no longer exists. The project has since been restructured to
use a single `LineageGraph` class in `lineage.models` wrapping NetworkX.

These tests cover the real API: `parse_manifest_from_dict` returns a
`LineageGraph`, and the graph supports the operations the UI needs
(successors, predecessors, ancestors, descendants, filter_by_type, search,
subgraph, node counts, etc.).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lineage.models import LineageGraph, TableNode
from lineage.parser import parse_manifest_from_dict

FIXTURE_MANIFEST = Path(__file__).parent / "fixtures" / "manifest.json"


# ─────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────

@pytest.fixture
def fixture_manifest() -> dict:
    with open(FIXTURE_MANIFEST, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def graph(fixture_manifest) -> LineageGraph:
    return parse_manifest_from_dict(fixture_manifest)


# ─────────────────────────────────────────────────────────────────
# Build & node count
# ─────────────────────────────────────────────────────────────────

class TestBuildLineageGraph:
    def test_returns_lineage_graph(self, fixture_manifest):
        g = parse_manifest_from_dict(fixture_manifest)
        assert isinstance(g, LineageGraph)

    def test_node_count(self, graph: LineageGraph):
        # 5 models + 1 source + 1 seed = 7 (test.* excluded)
        assert len(graph) == 7

    def test_edge_count(self, graph: LineageGraph):
        # raw_source -> raw_users, raw_users -> stg_users, raw_users -> orders,
        # stg_users -> customers, customers -> reports, orders -> reports
        assert len(graph.edges) == 6

    def test_node_attributes_preserved(self, graph: LineageGraph):
        customers = graph.get_node("model.my_project.customers")
        assert customers is not None
        assert customers.name == "customers"
        assert customers.resource_type == "model"
        # Schema is parsed from relation_name which the fixture doesn't include.
        # Populated schema assertions live in test_lineage.py against the
        # demo manifest.
        assert "user_id" in customers.columns

    def test_source_node(self, graph: LineageGraph):
        source = graph.get_node("source.my_project.raw_source")
        assert source is not None
        assert source.resource_type == "source"

    def test_seed_node(self, graph: LineageGraph):
        seed = graph.get_node("seed.my_project.seed_countries")
        assert seed is not None
        assert seed.resource_type == "seed"

    def test_test_node_excluded(self, graph: LineageGraph):
        assert "test.my_project.unique_users" not in graph.nodes


# ─────────────────────────────────────────────────────────────────
# Traversal: predecessors / successors / ancestors / descendants
# ─────────────────────────────────────────────────────────────────

class TestTraversal:
    def test_predecessors(self, graph: LineageGraph):
        assert "source.my_project.raw_source" in graph.predecessors("model.my_project.raw_users")
        assert "model.my_project.stg_users" in graph.predecessors("model.my_project.customers")

    def test_successors(self, graph: LineageGraph):
        assert "model.my_project.raw_users" in graph.successors("source.my_project.raw_source")
        assert "model.my_project.reports" in graph.successors("model.my_project.customers")

    def test_ancestors_full_chain(self, graph: LineageGraph):
        # reports is terminal — its ancestors are the full chain
        ancestors = graph.ancestors("model.my_project.reports")
        assert "model.my_project.customers" in ancestors
        assert "model.my_project.stg_users" in ancestors
        assert "source.my_project.raw_source" in ancestors

    def test_descendants(self, graph: LineageGraph):
        # raw_source feeds nearly everything
        desc = graph.descendants("source.my_project.raw_source")
        assert "model.my_project.reports" in desc
        assert "model.my_project.orders" in desc

    def test_root_has_no_predecessors(self, graph: LineageGraph):
        assert graph.predecessors("source.my_project.raw_source") == []

    def test_leaf_has_no_successors(self, graph: LineageGraph):
        assert graph.successors("model.my_project.reports") == []


# ─────────────────────────────────────────────────────────────────
# Filtering & search
# ─────────────────────────────────────────────────────────────────

class TestFiltering:
    def test_filter_by_type(self, graph: LineageGraph):
        sources_only = graph.filter_by_type("source")
        assert len(sources_only) == 1
        assert "source.my_project.raw_source" in sources_only.nodes

    def test_filter_by_type_models(self, graph: LineageGraph):
        models_only = graph.filter_by_type("model")
        assert len(models_only) == 5
        # Edges that involve only models should be preserved.
        # Edges involving a non-model node are dropped.
        for src, tgt in models_only.edges:
            src_node = models_only.get_node(src)
            tgt_node = models_only.get_node(tgt)
            assert src_node.resource_type == "model"
            assert tgt_node.resource_type == "model"

    def test_filter_by_type_empty(self, graph: LineageGraph):
        nothing = graph.filter_by_type("nonexistent_type")
        assert len(nothing) == 0
        assert nothing.edges == []

    def test_search_by_name(self, graph: LineageGraph):
        results = graph.search("customer")
        assert any(n.name == "customers" for n in results)

    def test_search_case_insensitive(self, graph: LineageGraph):
        upper = graph.search("CUSTOMER")
        lower = graph.search("customer")
        assert {n.unique_id for n in upper} == {n.unique_id for n in lower}

    def test_search_by_column_name(self, graph: LineageGraph):
        results = graph.search("user_id")
        # Multiple nodes have a user_id column
        assert len(results) >= 2

    def test_search_no_match(self, graph: LineageGraph):
        assert graph.search("xyznomatch") == []


# ─────────────────────────────────────────────────────────────────
# Subgraph
# ─────────────────────────────────────────────────────────────────

class TestSubgraph:
    def test_subgraph_size(self, graph: LineageGraph):
        sub = graph.subgraph({"model.my_project.customers", "model.my_project.reports"})
        assert len(sub) == 2
        assert "model.my_project.customers" in sub.nodes
        assert "model.my_project.reports" in sub.nodes

    def test_subgraph_drops_unmentioned(self, graph: LineageGraph):
        sub = graph.subgraph({"model.my_project.customers", "model.my_project.reports"})
        assert "model.my_project.stg_users" not in sub.nodes

    def test_subgraph_preserves_internal_edges(self, graph: LineageGraph):
        sub = graph.subgraph({"model.my_project.customers", "model.my_project.reports"})
        # The customers -> reports edge should still be there
        assert ("model.my_project.customers", "model.my_project.reports") in sub.edges


# ─────────────────────────────────────────────────────────────────
# Mutability & safety
# ─────────────────────────────────────────────────────────────────

class TestGraphOperations:
    def test_add_node(self):
        g = LineageGraph()
        node = TableNode(unique_id="model.t.a", name="a", resource_type="model")
        g.add_node(node)
        assert g.has_node("model.t.a")
        assert len(g) == 1

    def test_remove_node(self, graph: LineageGraph):
        graph.remove_node("model.my_project.reports")
        assert not graph.has_node("model.my_project.reports")
        # Edges incident to it are dropped.
        for src, tgt in graph.edges:
            assert src != "model.my_project.reports"
            assert tgt != "model.my_project.reports"

    def test_empty_graph(self):
        g = LineageGraph()
        assert len(g) == 0
        assert g.nodes == []
        assert g.edges == []

    def test_get_missing_node_returns_none(self, graph: LineageGraph):
        assert graph.get_node("model.my_project.does_not_exist") is None

    def test_repr_includes_counts(self, graph: LineageGraph):
        # Cheap smoke test that __repr__ doesn't crash and includes key info.
        r = repr(graph)
        assert "LineageGraph" in r
        assert "nodes" in r
        assert "edges" in r


# ─────────────────────────────────────────────────────────────────
# Graph stats (computed on the fly)
# ─────────────────────────────────────────────────────────────────

class TestGraphStats:
    def test_compute_basic_stats(self, graph: LineageGraph):
        models = sum(1 for uid in graph.nodes if graph.get_node(uid).resource_type == "model")
        sources = sum(1 for uid in graph.nodes if graph.get_node(uid).resource_type == "source")
        seeds = sum(1 for uid in graph.nodes if graph.get_node(uid).resource_type == "seed")
        assert models == 5
        assert sources == 1
        assert seeds == 1

    def test_terminal_nodes(self, graph: LineageGraph):
        # Nodes with no successors
        terminal = [uid for uid in graph.nodes if not graph.successors(uid)]
        # reports is the only model with no downstream
        assert "model.my_project.reports" in terminal

    def test_root_nodes(self, graph: LineageGraph):
        # Nodes with no predecessors
        root = [uid for uid in graph.nodes if not graph.predecessors(uid)]
        assert "source.my_project.raw_source" in root
        assert "seed.my_project.seed_countries" in root
