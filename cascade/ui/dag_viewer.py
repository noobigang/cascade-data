"""PyVis DAG renderer for Streamlit — dark-themed with glow effects."""

import networkx as nx
from pyvis.network import Network
from streamlit.components.v1 import html as st_html

# Node color map by resource_type
RESOURCE_COLORS = {
    "model": "#58A6FF",     # bright blue
    "source": "#39D353",    # green
    "seed": "#8B949E",      # gray
    "snapshot": "#D29922",  # amber
    "test": "#F85149",      # red
}

# Glow halo colors (slightly lighter than node color)
GLOW_COLORS = {
    "model": "rgba(88, 166, 255, 0.6)",
    "source": "rgba(57, 211, 83, 0.6)",
    "seed": "rgba(139, 148, 158, 0.4)",
    "snapshot": "rgba(210, 153, 34, 0.6)",
    "test": "rgba(248, 81, 73, 0.6)",
}


def _get_color(node_type: str) -> str:
    """Return hex color for a resource type."""
    for key, color in RESOURCE_COLORS.items():
        if key in node_type.lower():
            return color
    return "#8B949E"


def _get_glow(node_type: str) -> str:
    """Return glow color for a resource type."""
    for key, color in GLOW_COLORS.items():
        if key in node_type.lower():
            return color
    return "rgba(139, 148, 158, 0.4)"


def _get_shape(node_type: str) -> str:
    """Return pyvis shape for a resource type."""
    if "source" in node_type.lower():
        return "diamond"
    if "seed" in node_type.lower():
        return "square"
    return "dot"


def _build_tooltip(node_id: str, data: dict, dag: nx.DiGraph) -> str:
    """Build a rich HTML tooltip for a node."""
    resource_type = data.get("resource_type", "unknown")
    schema = data.get("schema", "")
    columns = data.get("columns", {})
    col_count = len(columns)
    description = data.get("description", "")

    # Upstream/downstream counts
    upstream = list(dag.predecessors(node_id))
    downstream = list(dag.successors(node_id))

    tooltip = f"""
    <div style="
        background: #161B22;
        border: 1px solid #30363D;
        border-radius: 8px;
        padding: 12px 16px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px;
        color: #E6EDF3;
        max-width: 280px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.5);
    ">
        <div style="font-size: 14px; font-weight: 600; color: #58A6FF; margin-bottom: 6px;">
            {node_id.split('.')[-1]}
        </div>
        <div style="color: #8B949E; font-size: 11px; margin-bottom: 8px;">
            {node_id}
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 4px; margin-bottom: 8px;">
            <span style="color: #8B949E;">Type:</span>
            <span style="color: {_get_color(resource_type)};">{resource_type}</span>
            <span style="color: #8B949E;">Schema:</span>
            <span style="color: #E6EDF3;">{schema or '—'}</span>
            <span style="color: #8B949E;">Columns:</span>
            <span style="color: #39D353;">{col_count}</span>
            <span style="color: #8B949E;">Upstream:</span>
            <span style="color: #D29922;">{len(upstream)}</span>
            <span style="color: #8B949E;">Downstream:</span>
            <span style="color: #F85149;">{len(downstream)}</span>
        </div>
        {f'<div style="color: #8B949E; font-size: 11px; border-top: 1px solid #30363D; padding-top: 6px;">{description[:80]}{"..." if len(description) > 80 else ""}</div>' if description else ''}
    </div>
    """
    return tooltip


def render_dag(
    dag: nx.DiGraph | None,
    height: int = 600,
    physics_enabled: bool = True,
    selected_node: str | None = None,
) -> None:
    """
    Render an interactive PyVis DAG in Streamlit with dark glow styling.

    Args:
        dag: NetworkX DiGraph. Pass None to show a placeholder.
        height: Height in pixels for the iframe.
        physics_enabled: Whether to enable physics simulation.
        selected_node: Node ID to pre-highlight on load.
    """
    if dag is None or len(dag.nodes) == 0:
        _render_placeholder(height)
        return

    net = Network(
        height=f"{height}px",
        width="100%",
        bgcolor="#0D1117",
        font_color="#E6EDF3",
        directed=True,
        notebook=False,
        select_menu=True,
    )

    # Build highlight set from selected_node and its connections
    highlight_nodes = set()
    highlight_edges = set()
    if selected_node and selected_node in dag.nodes:
        highlight_nodes.add(selected_node)
        for pred in dag.predecessors(selected_node):
            highlight_nodes.add(pred)
            highlight_edges.add((pred, selected_node))
        for succ in dag.successors(selected_node):
            highlight_nodes.add(succ)
            highlight_edges.add((selected_node, succ))
        # Second-degree downstream
        for succ in dag.successors(selected_node):
            for succ2 in dag.successors(succ):
                if succ2 not in highlight_nodes:
                    highlight_nodes.add(succ2)
                    highlight_edges.add((succ, succ2))

    # Physics options — spring_length=200, damping=0.08 per spec
    physics_config = """
        {
            "nodes": {
                "borderWidth": 2,
                "borderWidthSelected": 4,
                "font": {
                    "color": "#E6EDF3",
                    "size": 13,
                    "face": "JetBrains Mono, monospace",
                    "strokeWidth": 3,
                    "strokeColor": "#0D1117"
                },
                "shadow": {
                    "enabled": true,
                    "color": "rgba(88,166,255,0.5)",
                    "size": 16,
                    "x": 0,
                    "y": 4
                }
            },
            "edges": {
                "color": {
                    "color": "#30363D",
                    "highlight": "#58A6FF",
                    "hover": "#58A6FF",
                    "inherit": false
                },
                "width": 1.5,
                "arrows": {
                    "to": {
                        "enabled": true,
                        "scaleFactor": 0.7
                    }
                },
                "smooth": {
                    "type": "cubicBezier",
                    "forceDirection": "none",
                    "roundness": 0.4
                },
                "hoverWidth": 0.3,
                "selectionWidth": 2
            },
            "interaction": {
                "hover": true,
                "navigationButtons": true,
                "keyboard": true,
                "tooltipDelay": 150,
                "tooltipSticky": true,
                "hideEdgesOnDrag": false,
                "zoomView": true
            },
            "physics": {
                "enabled": true,
                "forceAtlas2Based": {
                    "gravitationalConstant": -100,
                    "centralGravity": 0.01,
                    "springLength": 200,
                    "springConstant": 0.08,
                    "damping": 0.08,
                    "avoidOverlap": 0.5
                },
                "minVelocity": 0.75,
                "maxVelocity": 20,
                "solver": "forceAtlas2Based",
                "stabilization": {
                    "enabled": true,
                    "iterations": 200,
                    "updateInterval": 25
                }
            },
            "layout": {
                "improvedLayout": true,
                "hierarchical": {
                    "enabled": false
                }
            }
        }
        """ if physics_enabled else """
        {
            "nodes": {
                "borderWidth": 2,
                "borderWidthSelected": 4,
                "font": {
                    "color": "#E6EDF3",
                    "size": 13,
                    "face": "JetBrains Mono, monospace",
                    "strokeWidth": 3,
                    "strokeColor": "#0D1117"
                },
                "shadow": {
                    "enabled": true,
                    "color": "rgba(88,166,255,0.5)",
                    "size": 16,
                    "x": 0,
                    "y": 4
                }
            },
            "edges": {
                "color": {
                    "color": "#30363D",
                    "highlight": "#58A6FF",
                    "hover": "#58A6FF",
                    "inherit": false
                },
                "width": 1.5,
                "arrows": {
                    "to": {
                        "enabled": true,
                        "scaleFactor": 0.7
                    }
                },
                "smooth": {
                    "type": "cubicBezier",
                    "forceDirection": "none",
                    "roundness": 0.4
                }
            },
            "interaction": {
                "hover": true,
                "navigationButtons": true,
                "keyboard": true,
                "tooltipDelay": 150,
                "tooltipSticky": true,
                "zoomView": true
            },
            "physics": {
                "enabled": false
            },
            "layout": {
                "improvedLayout": true
            }
        }
        """

    net.set_options(physics_config)

    # Add nodes with glow and highlight
    for node_id in dag.nodes:
        data = dag.nodes[node_id]
        resource_type = data.get("resource_type", "unknown")
        color = _get_color(resource_type)
        glow = _get_glow(resource_type)
        shape = _get_shape(resource_type)

        # Node size proportional to downstream count
        downstream_count = len(list(dag.successors(node_id)))
        base_size = 10
        size = base_size + min(downstream_count * 2.5, 30)

        # Label: short name
        label = node_id.split(".")[-1] if "." in node_id else node_id

        # Rich tooltip
        title = _build_tooltip(node_id, data, dag)

        # Highlight state
        is_highlighted = node_id in highlight_nodes

        net.add_node(
            node_id,
            label=label,
            title=title,
            color={
                "background": color,
                "border": "#30363D",
                "highlight": {"background": color, "border": "#58A6FF"},
                "hover": {"background": color, "border": "#58A6FF"},
            },
            size=size,
            shape=shape,
            font={"color": "#E6EDF3", "size": 14},
            borderWidth=2,
            borderWidthSelected=4,
            shadow={"enabled": True, "color": glow, "size": "20" if is_highlighted else "12", "x": 0, "y": 4},
        )

    # Add edges
    for source, target in dag.edges():
        is_highlighted_edge = (source, target) in highlight_edges
        net.add_edge(
            source,
            target,
            color="#58A6FF" if is_highlighted_edge else "#30363D",
            width=2.5 if is_highlighted_edge else 1.2,
            hover="#58A6FF",
        )

    # Get HTML
    html_str = net.generate_html()

    # Inject dark theme + animation CSS + custom tooltip styles into the HTML
    injected_head = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&display=swap');
    body { background-color: #0D1117; margin: 0; padding: 0; overflow: hidden; }
    #network { background-color: #0D1117 !important; }

    /* Node glow pulse on hover — animated */
    .vis-node:hover {
        filter: drop-shadow(0 0 8px currentColor) drop-shadow(0 0 16px rgba(88,166,255,0.4));
        transition: filter 150ms ease-out;
    }

    /* Edge animation on highlight */
    .vis-edge.vis-highlighted {
        animation: edge-pulse 1.5s ease-in-out infinite;
    }
    @keyframes edge-pulse {
        0%, 100% { opacity: 1; stroke-width: 2.5px; }
        50% { opacity: 0.7; stroke-width: 3.5px; }
    }

    /* Animated edge drawing — dash trick */
    .vis-edge path {
        stroke-dasharray: 5, 3;
        animation: dash-flow 20s linear infinite;
    }
    @keyframes dash-flow {
        to { stroke-dashoffset: -1000; }
    }

    /* PyVis nav buttons styled to match dark theme */
    .vis-navigation button {
        background-color: #161B22 !important;
        border: 1px solid #30363D !important;
        color: #58A6FF !important;
        border-radius: 4px !important;
    }
    .vis-navigation button:hover {
        background-color: #21262D !important;
    }

    /* Tooltip styling */
    .vis-tooltip {
        background: #161B22 !important;
        border: 1px solid #30363D !important;
        border-radius: 8px !important;
        color: #E6EDF3 !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 12px !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.6) !important;
        padding: 0 !important;
        overflow: visible !important;
    }

    /* Selected node highlight ring */
    .vis-node.vis-selected {
        border: 3px solid #58A6FF !important;
        box-shadow: 0 0 20px rgba(88,166,255,0.7) !important;
    }

    /* Smooth zoom */
    #network { transition: transform 200ms ease-out; }
    </style>
    """
    html_str = html_str.replace("<head>", "<head>\n" + injected_head)

    st_html(html_str, height=height, scrolling=False)


def _render_placeholder(height: int) -> None:
    """Render an animated placeholder when no DAG is loaded."""
    placeholder_html = f"""
    <div style="
        height: {height}px;
        width: 100%;
        background: #0D1117;
        border: 1px dashed #30363D;
        border-radius: 12px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        font-family: 'JetBrains Mono', monospace;
        color: #8B949E;
    ">
        <div style="font-size: 48px; margin-bottom: 16px; animation: float 3s ease-in-out infinite;">
            🌊
        </div>
        <div style="font-size: 16px; color: #58A6FF; margin-bottom: 8px;">
            No lineage graph loaded
        </div>
        <div style="font-size: 13px;">
            Upload a manifest.json to visualize your DAG
        </div>
    </div>
    <style>
    @keyframes float {{
        0%, 100% {{ transform: translateY(0); }}
        50% {{ transform: translateY(-10px); }}
    }}
    </style>
    """
    st_html(placeholder_html, height=height, scrolling=False)
