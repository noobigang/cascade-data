# Cascade — Data Lineage & Impact Analysis

## What it does

Cascade answers the question every data engineer fears: **"What breaks if I change this column?"**

You drop a manifest.json from a dbt project into Cascade, and it instantly maps your entire data warehouse — all the way down to the column level — and shows you everything that would break, be silently wrong, or get stale if you touch the wrong model.

---

## 1. Concept & Vision

Cascade is a column-level lineage tool with a visual "blast radius" — think of it as `git blame` for your data warehouse. It's built for data engineers who run dbt and need to answer:

- Which models and dashboards depend on this column?
- How risky is this change (1 column touching 50 downstream reports)?
- What should I validate before I deploy?

The aesthetic is **command-center dark** — deep charcoal surfaces, teal accents, glowing DAG lines. It should feel like mission control for your data pipeline, not a BI dashboard. Data engineers are power users — this tool respects their time.

---

## 2. Design Language

**Aesthetic**: Mission control / cyberpunk data terminal. Dark, precise, glowing. Think Bloomberg Terminal meets Figma.

**Color Palette**:
- Background: `#0D1117` (deep black)
- Surface: `#161B22` (elevated panels)
- Border: `#30363D` (subtle separators)
- Primary: `#58A6FF` (bright blue — selected/hover)
- Accent: `#39D353` (green — success/safe)
- Warning: `#D29922` (amber — moderate risk)
- Danger: `#F85149` (red — high blast radius)
- Text primary: `#E6EDF3`
- Text muted: `#8B949E`

**Typography**:
- UI labels + headings: `JetBrains Mono` (monospace — data engineer aesthetic)
- Body + descriptions: `Inter`
- Code/paths: `JetBrains Mono`

**Motion**:
- DAG node hover: subtle scale(1.05) + glow, 150ms ease-out
- Panel transitions: 200ms fade + slide
- Lineage path highlight: animated dash-offset on SVG path, 400ms

**Visual Assets**:
- Phosphor Icons (thin weight)
- Custom SVG DAG nodes (circles with glow)
- No stock photos — data is the content

---

## 3. Layout & Structure

```
┌─────────────────────────────────────────────────────────────┐
│  HEADER: Logo + "Cascade" + Upload button + GitHub link    │
├───────────────┬─────────────────────────────────────────────┤
│               │                                             │
│   SIDEBAR     │              MAIN CANVAS                    │
│               │                                             │
│  • Search     │  [Interactive Column-Level Lineage DAG]    │
│  • Filters    │                                             │
│  • Model list │  Nodes = models  |  Edges = column flows   │
│  • Stats      │                                             │
│               │                                             │
├───────────────┴─────────────────────────────────────────────┤
│  DETAIL PANEL (slide up on node click):                    │
│  Model name, columns, sample values, upstream/downstream   │
└─────────────────────────────────────────────────────────────┘
```

**Responsive**: Sidebar collapses on mobile. DAG becomes scrollable/pannable.

---

## 4. Core Features

### 4.1 Manifest Upload & Parse
- User uploads `manifest.json` (from `target/manifest.json` after `dbt build`)
- Drag-and-drop or click-to-upload
- Parser extracts: nodes (models, sources, seeds), columns, refs, sources, tests
- Build in-memory directed graph (DAG) of model → column dependencies
- Show parse progress bar for large manifests (10k+ nodes)

### 4.2 Column-Level Lineage DAG
- Interactive force-directed graph (D3.js / PyVis / Cytoscape)
- **Nodes** = models (colored by database type: snowflake=blue, bigquery=teal, redshift=orange)
- **Edges** = column-level flows (labeled with column names on hover)
- Click node → opens detail panel with:
  - Model name, schema, description
  - Upstream columns (what feeds this model)
  - Downstream columns (what this model feeds)
  - Column list with data types and descriptions
- Filter: show only models with >= N downstream dependents
- Highlight mode: highlight all paths from a selected node

### 4.3 Blast Radius / Impact Search
- **"What breaks if I change model X?"**
  - Input: model name or column name
  - Output: tree of all downstream models + their downstream models
  - Risk score = number of terminal downstream nodes (dashboards, reports)
- **"Where does this column come from?"**
  - Input: fully qualified column `model_name.column_name`
  - Output: upstream dependency tree to sources
- Risk score display:
  - 🟢 Low (1-3 downstream)
  - 🟡 Medium (4-20 downstream)
  - 🔴 High (20+ downstream)

### 4.4 Change Alert (Static Analysis)
- Upload two manifests (before/after a dbt change)
- Cascade diffs them: added/removed/modified models and columns
- Shows new blast radius of changes
- Highlights breaking changes: dropped columns, renamed columns, type changes

### 4.5 Share Card
- Generate a shareable URL (base64 encode state in URL params)
- One-click copy of the DAG view state
- No auth required — stateless, client-side decode

### 4.6 Export
- Export lineage as JSON (full graph structure)
- Export blast-radius report as Markdown
- Download annotated DAG as PNG/SVG

---

## 5. Technical Architecture

### Stack
- **Frontend/UI**: Streamlit (Python) — rapid development, great for data tool UIs
- **DAG Visualization**: PyVis (interactive HTML/JS graphs from Python)
- **Parser**: Python — parse `manifest.json` into `NetworkX` directed graph
- **Deployment**: Hugging Face Spaces (auto-deploy from GitHub)
- **No database** — fully stateless, all state in browser/URL params

### Data Flow
```
manifest.json
    ↓
[manifest_parser.py]  ← extracts nodes, columns, refs
    ↓
[NetworkX DiGraph]  ← builds directed graph
    ↓
[graph_builder.py]  ← converts to PyVis HTML
    ↓
[Streamlit app]  ← renders + interactive controls
```

### Key Modules

```
cascade/
├── app.py                    # Streamlit entrypoint
├── parser/
│   ├── __init__.py
│   ├── manifest_parser.py   # Parse manifest.json → node list
│   ├── column_resolver.py    # Resolve column-level refs
│   └── test_extractor.py     # Extract dbt tests as node attributes
├── graph/
│   ├── __init__.py
│   ├── lineage_graph.py      # Build NetworkX graph
│   ├── impact_analyzer.py    # Blast radius, upstream/downstream
│   └── graph_exporter.py     # Export to PyVis/JSON/Markdown
├── ui/
│   ├── __init__.py
│   ├── dag_viewer.py         # PyVis integration + Streamlit
│   ├── search_panel.py       # Impact search UI
│   ├── detail_panel.py       # Model/column detail slide-up
│   └── upload_zone.py        # Drag-drop manifest upload
└── utils/
    ├── __init__.py
    └── state_encoder.py      # URL state encode/decode for share cards
```

### Column-Level Lineage
The hardest part. Approach:
1. Parse `manifest.json` `nodes` dict — each node has `columns` dict and `depends_on` list
2. For column-level: traverse `depends_on` and match by column name in parent node's `columns`
3. Build hypergraph where edges carry column names
4. For display: collapse to node-level with column labels on hover
5. For blast radius: expand to column-level when user queries a specific column

### Hugging Face Spaces Deployment
- Connect `cascade-data` repo to Hugging Face Spaces (Subsection: Static)
- `requirements.txt` with: `streamlit, networkx, pyvis, pandas`
- `README.md` with Space metadata (emoji, title, thumbnail)
- Auto-deploys on every push to `main`
- No authentication — anyone can upload a manifest and explore

---

## 6. MVP Scope (v1.0)

### In Scope
- Manifest upload + parse (dbt 1.x manifest.json)
- Model-level DAG (nodes = models, edges = refs)
- Column-level edges on hover (show column names)
- Click node → detail panel (upstream/downstream columns)
- Blast radius search: "what breaks if I change model X"
- Upstream search: "where does this column come from"
- Risk score (🟢/🟡/🔴) per model
- Share card (URL state)
- Export as JSON
- Hugging Face Spaces deployment

### Out of Scope (v1.1+)
- Two-manifest diff (change alert)
- Dashboard/BI tool integration (Looker, Metabase)
- dbt Cloud live sync
- Column popularity scoring
- dbt test results overlay

---

## 7. Differentiation vs dbt-colibri

| Feature | dbt-colibri | Cascade |
|---|---|---|
| Column-level lineage | No | Yes |
| Interactive DAG | Static HTML | Live, clickable |
| Blast radius analysis | No | Yes |
| Risk scoring | No | Yes |
| Change diff | No | Yes (v1.1) |
| Share card | No | Yes |
| Deployment | Manual | Auto (HF Spaces) |
| Open source | Yes (265 stars) | Yes |

---

## 8. Success Metrics

- Parse 10k+ node manifest in < 5 seconds
- DAG renders smoothly for 500+ nodes
- Blast radius query returns in < 1 second
- Hugging Face Spaces: 100+ stars in first month