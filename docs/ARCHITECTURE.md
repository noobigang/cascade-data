# Architecture

This document describes Cascade's internal architecture — how a `manifest.json` becomes an interactive column-level lineage DAG.

---

## Data Flow Overview

```
manifest.json
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│  manifest_parser.py                                      │
│  ──────────────────────────────────────────────────────  │
│  1. Load JSON                                           │
│  2. Extract all nodes (models, sources, seeds, tests)   │
│  3. Extract column metadata (name, dtype, description)   │
│  4. Extract depends_on lists (refs + sources)            │
│  5. Emit: List[ManifestNode]                            │
└──────────────────────────────┬──────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────┐
│  lineage_graph.py (NetworkX DiGraph)                    │
│  ──────────────────────────────────────────────────────  │
│  1. Create directed graph                               │
│  2. Add one node per model/source/seed                  │
│  3. Add edges from depends_on relationships            │
│  4. Attach column metadata as node/edge attributes      │
│  5. Emit: networkx.DiGraph                             │
└──────────────────────────────┬──────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────┐
│  graph_builder.py (PyVis HTML)                          │
│  ──────────────────────────────────────────────────────  │
│  1. Convert NetworkX DiGraph → PyVis network            │
│  2. Style nodes: color by database, size by degree      │
│  3. Label edges with column names on hover              │
│  4. Configure physics: force-directed layout            │
│  5. Emit: HTML string (rendered in Streamlit iframe)   │
└──────────────────────────────┬──────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────┐
│  app.py (Streamlit)                                      │
│  ──────────────────────────────────────────────────────  │
│  1. Upload zone → manifest_parser                       │
│  2. Build graph → display PyVis DAG                    │
│  3. Search panel → impact_analyzer (blast radius)       │
│  4. Detail panel → show node columns + up/downstream   │
│  5. Share card → state_encoder (URL encode/decode)     │
│  6. Export → graph_exporter (JSON / Markdown / PNG)     │
└─────────────────────────────────────────────────────────┘
```

---

## Module Reference

```
cascade/
├── app.py
│   ├── Streamlit entrypoint
│   ├── Session state management
│   └── Routes to sub-modules
│
├── parser/
│   ├── __init__.py
│   ├── manifest_parser.py       # Parse manifest.json → structured nodes
│   ├── column_resolver.py        # Resolve column-level depends_on
│   └── test_extractor.py        # Extract dbt tests as node attributes
│
├── graph/
│   ├── __init__.py
│   ├── lineage_graph.py         # Build NetworkX DiGraph from nodes
│   ├── impact_analyzer.py       # Blast radius + upstream/downstream queries
│   └── graph_exporter.py        # Export to PyVis HTML / JSON / Markdown
│
├── ui/
│   ├── __init__.py
│   ├── dag_viewer.py            # PyVis iframe + Streamlit integration
│   ├── search_panel.py          # Impact search input + results display
│   ├── detail_panel.py          # Model/column detail slide-up panel
│   └── upload_zone.py           # Drag-and-drop manifest upload UI
│
└── utils/
    ├── __init__.py
    └── state_encoder.py         # URL-safe state encode/decode for share cards
```

---

## Key Design Decisions

### Why NetworkX?

NetworkX is the right tool for this workload:
- **Fast enough for 10k+ nodes** (dbt projects rarely exceed this)
- **Rich algorithms** — `ancestors()`, `descendants()`, `shortest_path()` all built-in
- **Easy serialization** — `node_link_data()` for JSON export
- **Python-native** — no bridge between languages needed

For extremely large graphs (100k+ nodes), consider swapping to `igraph` or `graph-tool`, but for the target user (single dbt project), NetworkX is sufficient.

### Why PyVis over D3.js?

PyVis wraps vis.js, which is:
- **Python-first** — no JavaScript build step required
- **Sufficient interactivity** — hover, click, zoom, pan
- **Easy to embed** — `st.components.v1.html()` in Streamlit

D3.js would allow finer visual control, but would require a separate frontend build pipeline (Vite/Webpack + TypeScript). That complexity is not worth it for a data-tool UI used by engineers who care about the graph, not the chrome.

### Why Stateless (No Database)?

Cascade is designed for one-shot exploration:
- Upload manifest → explore → share or export → done
- No user accounts, no persistence, no security surface
- State lives in URL params (base64-encoded) or local JSON files

This makes it trivially deployable on Hugging Face Spaces with zero infrastructure.

---

## State Management

Streamlit session state holds:
- `manifest_data` — raw dict from uploaded JSON
- `nodes` — list of parsed `ManifestNode` objects
- `graph` — the `networkx.DiGraph`
- `selected_node` — currently clicked model name
- `share_state` — base64-encoded URL params for share cards

State is **not persisted** across page refreshes. To share a view, use the Share Card feature which encodes the full state into the URL.

---

## Performance Targets

| Operation | Target |
|---|---|
| Parse 10k+ node manifest | < 5 seconds |
| DAG render (500+ nodes) | Smooth 60fps pan/zoom |
| Blast radius query | < 1 second |
| Two-manifest diff | < 10 seconds |