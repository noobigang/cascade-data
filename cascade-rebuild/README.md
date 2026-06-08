# 🌊 Cascade — Column-Level Data Lineage Dashboard

**See the full impact of every data change.**

Cascade is an open-source, self-hosted dashboard for exploring column-level lineage in dbt projects. Upload your `manifest.json`, visualize the full DAG, drill into column dependencies, and measure blast radius before you deploy.

> Built to beat [dbt-colibri](https://github.com/b-ned/dbt-colibri) in features, UX, and visual design.

---

## ✨ Features

- **Column-level lineage** — SQLGlot-powered tracing from source columns through every transformation
- **Interactive DAG** — D3.js force-directed graph with zoom/pan/click, glow effects, physics toggle
- **Blast radius analysis** — See every downstream table and column affected by a change, with risk scoring
- **Node detail panel** — Columns, data types, upstream/downstream deps, compiled SQL preview
- **Search & filters** — Full-text search across model names, column names, and descriptions
- **Shareable links** — URL-encoded view state for sharing specific nodes or filters
- **Dark theme** — Professional data-tool aesthetic with JetBrains Mono + Inter fonts
- **Auto-demo** — One-click demo loads a rich 20-node e-commerce lineage graph instantly

---

## 🚀 Quick Start

### Live Demo
[![Streamlit](https://static.streamlit.io/badges/streamlit_badge.svg)](https://cascade-data.streamlit.app/)

Try it instantly at **https://cascade-data.streamlit.app/** — the demo loads automatically.

### Self-Hosted

```bash
# 1. Clone
git clone https://github.com/noobigang/cascade-data.git
cd cascade-data/cascade-rebuild

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run
streamlit run app.py
```

Or generate a static report:
```bash
dbt compile
# Place target/manifest.json in demo/ then run
streamlit run app.py --server.headless true
```

---

## 📂 File Structure

```
cascade-rebuild/
├── app.py                    ← Streamlit entry point
├── pyproject.toml            ← project metadata, ruff/mypy/pytest config
├── requirements.txt           ← pinned runtime + dev dependencies
├── lineage/
│   ├── models.py             ← TableNode, ColumnNode, LineageGraph
│   ├── parser.py             ← manifest.json → LineageGraph
│   ├── sql_lineage.py        ← SQLGlot column extraction
│   └── impact.py             ← blast radius, risk scoring
├── ui/
│   ├── dag_viewer.py         ← D3.js force-directed DAG (embedded HTML)
│   ├── hero.py               ← Hero section + animated stats cards
│   ├── sidebar.py            ← Upload, filters, resource list
│   ├── detail_panel.py       ← Node detail + column table
│   └── search_panel.py       ← Impact search + blast radius
├── demo/
│   └── manifest.json         ← 20-node e-commerce demo graph
└── tests/
    └── test_lineage.py        ← 44 passing tests
```

---

## 🏗️ Tech Stack

| Layer | Technology |
|---|---|
| Dashboard | Streamlit |
| DAG Visualization | D3.js v7 (embedded via `st.components.v1.html`) |
| Lineage Extraction | SQLGlot (SQL parsing) + NetworkX (graph) |
| Data Model | Python dataclasses |
| Deployment | Streamlit Cloud (auto-deploy on push) |

---

## 📊 Architecture

```
manifest.json (dbt compile)
       ↓
  ManifestParser → LineageGraph (NetworkX DiGraph)
                          ↓
                    SQLGlot ColumnExtractor
                          ↓
               ColumnLineage records (column-level deps)
                          ↓
                    D3.js DAG Viewer (Streamlit embed)
```

---

## 🧪 Tests

```bash
pytest tests/ -v
# 44 passing tests covering:
# - Data models (TableNode, ColumnNode, ColumnLineage, LineageGraph)
# - Manifest parsing (20 nodes, edges, column metadata)
# - SQL lineage (aliases, CTEs, JOINs, window functions, CASE/WHEN)
# - Impact analysis (blast radius, risk scoring, most connected nodes)
# - Integration (full pipeline parse + enrich)
```

---

## 🔧 CI/CD

- **GitHub Actions CI**: ruff lint, mypy type check, pytest — runs on every push and PR
- **Parallel jobs**: lint/typecheck and test run concurrently for faster feedback
- **Pip caching**: dependencies cached between runs via `actions/cache@v4`
- **Streamlit Cloud**: auto-deploys on push to `main` (connect repo at [streamlit.io/cloud](https://streamlit.io/cloud))
- **Test coverage**: 44 tests, all passing

---

## 📖 How It Works

1. **Upload `manifest.json`** from `dbt compile` or `dbt build`
2. **LineageGraph** parses all nodes (models, sources, seeds) and edges
3. **SQLGlot** parses compiled SQL for each model, extracting column-level flows
4. **D3.js DAG** renders the interactive graph — click any node to see details
5. **Impact Analysis** shows full blast radius with risk scoring

---

## 🌐 Deployment

### Streamlit Cloud (recommended)

1. Go to [streamlit.io/cloud](https://streamlit.io/cloud) and sign in with GitHub
2. Click **New app** → select this repository → set app path to `app.py`
3. Set Python version to `3.11`
4. Click **Deploy** — Streamlit auto-deploys on every push to `main`

No API key or secrets needed. The GitHub Actions `deploy.yml` runs CI checks before each deploy.

### Self-hosted

```bash
pip install -r requirements.txt
streamlit run app.py --server.port 8501
```

### Upload your manifest

After deploying, open the app and upload `manifest.json` from your dbt project:

```bash
cd your-dbt-project
dbt compile
# Upload: target/manifest.json
```

The dashboard will parse all models, extract column-level flows via SQLGlot, and render an interactive lineage graph.

---

## 🤝 Contributing

PRs welcome! Run tests before submitting:
```bash
pytest tests/ -v
ruff check lineage/ ui/ app.py
mypy lineage/ ui/ --ignore-missing-imports
```

---

## 📄 License

MIT — see [LICENSE](/LICENSE)