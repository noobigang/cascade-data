# Changelog

All notable changes to Cascade are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-06-08

### Added

- **Column-level lineage DAG** — trace data flows from source to sink at column granularity, not just model-level
- **Blast radius analysis** — instantly see all downstream dependents of any model or column change
- **Risk scoring** — color-coded indicators (🟢 Low / 🟡 Medium / 🔴 High) based on downstream impact count
- **Share cards** — generate one-click shareable URLs that encode the full DAG view state, no account needed
- **Export: JSON** — download the full lineage graph structure as JSON
- **Export: Markdown** — download blast-radius reports as formatted Markdown
- **Export: PNG/SVG** — download the DAG as a rasterized or vector image
- **Hugging Face Spaces deployment** — auto-deploys on every push to `main`, no manual infra needed
- **manifest.json parser** — full support for dbt 1.x `target/manifest.json` including models, sources, seeds, and refs
- **Interactive PyVis DAG** — force-directed graph with hover labels, click-to-select, pan, and zoom
- **Model detail panel** — slide-up panel showing columns, data types, upstream sources, and downstream dependents
- **Impact search** — query any model or column and see its upstream dependency tree or downstream blast radius
- **No auth required** — fully stateless, all state in browser URL params
- **Command-center dark UI** — mission control aesthetic with teal accents, JetBrains Mono typography
- **This documentation suite** — ARCHITECTURE.md, COLUMN_LINEAGE.md, DEPLOY.md, CONTRIBUTING.md

### Technical

- **Stack**: Streamlit, NetworkX, PyVis, Python 3.9+
- **Deployment**: Hugging Face Spaces (Static SDK), Docker, bare-metal
- **License**: MIT

---

## [Unreleased]

### Planned

- Two-manifest diff (change alert) — upload before/after manifests to highlight breaking changes
- dbt test results overlay — highlight columns with failing tests on the DAG
- BI tool integration — Metabase, Looker, Mode dashboard linkage
- Column popularity scoring — rank columns by number of downstream consumers
- `@cascade upstream:` annotation parser — enable manual column-level overrides via model descriptions
- dbt Cloud live sync — pull manifest directly from dbt Cloud API

---

## Versioning Policy

Cascade uses **Semantic Versioning** (MAJOR.MINOR.PATCH):

- **MAJOR** — breaking changes to the API or data model
- **MINOR** — new features, backward-compatible
- **PATCH** — bug fixes, documentation, refactoring

Tags follow the format `v{version}` (e.g., `v0.1.0`).