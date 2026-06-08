# Contributing to Cascade

Thank you for your interest in contributing! Cascade is an open-source project and we welcome contributions of all kinds: code, documentation, bug reports, and feature requests.

---

## Getting Started

### Prerequisites

- Python 3.9 or higher
- Git
- A dbt project with a `manifest.json` to test against (any public dbt project works)

### Setup

```bash
# 1. Fork and clone
git clone https://github.com/<your-username>/cascade-data.git
cd cascade-data

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
.venv\Scripts\activate           # Windows PowerShell

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install dev dependencies (if any)
pip install -r requirements-dev.txt   # if it exists

# 5. Run the app
streamlit run cascade/app.py
```

The app will open at [http://localhost:8501](http://localhost:8501).

### Running Tests

```bash
# If tests are added:
pytest tests/

# Run with coverage:
pytest --cov=cascade --cov-report=term-missing
```

---

## Project Structure

```
cascade-data/
├── cascade/
│   ├── app.py                  # Streamlit entrypoint — start here
│   ├── parser/                 # manifest.json → structured data
│   ├── graph/                  # NetworkX graph operations
│   ├── ui/                     # Streamlit UI components
│   └── utils/                  # Shared utilities
├── docs/                        # This directory
│   ├── ARCHITECTURE.md
│   ├── COLUMN_LINEAGE.md
│   ├── DEPLOY.md
│   └── CONTRIBUTING.md         # (this file)
├── tests/                       # Test suite (add here)
├── requirements.txt
├── SPEC.md                      # Full product specification
└── README.md
```

---

## Coding Standards

### Python Style

- Follow **PEP 8**
- Use `black` for formatting (line length: 100)
- Use `isort` for import sorting
- Type hints for all public functions

```python
# Good
def parse_manifest(path: str) -> dict[str, ManifestNode]:
    ...

# Bad
def parse_manifest(path):
    ...
```

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add column-level edge labels on DAG hover
fix: handle missing 'columns' key in seed nodes
docs: add DEPLOY.md with Docker instructions
refactor: split impact_analyzer from lineage_graph
test: add pytest suite for column_resolver
```

### Pull Request Process

1. **Fork** the repo and create a feature branch:
   ```bash
   git checkout -b feat/your-feature-name
   ```

2. **Make your changes** — add tests, update docs, keep commits clean

3. **Run local checks**:
   ```bash
   black cascade/
   isort cascade/
   mypy cascade/          # if type stubs are available
   pytest tests/
   streamlit run cascade/app.py  # manual smoke test
   ```

4. **Open a PR** against `main`:
   - Title: follow Conventional Commits
   - Description: explain *why* this change, not just *what*
   - Link any related issues: `Closes #42`

5. **Review**: a maintainer will review within a few days. Address feedback, don't force-push.

6. **Merge**: squash-merge or merge-commit at maintainer's discretion.

---

## Reporting Bugs

Before opening a bug report:

1. **Check existing issues** — someone may have already reported it
2. **Reproduce with a public manifest** if possible (e.g., the dbt Jaffle Shop sample project)

Bug report template:

```
## Description
A clear description of the bug.

## Steps to Reproduce
1. Go to '...'
2. Upload '...' manifest
3. Click on '...'
4. See error / unexpected behavior

## Expected Behavior
What you expected to happen.

## Actual Behavior
What actually happened.

## Environment
- Browser: Chrome / Firefox / ...
- Manifest size: ~X nodes
- dbt version: X.X.X

## Possible Fix
Optional — your guess at the cause.
```

---

## Suggesting Features

Open a **Feature Request** issue with:

- **Problem**: What user problem does this solve?
- **Proposed solution**: How should it work?
- **Alternatives considered**: What else did you consider?
- **Priority**: Critical / High / Medium / Low (your assessment)

---

## Code of Conduct

Be respectful. We're data engineers helping each other. No politics, no snark, no gatekeeping.

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.