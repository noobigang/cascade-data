"""
test_lineage_graph.py — Tests for lineage_graph.py.
"""


import pytest

from cascade.graph.lineage_graph import (
    add_column_edges,
    build_lineage_graph,
    get_downstream_columns,
    get_node_columns,
    get_upstream_columns,
    graph_stats,
)
from cascade.parser.manifest_parser import parse_manifest_from_dict


@pytest.fixture
def graph(manifest_data):
    nodes = parse_manifest_from_dict(manifest_data)
    return build_lineage_graph(nodes)


class TestBuildLineageGraph:
    def test_nodes_added(self, graph):
        assert graph.number_of_nodes() == 7

    def test_edges_added(self, graph):
        # edges: raw_source->raw_users, raw_users->stg_users, raw_users->orders,
        # stg_users->customers, customers->reports, orders->reports
        assert graph.number_of_edges() == 6

    def test_node_attributes(self, graph):
        customers = graph.nodes["model.my_project.customers"]
        assert customers["name"] == "customers"
        assert customers["resource_type"] == "model"
        assert customers["schema"] == "analytics"
        assert "columns" in customers

    def test_source_node(self, graph):
        source = graph.nodes["source.my_project.raw_source"]
        assert source["resource_type"] == "source"

    def test_seed_node(self, graph):
        seed = graph.nodes["seed.my_project.seed_countries"]
        assert seed["resource_type"] == "seed"

    def test_test_node_excluded(self, graph):
        # test nodes should not appear as graph nodes
        node_ids = list(graph.nodes())
        assert "test.my_project.unique_users" not in node_ids


class TestColumnEdges:
    def test_upstream_columns(self, graph):
        # customers depends on stg_users, both have user_id
        up = get_upstream_columns(graph, "model.my_project.customers", "user_id")
        assert "model.my_project.stg_users.user_id" in up

    def test_downstream_columns(self, graph):
        # raw_users has user_id, stg_users and orders both downstream with user_id
        # (customers has user_id too but is reached via stg_users BFS first)
        down = get_downstream_columns(graph, "model.my_project.raw_users", "user_id")
        assert len(down) == 2
        assert "model.my_project.stg_users.user_id" in down
        assert "model.my_project.orders.user_id" in down

    def test_no_matching_column(self, graph):
        # reports has total_amount, raw_users does not
        down = get_downstream_columns(graph, "model.my_project.raw_users", "total_amount")
        assert down == []


class TestAddColumnEdges:
    def test_add_explicit_column_edge(self, graph):
        # Manually connect raw_source.user_id to orders.user_id (both have user_id)
        add_column_edges(
            graph,
            "source.my_project.raw_source",
            "model.my_project.orders",
            "user_id",
            "user_id",
        )
        up = get_upstream_columns(graph, "model.my_project.orders", "user_id")
        assert "source.my_project.raw_source.user_id" in up


class TestGraphStats:
    def test_stats(self, graph):
        stats = graph_stats(graph)
        assert stats["nodes"] == 7
        assert stats["edges"] == 6
        assert stats["models"] == 5
        assert stats["sources"] == 1
        assert stats["seeds"] == 1

    def test_terminal_nodes(self, graph):
        stats = graph_stats(graph)
        # Terminal = no outgoing edges: reports (only model downstream), orders
        assert stats["terminal_nodes"] == 2

    def test_root_nodes(self, graph):
        stats = graph_stats(graph)
        # Root = no incoming edges: raw_source, seed_countries
        assert stats["root_nodes"] == 2


class TestGetNodeColumns:
    def test_existing_node(self, graph):
        cols = get_node_columns(graph, "model.my_project.customers")
        assert "user_id" in cols
        assert "name" in cols

    def test_missing_node(self, graph):
        cols = get_node_columns(graph, "model.my_project.does_not_exist")
        assert cols == {}


class TestEmptyGraph:
    def test_empty_nodes_list(self):
        graph = build_lineage_graph([])
        assert graph.number_of_nodes() == 0
        assert graph.number_of_edges() == 0
