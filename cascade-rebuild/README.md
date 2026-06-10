# 🌊 Cascade — Column-Level Data Lineage Dashboard

> **This app is designed to run locally on your own machine.**
> Your `manifest.json` can contain sensitive metadata (table names, column descriptions, model SQL), so Cascade does not phone home, does not require any account, and never sends your data to a third-party server.

A self-hosted, single-binary dashboard for exploring **column-level lineage** in dbt projects. Drop in a `manifest.json`, get an interactive DAG, drill into column dependencies, and see the blast radius of any change before you ship it.

Built to beat [dbt-colibri](https://github.com/b-ned/dbt-colibri) in features, UX, and visual design.

---

## ⚡ Quick start (60 seconds)

You need **Python 3.11 or newer** on your machine. That's it.

```bash
# 1. Clone the repo
git clone https://github.com/noobigang/cascade-data.git
cd cascade-data/cascade-rebuild

# 2. Create a virtual environment (recommended)
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On macOS / Linux:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the dashboard
streamlit run app.py
```

Streamlit will print something like:

```
You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8502
  Network URL: http://192.168.x.x:8502
```

Open `http://localhost:8502` in your browser. Click **🎲 Try Demo** to load a sample 20-node e-commerce project, or upload your own `manifest.json`.

> **Heads up:** the app binds to `localhost` only by default. It is not reachable from the internet. Don't change that.

---

## 🔍 Where do I get `manifest.json`?

Run this in your dbt project:

```bash
dbt compile   # or: dbt build
```

This creates `target/manifest.json` in your dbt project. Drop that file onto the **📦 Upload** area in the dashboard, and Cascade will parse it and render the full lineage.

Optional: also drop `target/catalog.json` for richer column descriptions (column data types come from the manifest, descriptions come from the catalog).

---

## 📋 Detailed setup

If the quick start didn't work, or you want more detail:

- **Windows users:** see [SETUP_WINDOWS.md](SETUP_WINDOWS.md) for step-by-step terminal screenshots and common pitfalls (Python not on PATH, port 8502 already in use, etc.)
- **macOS / Linux users:** see [SETUP_UNIX.md](SETUP_UNIX.md) for the same

Both cover:
- Installing Python 3.11+
- Creating a virtual environment
- Resolving the most common `pip install` errors
- What to do if `streamlit: command not found`
- What to do if port 8502 is taken
- How to run the test suite

---

## 🧪 Run the test suite

The lineage engine has 44 tests covering SQL parsing, blast-radius scoring, edge cases (CTEs, JOINs, window functions, CASE/WHEN), and full-pipeline integration.

```bash
pip install pytest
pytest tests/ -v
```

Expected output:

```
============================== 44 passed in 0.6s ===============================
```

---

## 🏗️ Tech stack

| Layer | Technology |
|---|---|
| Dashboard | Streamlit |
| DAG visualization | D3.js v7 (embedded via `st.components.v1.html`) |
| Lineage extraction | SQLGlot (SQL parsing) + NetworkX (graph) |
| Data model | Python dataclasses |
| Tests | pytest (44 passing) |
| Lint / types | ruff + mypy |

No database, no API keys, no cloud service. Just a `pip install` and a `streamlit run`.

---

## 📂 Project layout

```
cascade-data/
├── cascade-rebuild/
│   ├── app.py                  ← Streamlit entry point
│   ├── pyproject.toml          ← project metadata
│   ├── requirements.txt        ← pinned runtime deps
│   ├── SETUP_WINDOWS.md        ← step-by-step for Windows
│   ├── SETUP_UNIX.md           ← step-by-step for macOS/Linux
│   ├── SECURITY.md             ← why this app is local-only
│   ├── lineage/
│   │   ├── models.py           ← TableNode, ColumnNode, LineageGraph
│   │   ├── parser.py           ← manifest.json → LineageGraph
│   │   ├── sql_lineage.py      ← SQLGlot column extraction
│   │   └── impact.py           ← blast radius, risk scoring
│   ├── ui/
│   │   ├── dag_viewer.py       ← D3.js DAG
│   │   ├── hero.py             ← hero section + dark theme
│   │   ├── sidebar.py          ← upload, filters, resource list
│   │   ├── detail_panel.py     ← node detail + column table
│   │   └── scroll_bridge.py    ← click → state bridge
│   ├── demo/
│   │   └── manifest.json       ← 20-node e-commerce demo graph
│   └── tests/
│       └── test_lineage.py     ← 44 tests
├── .github/workflows/ci.yml    ← ruff + mypy + pytest
├── LICENSE
└── README.md
```

---

## 🔒 Security & privacy

Read [SECURITY.md](SECURITY.md). The short version:

- The app binds to `localhost` (127.0.0.1) by default. It is not reachable from your network or the internet.
- No telemetry, no analytics, no phone-home.
- Your `manifest.json` is parsed in memory and never written to disk by Cascade.
- All processing happens in your local Python process. Nothing leaves your machine.
- Don't run it on a public server unless you've reviewed the code and understand the implications.

---

## 🤝 Contributing

PRs welcome. Before opening a PR:

```bash
pytest tests/ -v
ruff check .
mypy lineage/ ui/ --config-file pyproject.toml
```

All three must pass.

---

## 📄 License

MIT — see [LICENSE](LICENSE).
