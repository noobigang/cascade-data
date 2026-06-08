"""Impact search panel — blast radius analysis."""


import networkx as nx
import streamlit as st


def _risk_emoji(count: int) -> tuple[str, str, str]:
    """Return emoji and label for blast radius count."""
    if count <= 3:
        return "🟢", "Low", "#39D353"
    elif count <= 20:
        return "🟡", "Medium", "#D29922"
    else:
        return "🔴", "High", "#F85149"


def render_search_panel(dag: nx.DiGraph | None, key: str = "search") -> str | None:
    """
    Render the impact search panel.

    Args:
        dag: NetworkX DiGraph to search in.
        key: Streamlit widget key prefix.

    Returns:
        The selected model name string, or None.
    """
    st.markdown("### 🔍 Impact Search")

    query = st.text_input(
        "Model or model.column name",
        placeholder="e.g. dim_customers or dim_customers.user_id",
        help="Search for a model or column to see its blast radius.",
        key=f"{key}_input",
    )

    if not query or dag is None or len(dag.nodes) == 0:
        return None

    # Find matching node
    # Support both "model" and "model.column" formats
    query_lower = query.lower()
    candidates = [
        n for n in dag.nodes
        if query_lower in n.lower()
    ]

    if not candidates:
        st.warning(f"No matches found for: `{query}`")
        return None

    # Show matches
    with st.expander(f"📋 {len(candidates)} match(es) found", expanded=True):
        selected = None
        for candidate in candidates[:10]:
            data = dag.nodes[candidate]
            rtype = data.get("resource_type", "?")
            col_str = ""
            if "columns" in data:
                col_str = f" ({len(data['columns'])} cols)"
            if st.button(
                f"`{candidate}` [{rtype}]{col_str}",
                key=f"{key}_btn_{candidate}",
                use_container_width=True,
            ):
                selected = candidate

        if len(candidates) > 10:
            st.caption(f"... and {len(candidates) - 10} more")

    return selected


def render_blast_radius(dag: nx.DiGraph | None, model_name: str) -> None:
    """
    Render blast radius details for a given model.

    Args:
        dag: NetworkX DiGraph.
        model_name: Full node name to analyze.
    """
    if dag is None or model_name not in dag.nodes:
        return

    # Calculate downstream
    downstream = list(nx.descendants(dag, model_name))
    upstream = list(nx.ancestors(dag, model_name))
    downstream_count = len(downstream)
    upstream_count = len(upstream)

    # Risk score
    emoji, label, color = _risk_emoji(downstream_count)

    st.markdown("#### Blast Radius")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("🔽 Upstream", upstream_count)
    with col2:
        st.metric("🔽 Downstream", downstream_count)
    with col3:
        st.markdown(f"{emoji} **{label}**")

    # Top downstream models
    if downstream:
        st.markdown("**Top downstream models:**")
        # Sort by reverse topological distance
        sorted_downstream = sorted(
            downstream,
            key=lambda n: len(list(nx.descendants(dag, n))),
            reverse=True,
        )[:5]
        for i, node in enumerate(sorted_downstream, 1):
            rtype = dag.nodes[node].get("resource_type", "?")
            desc = dag.nodes[node].get("description", "")
            desc_short = desc[:60] + "..." if len(desc) > 60 else desc
            st.markdown(f"{i}. `{node}` [{rtype}]")
            if desc_short:
                st.caption(f"   {desc_short}")

    # Upstream paths (column-level)
    if upstream:
        st.markdown("**Upstream sources:**")
        for node in upstream[:5]:
            rtype = dag.nodes[node].get("resource_type", "?")
            st.markdown(f"- `{node}` [{rtype}]")


def render_upstream_column(dag: nx.DiGraph | None, model_name: str, column: str) -> None:
    """
    Show column-level upstream lineage path.

    Args:
        dag: NetworkX DiGraph.
        model_name: Model name.
        column: Column name.
    """
    if dag is None or model_name not in dag.nodes:
        return

    # Build upstream path
    ancestors = list(nx.ancestors(dag, model_name))
    if not ancestors:
        st.info("No upstream sources found.")
        return

    st.markdown(f"#### Column: `{column}`")

    # Simple path: show which source models feed this column
    upstream_sources = [
        n for n in ancestors
        if "source" in n.lower() or "seed" in n.lower()
    ]

    if upstream_sources:
        st.markdown("**Source path:**")
        for node in upstream_sources:
            st.markdown(f"  ↖️ `{node}`")
    else:
        st.info("No direct source found — column may be derived.")
