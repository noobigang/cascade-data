"""Model detail panel — slide-up view on node click."""


import networkx as nx
import streamlit as st


def render_detail_panel(dag: nx.DiGraph | None, model_name: str | None) -> None:
    """
    Render a detail panel for the selected model.
    Uses st.expander as a slide-up panel.

    Args:
        dag: NetworkX DiGraph.
        model_name: Full node name selected in the DAG.
    """
    if model_name is None:
        return

    if dag is None or model_name not in dag.nodes:
        st.warning(f"Model `{model_name}` not found in graph.")
        return

    data = dag.nodes[model_name]
    resource_type = data.get("resource_type", "unknown")
    description = data.get("description", "")
    schema = data.get("schema", "")

    st.markdown("---")
    st.markdown(f"### 📄 `{model_name}`")
    st.caption(f"Type: **{resource_type}** | Schema: **{schema}**")

    if description:
        st.markdown(f"_{description}_")

    # Columns
    columns = data.get("columns", {})
    if columns:
        with st.expander(f"📊 Columns ({len(columns)})"):
            col_data = []
            for col_name, col_info in columns.items():
                dtype = col_info.get("data_type", "?")
                col_desc = col_info.get("description", "")
                col_data.append({
                    "Column": col_name,
                    "Type": dtype,
                    "Description": col_desc or "—",
                })
            st.dataframe(col_data, use_container_width=True, hide_index=True)
    else:
        st.caption("No column metadata available.")

    # Upstream and Downstream
    upstream = list(dag.predecessors(model_name))
    downstream = list(dag.successors(model_name))

    col_up, col_down = st.columns(2)

    with col_up:
        st.markdown("**⬆️ Upstream**")
        if upstream:
            for node in upstream[:8]:
                rtype = dag.nodes[node].get("resource_type", "?")
                st.markdown(f"- `{node}` [{rtype}]")
            if len(upstream) > 8:
                st.caption(f"... and {len(upstream) - 8} more")
        else:
            st.caption("No upstream dependencies.")

    with col_down:
        st.markdown("**⬇️ Downstream**")
        if downstream:
            for node in downstream[:8]:
                rtype = dag.nodes[node].get("resource_type", "?")
                st.markdown(f"- `{node}` [{rtype}]")
            if len(downstream) > 8:
                st.caption(f"... and {len(downstream) - 8} more")
        else:
            st.caption("No downstream dependents.")

    st.markdown("---")


def render_stats_sidebar(dag: nx.DiGraph | None) -> None:
    """
    Render a stats summary in the sidebar.

    Args:
        dag: NetworkX DiGraph.
    """
    if dag is None or len(dag.nodes) == 0:
        st.markdown("**📊 Stats**")
        st.caption("No data loaded.")
        return

    nodes = list(dag.nodes)
    edges = list(dag.edges)

    # Count by resource type
    resource_counts: dict[str, int] = {}
    for node in nodes:
        rtype = dag.nodes[node].get("resource_type", "unknown")
        resource_counts[rtype] = resource_counts.get(rtype, 0) + 1

    st.markdown("**📊 Stats**")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Models", resource_counts.get("model", 0))
    with col2:
        st.metric("Sources", resource_counts.get("source", 0))

    col3, col4 = st.columns(2)
    with col3:
        st.metric("Seeds", resource_counts.get("seed", 0))
    with col4:
        st.metric("Edges", len(edges))

    st.divider()
    st.markdown("**Resource types**")
    for rtype, count in sorted(resource_counts.items()):
        st.caption(f"- {rtype}: {count}")
