"""
DAG Viewer component for Cascade.
Renders a static, clean, left-to-right lineage graph (no force animation).
Uses D3.js with dagre layout — matches dbt-colibri's static style.
"""

import streamlit as st
import json


DAG_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Cascade DAG</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/dagre@0.8.5/dist/dagre.min.js"></script>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html, body {
    background: #0D1117;
    font-family: 'Inter', -apple-system, sans-serif;
    overflow: hidden;
    width: 100%;
    height: 100%;
    color: #E6EDF3;
  }
  #dag-container { width: 100%; height: 100%; position: relative; }
  #graph-svg { width: 100%; height: 100%; display: block; background: #0D1117; }

  /* Node card */
  .node-card { cursor: pointer; }
  .node-card-bg {
    fill: #161B22;
    stroke-width: 1.5;
    transition: stroke 0.15s, stroke-width 0.15s;
  }
  .node-card:hover .node-card-bg { stroke-width: 2.5; }
  .node-card.selected .node-card-bg { stroke-width: 3; }

  /* Type accents */
  .node-card.model .node-card-bg     { stroke: #58A6FF; }
  .node-card.source .node-card-bg    { stroke: #39D353; }
  .node-card.seed .node-card-bg      { stroke: #8B949E; }
  .node-card.snapshot .node-card-bg  { stroke: #D29922; }
  .node-card.selected .node-card-bg  { stroke: #F0F6FC; }

  /* Type label (small badge in top-left) */
  .node-type-badge {
    font-family: 'JetBrains Mono', monospace;
    font-size: 9px;
    font-weight: 600;
    fill: #0D1117;
    text-anchor: middle;
    dominant-baseline: central;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  .node-card.model .badge-bg     { fill: #58A6FF; }
  .node-card.source .badge-bg    { fill: #39D353; }
  .node-card.seed .badge-bg      { fill: #8B949E; }
  .node-card.snapshot .badge-bg  { fill: #D29922; }

  /* Main name label */
  .node-name {
    font-family: 'JetBrains Mono', 'Consolas', monospace;
    font-size: 14px;
    font-weight: 600;
    fill: #E6EDF3;
    text-anchor: middle;
    dominant-baseline: central;
  }

  /* Sub label (schema) */
  .node-sub {
    font-family: 'Inter', sans-serif;
    font-size: 11px;
    fill: #8B949E;
    text-anchor: middle;
    dominant-baseline: central;
  }

  /* Column count pill */
  .node-meta {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    fill: #8B949E;
    text-anchor: middle;
    dominant-baseline: central;
  }

  /* Edges */
  .edge-path {
    fill: none;
    stroke: #30363D;
    stroke-width: 1.5;
  }
  .edge-path.highlighted { stroke: #58A6FF; stroke-width: 2.5; }
  .edge-path.dimmed { stroke: #1A1F26; }

  /* Toolbar */
  #toolbar {
    position: absolute;
    top: 12px;
    right: 12px;
    display: flex;
    gap: 6px;
    z-index: 100;
  }
  .tool-btn {
    background: #161B22;
    border: 1px solid #30363D;
    border-radius: 6px;
    color: #8B949E;
    font-size: 11px;
    font-family: 'Inter', sans-serif;
    padding: 6px 10px;
    cursor: pointer;
    transition: all 0.15s;
  }
  .tool-btn:hover { background: #21262D; color: #E6EDF3; border-color: #58A6FF; }
  .tool-btn.active { background: #58A6FF20; border-color: #58A6FF; color: #58A6FF; }

  /* Filter chips */
  #filter-bar {
    position: absolute;
    top: 12px;
    left: 12px;
    display: flex;
    gap: 6px;
    z-index: 100;
    flex-wrap: wrap;
    max-width: 380px;
  }
  .chip {
    background: #161B22;
    border: 1px solid #30363D;
    border-radius: 20px;
    font-size: 10px;
    font-family: 'Inter', sans-serif;
    padding: 4px 10px;
    cursor: pointer;
    color: #8B949E;
    user-select: none;
    transition: all 0.15s;
  }
  .chip:hover { border-color: #58A6FF; color: #E6EDF3; }
  .chip.active { background: #58A6FF20; border-color: #58A6FF; color: #58A6FF; }

  /* Stats bar */
  #stats {
    position: absolute;
    bottom: 12px;
    left: 50%;
    transform: translateX(-50%);
    background: #161B22;
    border: 1px solid #30363D;
    border-radius: 8px;
    padding: 6px 16px;
    display: flex;
    gap: 18px;
    font-size: 11px;
    font-family: 'JetBrains Mono', monospace;
    color: #8B949E;
    z-index: 100;
  }
  #stats span { color: #E6EDF3; font-weight: 600; }

  /* Tooltip */
  #tooltip {
    position: fixed;
    background: #161B22;
    border: 1px solid #30363D;
    border-radius: 6px;
    padding: 8px 12px;
    pointer-events: none;
    opacity: 0;
    transition: opacity 0.12s;
    z-index: 1000;
    font-size: 11px;
    color: #E6EDF3;
    max-width: 280px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.5);
  }
  #tooltip.visible { opacity: 1; }
  #tooltip .tip-name { font-family: 'JetBrains Mono', monospace; font-weight: 600; }
  #tooltip .tip-uid  { color: #8B949E; font-family: 'JetBrains Mono', monospace; font-size: 10px; }

  /* Empty state */
  #empty-state {
    position: absolute;
    top: 50%; left: 50%;
    transform: translate(-50%, -50%);
    text-align: center;
    color: #8B949E;
    display: none;
  }
  #empty-state.visible { display: block; }
  #empty-state .empty-icon { font-size: 56px; margin-bottom: 16px; opacity: 0.3; }
  #empty-state .empty-title { font-size: 16px; color: #E6EDF3; font-weight: 600; margin-bottom: 6px; }
  #empty-state .empty-sub { font-size: 12px; }
</style>
</head>
<body>
<div id="dag-container">
  <svg id="graph-svg"></svg>

  <div id="filter-bar">
    <div class="chip active" data-type="all">All</div>
    <div class="chip active" data-type="model">Models</div>
    <div class="chip active" data-type="source">Sources</div>
    <div class="chip active" data-type="seed">Seeds</div>
  </div>

  <div id="toolbar">
    <button class="tool-btn" id="btn-fit">Fit to Screen</button>
    <button class="tool-btn" id="btn-reset">Reset</button>
  </div>

  <div id="stats">
    <div>Nodes: <span id="stat-nodes">0</span></div>
    <div>Edges: <span id="stat-edges">0</span></div>
    <div>Visible: <span id="stat-visible">0</span></div>
  </div>

  <div id="tooltip"></div>

  <div id="empty-state">
    <div class="empty-icon">&#9675;</div>
    <div class="empty-title">No nodes to display</div>
    <div class="empty-sub">Graph data is empty or all nodes are filtered out.</div>
  </div>
</div>

<script>
(function() {
  'use strict';

  let graphData = { nodes: [], edges: [] };
  let activeFilters = new Set(['model', 'source', 'seed']);
  let selectedNodeId = null;

  const svg = d3.select('#graph-svg');
  const container = document.getElementById('dag-container');
  const tooltip = document.getElementById('tooltip');

  // Use a sub-group so zoom/pan only affects the graph layer
  let gRoot, gEdges, gNodes, zoomBehavior;
  let width = 0, height = 0;

  // ── Graph Data Loader (called from Python via window.loadGraphData) ───────
  window.loadGraphData = function(data) {
    if (!data || !data.nodes || !data.edges) return;
    graphData = data;
    layout();
    updateStats();
  };

  // ── Dagre layout (static, no animation) ─────────────────────────────────
  function layout() {
    width = container.clientWidth;
    height = container.clientHeight;
    svg.attr('viewBox', `0 0 ${width} ${height}`);

    svg.selectAll('*').remove();

    // Arrow marker
    const defs = svg.append('defs');
    defs.append('marker')
      .attr('id', 'arrow')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 8)
      .attr('refY', 0)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', '#30363D');

    defs.append('marker')
      .attr('id', 'arrow-blue')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 8)
      .attr('refY', 0)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', '#58A6FF');

    gRoot = svg.append('g').attr('class', 'g-root');
    gEdges = gRoot.append('g').attr('class', 'g-edges');
    gNodes = gRoot.append('g').attr('class', 'g-nodes');

    zoomBehavior = d3.zoom()
      .scaleExtent([0.3, 3])
      .on('zoom', (event) => gRoot.attr('transform', event.transform));

    svg.call(zoomBehavior);

    const visibleNodes = getVisibleNodes();
    if (visibleNodes.length === 0) {
      document.getElementById('empty-state').classList.add('visible');
      return;
    }
    document.getElementById('empty-state').classList.remove('visible');

    // Build dagre graph
    const g = new dagre.graphlib.Graph();
    g.setGraph({
      rankdir: 'LR',          // left to right
      nodesep: 30,            // vertical space between nodes in same rank
      ranksep: 60,            // horizontal space between ranks
      marginx: 20,
      marginy: 20
    });
    g.setDefaultEdgeLabel(() => ({}));

    // Node dimensions (must match the rect we draw)
    const NODE_W = 180;
    const NODE_H = 52;

    visibleNodes.forEach(n => g.setNode(n.id, { width: NODE_W, height: NODE_H, node: n }));
    const visibleEdges = getVisibleEdges();
    visibleEdges.forEach(e => g.setEdge(e.source, e.target));

    dagre.layout(g);

    // ── Draw edges ─────────────────────────────────────────────────────
    const edgeSel = gEdges.selectAll('path.edge-path')
      .data(visibleEdges, d => `${d.source}->${d.target}`);

    edgeSel.enter().append('path')
      .attr('class', 'edge-path')
      .merge(edgeSel)
      .attr('marker-end', 'url(#arrow)')
      .attr('d', d => {
        const edge = g.edge(d.source, d.target);
        if (!edge) return '';
        // Dagre gives us points; build a smooth path
        const pts = edge.points;
        if (!pts || pts.length === 0) return '';
        // Stop short of node by NODE_W/2 + 4
        const target = g.node(d.target);
        const source = g.node(d.source);
        const sx = source.x + source.width / 2;
        const sy = source.y;
        const tx = target.x - target.width / 2 - 4;
        const ty = target.y;
        return `M${sx},${sy} L${tx},${ty}`;
      });

    edgeSel.exit().remove();

    // ── Draw nodes ─────────────────────────────────────────────────────
    const nodeSel = gNodes.selectAll('g.node-card')
      .data(visibleNodes, d => d.id);

    const nodeEnter = nodeSel.enter()
      .append('g')
      .attr('class', d => `node-card ${d.resource_type || 'model'}`)
      .attr('transform', d => {
        const n = g.node(d.id);
        return `translate(${n.x - n.width/2},${n.y - n.height/2})`;
      })
      .on('click', (event, d) => {
        event.stopPropagation();
        selectNode(d);
      })
      .on('mouseenter', (event, d) => showTooltip(event, d))
      .on('mousemove', moveTooltip)
      .on('mouseleave', hideTooltip);

    // Card background
    nodeEnter.append('rect')
      .attr('class', 'node-card-bg')
      .attr('width', NODE_W)
      .attr('height', NODE_H)
      .attr('rx', 6)
      .attr('ry', 6);

    // Type badge (top-left)
    nodeEnter.append('rect')
      .attr('class', 'badge-bg')
      .attr('x', 8)
      .attr('y', 8)
      .attr('width', 32)
      .attr('height', 14)
      .attr('rx', 3)
      .attr('ry', 3);

    nodeEnter.append('text')
      .attr('class', 'node-type-badge')
      .attr('x', 24)
      .attr('y', 15)
      .text(d => (d.resource_type || 'model').toUpperCase().slice(0, 3));

    // Main name
    nodeEnter.append('text')
      .attr('class', 'node-name')
      .attr('x', NODE_W / 2)
      .attr('y', NODE_H / 2 - 4)
      .text(d => truncate(d.name || d.label || d.id.split('.').pop(), 22));

    // Sub (schema or schema.table)
    nodeEnter.append('text')
      .attr('class', 'node-sub')
      .attr('x', NODE_W / 2)
      .attr('y', NODE_H / 2 + 12)
      .text(d => d.schema || '');

    // Column count pill (bottom-right)
    nodeEnter.append('text')
      .attr('class', 'node-meta')
      .attr('x', NODE_W - 10)
      .attr('y', NODE_H - 8)
      .text(d => d.column_count != null ? `${d.column_count} cols` : '');

    nodeSel.exit().remove();

    // Auto-fit to view
    fitToScreen();
    updateNodeStyles();
    updateEdgeStyles();
  }

  // ── Selection ─────────────────────────────────────────────────────────
  function selectNode(node) {
    selectedNodeId = (selectedNodeId === node.id) ? null : node.id;
    updateNodeStyles();
    updateEdgeStyles();

    // Notify Streamlit
    if (window.parent && window.parent !== window) {
      window.parent.postMessage({
        type: 'cascade_node_selected',
        nodeId: selectedNodeId
      }, '*');
    }
  }

  function updateNodeStyles() {
    gNodes.selectAll('g.node-card')
      .classed('selected', d => d.id === selectedNodeId)
      .style('opacity', d => {
        if (!selectedNodeId) return 1;
        return isConnected(d.id) || d.id === selectedNodeId ? 1 : 0.2;
      });
  }

  function updateEdgeStyles() {
    gEdges.selectAll('path.edge-path')
      .classed('highlighted', d => selectedNodeId && (d.source === selectedNodeId || d.target === selectedNodeId))
      .classed('dimmed', d => selectedNodeId && d.source !== selectedNodeId && d.target !== selectedNodeId)
      .attr('marker-end', d => {
        const isHi = selectedNodeId && (d.source === selectedNodeId || d.target === selectedNodeId);
        return isHi ? 'url(#arrow-blue)' : 'url(#arrow)';
      });
  }

  function isConnected(nodeId) {
    if (!selectedNodeId) return true;
    return getVisibleEdges().some(e =>
      (e.source === selectedNodeId && e.target === nodeId) ||
      (e.target === selectedNodeId && e.source === nodeId)
    );
  }

  // ── Filters ───────────────────────────────────────────────────────────
  function getVisibleNodes() {
    return graphData.nodes.filter(n => activeFilters.has(n.resource_type || 'model'));
  }
  function getVisibleEdges() {
    const ids = new Set(getVisibleNodes().map(n => n.id));
    return graphData.edges.filter(e => ids.has(e.source) && ids.has(e.target));
  }

  document.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const type = chip.dataset.type;
      if (type === 'all') {
        const turningOn = !chip.classList.contains('active');
        activeFilters = turningOn ? new Set(['model', 'source', 'seed']) : new Set();
        document.querySelectorAll('.chip').forEach(c => c.classList.toggle('active', turningOn));
      } else {
        if (activeFilters.has(type)) activeFilters.delete(type);
        else activeFilters.add(type);
        chip.classList.toggle('active');
        const allChip = document.querySelector('.chip[data-type="all"]');
        allChip.classList.toggle('active', activeFilters.size === 3);
      }
      layout();
      updateStats();
    });
  });

  // ── Toolbar ───────────────────────────────────────────────────────────
  document.getElementById('btn-fit').addEventListener('click', fitToScreen);
  document.getElementById('btn-reset').addEventListener('click', () => {
    svg.transition().duration(250).call(zoomBehavior.transform, d3.zoomIdentity);
  });

  function fitToScreen() {
    const bbox = gRoot.node().getBBox();
    if (bbox.width === 0) return;
    const pad = 30;
    // Fit to width primarily (left-to-right layout) so nodes stay readable
    const scale = Math.min(
      (width - pad * 2) / bbox.width,
      (height - pad * 2) / bbox.height,
      1.0
    );
    const finalScale = Math.max(scale, 0.5);  // never shrink below 0.5x
    const tx = (width - bbox.width * finalScale) / 2 - bbox.x * finalScale;
    const ty = (height - bbox.height * finalScale) / 2 - bbox.y * finalScale;
    svg.call(zoomBehavior.transform, d3.zoomIdentity.translate(tx, ty).scale(finalScale));
  }

  // ── Stats ─────────────────────────────────────────────────────────────
  function updateStats() {
    document.getElementById('stat-nodes').textContent = graphData.nodes.length;
    document.getElementById('stat-edges').textContent = graphData.edges.length;
    document.getElementById('stat-visible').textContent = getVisibleNodes().length;
  }

  // ── Tooltip ───────────────────────────────────────────────────────────
  function showTooltip(event, node) {
    const id = node.id;
    const name = node.name || id.split('.').pop();
    const sub = [node.schema, node.database].filter(Boolean).join('.');
    tooltip.innerHTML = `<div class="tip-name">${escapeHtml(name)}</div>
                         <div class="tip-uid">${escapeHtml(id)}</div>
                         ${sub ? `<div style="margin-top:4px;color:#8B949E;font-size:10px;">${escapeHtml(sub)}</div>` : ''}`;
    tooltip.classList.add('visible');
    moveTooltip(event);
  }
  function moveTooltip(event) {
    const x = event.clientX + 14;
    const y = event.clientY + 14;
    const r = tooltip.getBoundingClientRect();
    tooltip.style.left = (x + r.width > window.innerWidth ? event.clientX - r.width - 14 : x) + 'px';
    tooltip.style.top  = (y + r.height > window.innerHeight ? event.clientY - r.height - 14 : y) + 'px';
  }
  function hideTooltip() { tooltip.classList.remove('visible'); }

  // ── Utils ─────────────────────────────────────────────────────────────
  function truncate(s, n) {
    s = String(s || '');
    return s.length > n ? s.slice(0, n - 1) + '\u2026' : s;
  }
  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({
      '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
    }[c]));
  }

  // ── Resize ────────────────────────────────────────────────────────────
  const ro = new ResizeObserver(() => layout());
  ro.observe(container);

  // ── Background click ──────────────────────────────────────────────────
  svg.on('click.bg', () => {
    if (selectedNodeId) {
      selectedNodeId = null;
      updateNodeStyles();
      updateEdgeStyles();
    }
  });

  // ── Listen for data from parent (Streamlit) ───────────────────────────
  window.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'cascade_load_data') {
      window.loadGraphData(event.data.data);
    }
  });

})();
</script>
</body>
</html>
"""


def render_dag_viewer(graph_data: dict, height: int = 600) -> None:
    """Render the static dagre-laid-out DAG viewer."""
    import streamlit.components.v1 as components

    data_json = json.dumps(graph_data)

    html = DAG_HTML.replace(
        "</body>",
        f"<script>window.loadGraphData({data_json});</script></body>",
    )

    components.html(html, height=height, scrolling=False)
