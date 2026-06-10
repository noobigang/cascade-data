# Architecture

This document describes Cascade's internal architecture — how a `manifest.json` becomes an interactive column-level lineage DAG.

---

## Data Flow Overview

```
manifest.json
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│  lineage/parser.py                                       │
│  ──────────────────────────────────────────────────────  │
│  1. Load JSON                                            │
│  2. Extract all nodes (models, sources, seeds, tests)   │
│  3. Extract column metadata (name, dtype, description)  │
│  4. Extract depends_on lists (refs + sources)            │
│  5. Emit: List[TableNode]                               │
└──────────────────────────────┬──────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────┐
│  lineage/models.py (LineageGraph — NetworkX DiGraph)    │
│  ──────────────────────────────────────────────────────  │
│  1. Create directed graph                               │
│  2. Add one node per model/source/seed                  │
│  3. Add edges from depends_on relationships            │
│  4. Attach column metadata as node attributes           │
│  5. Emit: LineageGraph                                  │
└──────────────────────────────┬──────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────┐
│  lineage/sql_lineage.py (SQLGlot)                        │
│  ──────────────────────────────────────────────────────  │
│  1. For each model, parse compiled SQL with SQLGlot     │
│  2. Walk SELECT/JOIN/CTE expressions                     │
│  3. Resolve column-level source → destination pairs     │
│  4. Emit: List[ColumnLineage] attached to model nodes  │
└──────────────────────────────┬──────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────┐
│  lineage/impact.py (blast radius + risk scoring)         │
│  ──────────────────────────────────────────────────────  │
│  1. NetworkX.descendants() for downstream trees         │
│  2. Risk score: weighted by # affected models + cols    │
│  3. Most-connected nodes: degree centrality             │
│  4. Emit: ImpactReport (used by blast-radius UI)        │
└──────────────────────────────┬──────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────┐
│  app.py (Streamlit)                                      │
│  ──────────────────────────────────────────────────────  │
│  1. Upload zone → lineage/parser.py                     │
│  2. ui/dag_viewer.py — render D3.js DAG                 │
│  3. ui/detail_panel.py — show node columns + lineage    │
│  4. ui/scroll_bridge.py — DAG click → state             │
│  5. Blast-radius panel — render ImpactReport            │
└─────────────────────────────────────────────────────────┘
```

---

## Module Reference

```
cascade-data/
├── app.py                    # Streamlit entrypoint
│
├── lineage/
│   ├── __init__.py
│   ├── models.py             # TableNode, ColumnNode, ColumnLineage, LineageGraph
│   ├── parser.py             # manifest.json → LineageGraph
│   ├── sql_lineage.py        # SQLGlot column-level extraction
│   └── impact.py             # blast radius, risk scoring, connectivity
│
├── ui/
│   ├── __init__.py
│   ├── dag_viewer.py         # D3.js dagre-layout DAG (embedded HTML)
│   ├── detail_panel.py       # node detail + column lineage table
│   ├── sidebar.py            # upload, filters, resource list
│   ├── hero.py               # dark theme CSS
│   ├── upload_zone.py        # drag-and-drop manifest uploader
│   └── scroll_bridge.py      # DAG click → Streamlit state bridge
│
├── tests/
│   └── test_lineage.py        # 44 tests
│
└── demo/
    ├── manifest.json
    └── build_manifest.py
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

### Why D3.js + dagre over PyVis / vis.js?

D3.js with the `dagre` layout gives us:
- **Static, predictable layout** — no physics simulation flinging nodes around
- **Better visual control** — we can render exactly the cards, badges, and labels we want
- **Smaller payload** — no vis.js runtime, no physics engine
- **More professional look** — the kind of diagram you'd see in a dbt / Looker / Fivetran doc

The trade-off is more JavaScript to maintain. The `ui/dag_viewer.py` file is one self-contained HTML+JS+CSS block; no build step.

### Why SQLGlot?

SQLGlot is the best-in-class Python SQL parser:
- **Dialect-aware** — handles BigQuery, Snowflake, Postgres, Spark, DuckDB, etc.
- **AST-based** — exposes columns, joins, CTEs, subqueries as a traversable tree
- **Pure Python** — no external compiler, no Java dependency
- **Used in production by major projects** (Dagster, dlt, sqlmesh)

### Why Stateless (No Database)?

Cascade is designed for one-shot exploration:
- Upload manifest → explore → export or share → done
- No user accounts, no persistence, no security surface
- State lives in URL params or in the running process

This makes it trivially runnable on localhost. Each user has their own instance. No shared infrastructure.

---

## State Management

Streamlit session state holds:
- `graph` — the `LineageGraph`
- `selected_node_uid` — currently clicked node
- `_bridge_last_at` — last seen timestamp from the DAG click bridge
- `dag_graph_data` — cached DAG payload (avoid re-computing)

State is **not persisted** across page refreshes. To share a view, the user exports a screenshot or the underlying JSON.

---

## Performance Targets

| Operation | Target |
|---|---|
| Parse 200-node manifest | < 1 second |
| Parse 1000-node manifest | < 5 seconds |
| Column-lineage extraction | < 1 second per 100 models |
| DAG render (200 nodes) | Smooth 60fps pan/zoom |
| Blast-radius query | < 100ms |
| Filter toggle | < 200ms |