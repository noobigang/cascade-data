---
title: Cascade
emoji: 🧬
sdk: static
color: 0d1117
---

<p align="center">
  <img src="docs/demo.png" alt="Cascade — Column-Level Data Lineage" width="800" />
</p>

# Cascade — Column-Level Data Lineage 🧬

<p>
  <a href="https://github.com/noobigang/cascade-data/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT" /></a>
  <a href="https://github.com/noobigang/cascade-data/stargazers"><img src="https://img.shields.io/github/stars/noobigang/cascade-data?style=flat&logo=github" alt="GitHub Stars" /></a>
  <a href="https://huggingface.co/spaces/cascade-data"><img src="https://img.shields.io/badge/Deploy-Hugging%20Face%20Spaces-FFD9E9?style=flat" alt="Hugging Face Spaces" /></a>
  <a href="https://pypi.org/project/streamlit/"><img src="https://img.shields.io/badge/Python-3.9+-green.svg" alt="Python 3.9+" /></a>
</p>

**Cascade** is an interactive column-level data lineage tool for dbt projects. Drop in your `manifest.json` and instantly see the full blast radius of any model or column change — no setup, no auth, no database.

---

## ✨ Feature Highlights

| Feature | Description |
|---|---|
| 🧬 **Column-Level Lineage** | Trace data flows from source to sink at the column granularity, not just model-level |
| 💥 **Blast Radius Analysis** | Instantly see how many models, dashboards, and reports would break if you change a column |
| 📊 **Risk Scoring** | Color-coded risk indicators (🟢 Low / 🟡 Medium / 🔴 High) based on downstream impact |
| 🔗 **Share Cards** | Generate a one-click shareable URL — encode the full DAG view state, no account needed |
| ⚠️ **Two-Manifest Diff** (planned) | Upload before/after manifests to highlight breaking changes, dropped columns, and renamed fields |
| 📤 **Export** | Download lineage as JSON, blast-radius reports as Markdown, or the DAG as PNG/SVG |
| 🌐 **Hugging Face Spaces** | Auto-deploys on every push — anyone can explore without installing anything |

---

## 📊 Comparison

| Feature | Cascade | dbt-colibri | elementary |
|---|---|---|---|
| Column-level lineage | ✅ Native | ❌ Model-only | ⚠️ Partial |
| Interactive DAG | ✅ Live, clickable | ⚠️ Static HTML | ⚠️ Static HTML |
| Blast radius analysis | ✅ Full tree | ❌ | ❌ |
| Risk scoring (🟢🟡🔴) | ✅ | ❌ | ❌ |
| Two-manifest diff | ⚠️ Planned | ❌ | ✅ |
| Share cards / URL state | ✅ | ❌ | ❌ |
| Deployment | ✅ Auto (HF Spaces) | ⚠️ Manual | ⚠️ Manual |
| Open source | ✅ | ✅ | ✅ |
| No auth required | ✅ | ✅ | ❌ |
| dbt test overlay | Planned (v1.1) | ❌ | ✅ |
| BI tool integration | Planned (v1.2) | ❌ | ✅ |

---

## 🚀 Quick Start

```bash
# 1. Generate your manifest
dbt build   # produces target/manifest.json

# 2. Open the app
#    https://huggingface.co/spaces/cascade-data
#    OR run locally:
pip install -r requirements.txt
streamlit run cascade/app.py

# 3. Drop your manifest.json — Cascade maps everything instantly
```

Three lines. That's it. No credentials, no database, no dbt Cloud.

---

## 🏗️ Architecture

```
manifest.json
      │
      ▼
┌─────────────────────┐
│  manifest_parser.py  │  ← extracts nodes, columns, refs, tests
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  NetworkX DiGraph   │  ← directed graph of model → column dependencies
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   graph_builder.py  │  ← converts to PyVis HTML + edge labels
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Streamlit app.py  │  ← renders DAG, search, detail panel, share card
└─────────────────────┘
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full module breakdown.

---

## 🌐 Deployment

### Option A — Hugging Face Spaces (Recommended)

This repo is connected to [cascade-data on Hugging Face Spaces](https://huggingface.co/spaces/cascade-data). Every push to `main` automatically deploys.

To deploy your own fork:

1. **Fork** this repo
2. **Create** a new Space at [hf.co/new-space](https://huggingface.co/new-space) → select **Static** SDK
3. **Link** your forked repo under the Space settings → **Sync Git Repository**
4. **Push to `main`** — Cascade deploys automatically in ~60 seconds

No CI/CD pipeline needed. HF Spaces handles everything.

### Option B — Self-Hosted / CI/CD

```bash
# Build the image
docker build -t cascade-data .

# Run
docker run -p 8501:8501 cascade-data

# Or with Docker Compose
docker compose up -d
```

For GitHub Actions, GitLab CI, or other CI/CD pipelines, see [docs/DEPLOY.md](docs/DEPLOY.md).

---

## 🤝 Contributing

Contributions are welcome! See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for setup instructions, coding standards, and the PR process.

Quick start for local dev:

```bash
# Clone
git clone https://github.com/noobigang/cascade-data.git
cd cascade-data

# Create venv
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install deps
pip install -r requirements.txt

# Run
streamlit run cascade/app.py
```

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🔗 Links

- **Live App**: [huggingface.co/spaces/cascade-data](https://huggingface.co/spaces/cascade-data)
- **GitHub**: [github.com/noobigang/cascade-data](https://github.com/noobigang/cascade-data)
- **Issues**: [github.com/noobigang/cascade-data/issues](https://github.com/noobigang/cascade-data/issues)