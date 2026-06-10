# Changelog

All notable changes to Cascade are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] — 2026-06-11

The first production-ready release. Local-first, MIT licensed, fully self-hosted.

### Added

- **Column-level lineage** — SQLGlot parses compiled SQL and traces data flows from source column to destination column
- **Interactive D3.js DAG** — dagre-laid-out static graph (no physics flinging) with type-colored node cards (model/source/seed/snapshot), zoom, pan, drag
- **Multi-hop chain highlighting** — selecting a node dims unrelated nodes and keeps the full upstream/downstream chain visible
- **Click-to-detail** — clicking any node opens its detail panel with columns, types, descriptions, compiled/raw SQL, and upstream/downstream lists
- **Click-to-column** — clicking a column shows its full upstream origin and downstream consumers
- **Blast-radius analysis** — every model and column has a risk score (🟢 Low / 🟡 Medium / 🔴 High) and full downstream tree
- **Filter chips** — toggle All / Models / Sources / Seeds / Snapshots
- **Search** — fuzzy search across model names, column names, and descriptions
- **Auto-demo** — sample 20-node e-commerce project loaded on first run
- **Column lineage indicators** — colored dots showing leaf (🟢), transformed (🟡), or passthrough (🔴) status
- **Compiled SQL and Raw SQL** expanders per node
- **Streamlit-internal click bridge** — uses `streamlit-js-eval` for clean DAG→state round-trip (no broken icon fonts)
- **44 pytest tests** — data models, parser, SQL lineage (CTEs, JOINs, window functions, CASE/WHEN), impact
- **CI on every push** — ruff lint, mypy type check, pytest, all green
- **Comprehensive docs** — README, SECURITY, SETUP_WINDOWS, SETUP_UNIX, docs/USAGE, docs/ARCHITECTURE, docs/COLUMN_LINEAGE, docs/CONTRIBUTING

### Technical

- **Stack**: Streamlit 1.58+, SQLGlot 25+, NetworkX 3+, pandas, streamlit-js-eval
- **DAG rendering**: D3.js v7 with dagre layout (embedded via `st.components.v1.html`)
- **Python**: 3.11+ required
- **License**: MIT
- **Distribution**: self-hosted only, runs on `localhost`; no account, no cloud, no telemetry
- **Test coverage**: 44 tests, all passing
- **Type checking**: mypy strict-ish on `lineage/` and `ui/`
- **Linting**: ruff with E, F, W, I, N, UP, B, C4, SIM

### Security

- App binds to `127.0.0.1:8502` only (not `0.0.0.0`)
- No outbound requests except Google Fonts and Streamlit component runtime
- No telemetry, no analytics, no phone-home
- `manifest.json` parsed in memory; never written to disk by Cascade

---

## [0.2.0] — 2026-06-09

Migrated from PyVis (force-directed) to D3.js with dagre (static layout). Static layout is professional, predictable, and matches what users expect from data-tool documentation.

### Changed

- DAG: PyVis (vis.js force-directed) → D3.js v7 + dagre (static left-to-right)
- File structure: `cascade/` (legacy) → `cascade-rebuild/` (working) → root (final)
- Package name: `cascade-data` → `cascade`

### Removed

- Hugging Face Spaces deployment (replaced with self-host guidance — see [SECURITY.md](SECURITY.md))
- Docker image (instructions only — see [docs/DEPLOY.md](docs/DEPLOY.md))
- Share cards (URL state encoding) — deferred
- Export to PNG/SVG — deferred

---

## [0.1.0] — 2026-06-08

Initial prototype. PyVis-based DAG, full feature set, Hugging Face Spaces deployment.

---

## Versioning Policy

Cascade uses **Semantic Versioning** (MAJOR.MINOR.PATCH):

- **MAJOR** — breaking changes to the API or data model
- **MINOR** — new features, backward-compatible
- **PATCH** — bug fixes, documentation, refactoring

Tags follow the format `v{version}` (e.g., `v1.0.0`).

---

## Roadmap

Things we'd like to add but haven't yet:

- **Two-manifest diff** — upload a "before" and "after" manifest, see what changed (new models, dropped columns, renamed fields, breaking changes)
- **dbt test overlay** — highlight columns with failing dbt tests on the DAG
- **Column popularity scoring** — rank columns by number of downstream consumers
- **dbt Cloud live sync** — pull manifest directly from dbt Cloud API
- **Export to PNG/SVG** — for embedding in docs and design reviews

If you want any of these, open an issue. PRs welcome.
