# 🌊 Cascade — Column-Level Data Lineage for dbt

> **Local-first lineage dashboard for dbt projects.**
> Drop in your `manifest.json`. Get a clickable DAG, column-level dependencies, blast-radius analysis, and impact reports. Nothing leaves your machine.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-44%20passing-brightgreen.svg)](tests/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](https://mypy.readthedocs.io/)
[![Self-hosted only](https://img.shields.io/badge/deployment-self--hosted-orange.svg)](SECURITY.md)

---

## What is Cascade?

Cascade is a single-user dashboard for inspecting the **column-level** lineage of a dbt project. It reads the `manifest.json` produced by `dbt compile` or `dbt build`, parses the compiled SQL with [SQLGlot](https://github.com/tobymao/sqlglot), and renders an interactive DAG where every node and every column is clickable.

It's the tool you reach for when someone says "what breaks if I drop this column?" or "show me the path from this Snowflake raw table to this dashboard".

### Why use it?

| | dbt docs | dbt-colibri | elementary | **Cascade** |
|---|---|---|---|---|
| Model-level lineage | ✅ | ✅ | ✅ | ✅ |
| **Column-level** lineage | ❌ | ⚠️ Limited | ⚠️ Limited | ✅ Native |
| Interactive DAG (clickable) | ⚠️ Static | ⚠️ Static | ⚠️ Static | ✅ Live |
| Blast-radius analysis | ❌ | ❌ | ❌ | ✅ Full tree |
| Risk scoring (🟢🟡🔴) | ❌ | ❌ | ❌ | ✅ |
| Per-column upstream/downstream | ❌ | ❌ | ❌ | ✅ |
| Manifest diff (before/after) | ❌ | ❌ | ✅ | Planned |
| Runs on localhost | ✅ | ✅ | ✅ | ✅ |
| **No account / no auth / no cloud** | ❌ (dbt Cloud) | ❌ (HF Spaces) | ❌ (cloud) | ✅ |
| **No data leaves your machine** | ❌ | ❌ | ❌ | ✅ |
| Open source (MIT) | ✅ | ✅ | ✅ | ✅ |

---

## 📑 Table of contents

- [Quick start](#-quick-start)
- [How to use it with your dbt project](#-how-to-use-it-with-your-dbt-project)
- [What the app shows you](#-what-the-app-shows-you)
- [Architecture](#-architecture)
- [Project layout](#-project-layout)
- [Running the test suite](#-running-the-test-suite)
- [FAQ](#-faq)
- [Contributing](docs/CONTRIBUTING.md)
- [Security & privacy](SECURITY.md)
- [License](LICENSE)

---

## ⚡ Quick start

You need **Python 3.11 or newer** on your machine. That's it.

```bash
# 1. Clone
git clone https://github.com/noobigang/cascade-data.git
cd cascade-data

# 2. Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows PowerShell

# 3. Install
pip install -r requirements.txt

# 4. Run
streamlit run app.py
```

The app opens at **http://localhost:8502** in your browser. Click **🎲 Try Demo** to load a sample 20-node e-commerce project, or upload your own `manifest.json`.

> 🔒 The app binds to `127.0.0.1:8502` only. It is **not** reachable from the internet.

For platform-specific setup (Windows / macOS / Linux troubleshooting), see [SETUP_WINDOWS.md](SETUP_WINDOWS.md) or [SETUP_UNIX.md](SETUP_UNIX.md).

---

## 🧬 How to use it with your dbt project

The full walkthrough is in [docs/USAGE.md](docs/USAGE.md). The short version:

### Step 1 — generate the manifest

In your dbt project:

```bash
dbt build
# or: dbt compile
```

This produces `target/manifest.json`. Optionally also `target/catalog.json` (richer column descriptions from the warehouse).

### Step 2 — open Cascade

```bash
streamlit run app.py
```

### Step 3 — upload

Drag `target/manifest.json` onto the **📦 Upload** area in the sidebar. (Optionally drop `target/catalog.json` too.)

Cascade parses it in about 1-3 seconds for a 200-model project and renders the full lineage graph.

### Step 4 — explore

- **Click any node** to see its columns, types, and SQL.
- **Click a column** to see its upstream and downstream sub-tree at column granularity.
- **Click "View Full Blast Radius"** to see every model, every column, and every other thing affected by a change.
- **Use the search box** to jump to any model or column.
- **Use the filter chips** to show only models, only sources, only seeds.

---

## 👁️ What the app shows you

### The DAG (left panel)

- **Nodes** are dbt resources — models, sources, seeds, snapshots. Colored by type (blue=models, green=sources, gray=seeds, orange=snapshots).
- **Edges** are `ref()` / `source()` references. Hover to see the source column.
- **Click a node** to see its detail panel and its full column lineage.
- **Drag to pan**, **scroll to zoom**, **click-and-hold to drag a node** for fine-tuning.

### The detail panel (right side of DAG)

For the selected node:

- **Header** — type, schema, upstream/downstream count, risk score.
- **Columns** — name, data type, description, lineage indicator (colored dot).
  - 🟢 = leaf column (no upstream)
  - 🟡 = transformed column (modified)
  - 🔴 = passthrough column (verbatim from upstream)
- **Compiled SQL** and **Raw SQL** — expand to see what dbt will actually run.
- **Upstream / Downstream** — every other model this depends on or is depended on by.

### The blast-radius panel (below)

- **Risk score** with 🟢🟡🔴 indicator.
- **Affected models** — count and list.
- **Affected columns** — count and list.
- **Risk reasons** — why this score.

---

## 🏗️ Architecture

```
                 ┌────────────────────┐
   manifest.json │  parser.py         │
   ────────────► │  - extract nodes   │
                 │  - extract edges   │
                 │  - extract columns │
                 └─────────┬──────────┘
                           │
                           ▼
                 ┌────────────────────┐
                 │  models.py         │
                 │  LineageGraph      │ ◄── NetworkX DiGraph
                 │  (DiGraph wrapper) │
                 └─────────┬──────────┘
                           │
                           ▼
                 ┌────────────────────┐
                 │  sql_lineage.py     │ ◄── SQLGlot parses compiled SQL
                 │  ColumnLineage      │     and extracts column-level
                 │  records            │     dependencies
                 └─────────┬──────────┘
                           │
                           ▼
                 ┌────────────────────┐
                 │  impact.py          │
                 │  - blast radius     │
                 │  - risk scoring     │
                 │  - most connected   │
                 └─────────┬──────────┘
                           │
                           ▼
                 ┌────────────────────┐
                 │  Streamlit UI       │ ◄── D3.js DAG + tables
                 │  app.py             │
                 └────────────────────┘
```

The full module-by-module breakdown is in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). The column-lineage extraction algorithm is in [docs/COLUMN_LINEAGE.md](docs/COLUMN_LINEAGE.md).

---

## 📂 Project layout

```
cascade-data/
├── app.py                    ← Streamlit entry point
├── pyproject.toml            ← project metadata, ruff/mypy/pytest config
├── requirements.txt          ← pinned runtime dependencies
├── README.md                 ← you are here
├── SETUP_WINDOWS.md          ← step-by-step for Windows
├── SETUP_UNIX.md             ← step-by-step for macOS / Linux
├── SECURITY.md               ← why this app is local-only
├── CHANGELOG.md              ← version history
├── LICENSE                   ← MIT
├── CODE_OF_CONDUCT.md        ← community standards
│
├── lineage/
│   ├── __init__.py
│   ├── models.py             ← TableNode, ColumnNode, ColumnLineage, LineageGraph
│   ├── parser.py             ← manifest.json → LineageGraph
│   ├── sql_lineage.py        ← SQLGlot column-level extraction
│   └── impact.py             ← blast radius, risk scoring, connectivity
│
├── ui/
│   ├── __init__.py
│   ├── dag_viewer.py         ← D3.js DAG (embedded HTML)
│   ├── hero.py               ← dark theme + hero section
│   ├── sidebar.py            ← upload, filters, resource list
│   ├── detail_panel.py       ← node detail + column table
│   ├── scroll_bridge.py      ← DAG click → state bridge
│   └── upload_zone.py        ← manifest uploader
│
├── tests/
│   └── test_lineage.py        ← 44 tests (data models, parser, SQL lineage, impact)
│
├── demo/
│   ├── manifest.json          ← sample 20-node e-commerce project
│   └── build_manifest.py      ← regenerate the sample
│
├── docs/
│   ├── USAGE.md               ← step-by-step with your dbt project
│   ├── ARCHITECTURE.md        ← module-by-module deep dive
│   ├── COLUMN_LINEAGE.md      ← how column-level extraction works
│   └── CONTRIBUTING.md        ← dev setup, code style, PR process
│
└── .github/
    ├── workflows/ci.yml       ← ruff + mypy + pytest
    └── ISSUE_TEMPLATE/        ← bug report, feature request
```

---

## 🧪 Running the test suite

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

You should see:

```
tests/test_lineage.py::TestDataModels::test_column_node_defaults PASSED
tests/test_lineage.py::TestDataModels::test_column_node_full PASSED
... (44 tests)
============================== 44 passed in 0.6s ===============================
```

What the tests cover:
- **Data models** — TableNode, ColumnNode, ColumnLineage, LineageGraph (add/remove, edge cases, defaults)
- **Manifest parser** — parses a real dbt manifest, extracts nodes, edges, columns
- **Column lineage** — SQLGlot extracts column-level flows for SELECT, JOIN, CTE, window functions, CASE/WHEN
- **Blast radius** — full downstream tree, risk scoring, most-connected nodes
- **Integration** — full pipeline: manifest → graph → column lineage → impact report

---

## 💡 FAQ

### Why local-only?

A dbt `manifest.json` contains table names, column descriptions, compiled SQL, and database identifiers. That's proprietary metadata. Cascade runs entirely on your machine — no telemetry, no account, no third-party server. Read [SECURITY.md](SECURITY.md) for the full argument.

### Can I deploy it to share with my team?

You can, but I don't recommend it for the same reason above. If you must, **read [SECURITY.md](SECURITY.md) first.** The safest option is having each teammate run their own local instance — `git clone` is one line, `streamlit run` is one line.

### Why not just use dbt docs?

`dbt docs` shows model-level lineage. Cascade shows **column-level** lineage — which is what you need when a single column rename can break 30 downstream models. dbt docs also requires running `dbt docs generate` and serving the output; Cascade reads the same `manifest.json` directly.

### How big a manifest can it handle?

A 200-model / 2000-column project parses in about 1-3 seconds and renders smoothly. The DAG stays performant up to about 500 nodes. For projects beyond that, the auto-fit and zoom levels still work, but the node cards get small.

### Does it work with dbt Cloud?

Yes — `dbt Cloud` produces the same `manifest.json` as `dbt compile` locally. Just download it from your dbt Cloud account and drop it onto the upload area.

### Does it work with `dbt-core` 0.x, 1.x, 2.x?

The parser handles both the legacy `nodes`/`sources` structure and the modern unified `nodes` structure used in dbt 1.0+. If you hit a parsing issue, file an issue with your `manifest.json` schema version.

### Can I extend it with custom analyses?

Yes. The package is just `lineage/` + `ui/`. Write your own Python module that uses `LineageGraph` and `ImpactAnalyzer`, drop it next to the others, and import it from `app.py`.

---

## 📜 License

MIT — see [LICENSE](LICENSE).

## 🤝 Contributing

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md). All contributions welcome — bug reports, features, docs, tests.

## 🔒 Security

Read [SECURITY.md](SECURITY.md). Report vulnerabilities via GitHub Security Advisories.
