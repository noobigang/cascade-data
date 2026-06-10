# Using Cascade with your dbt project

This is a step-by-step walkthrough for using Cascade against a real dbt project. We'll go from a fresh `dbt init` to a populated column-level lineage graph in about 10 minutes.

---

## Prerequisites

- A working dbt project. If you don't have one, see the [dbt quickstart](https://docs.getbt.com/quickstarts) or use the bundled sample under `examples/jaffle_shop_minimal/`.
- Python 3.11+ on the same machine.
- ~500 MB free disk for the venv + dependencies.

---

## 1. Generate the manifest

In your dbt project directory:

```bash
# Compile (cheap — no warehouse queries)
dbt compile

# OR build (full pipeline — actually materializes tables)
dbt build
```

This produces `target/manifest.json` in your dbt project.

To verify:

```bash
ls -la target/manifest.json
# Should be a JSON file, typically 100KB - 50MB depending on project size
```

> **Optional but recommended:** also generate `target/catalog.json`. This contains richer column descriptions from the actual warehouse. Cascade will use it for column descriptions if present.
>
> ```bash
> dbt docs generate
> # produces target/catalog.json
> ```

---

## 2. Install Cascade

In a separate terminal (or wherever you keep Python projects):

```bash
git clone https://github.com/noobigang/cascade-data.git
cd cascade-data
python3 -m venv .venv
source .venv/bin/activate     # macOS / Linux
# .venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

See [SETUP_WINDOWS.md](../SETUP_WINDOWS.md) or [SETUP_UNIX.md](../SETUP_UNIX.md) for troubleshooting.

---

## 3. Launch Cascade

```bash
streamlit run app.py
```

A browser tab opens at **http://localhost:8502**.

---

## 4. Load your manifest

In the sidebar:

1. Under **📦 Upload Your Manifest**, click the dropzone.
2. Navigate to your dbt project's `target/manifest.json` and select it.
3. (Optional) Also drop `target/catalog.json` if you generated one.

Cascade parses the manifest in 1-3 seconds for a 200-model project, then renders the full DAG.

You should see the dashboard populated with:
- The hero stats bar (Models, Sources, Edges, Columns counts)
- The DAG with all your models, sources, and seeds
- The detail panel for the first node

---

## 5. Explore

### Click any node to inspect it

- **Header** shows type, schema, upstream/downstream count, risk score.
- **Columns** section shows every column in the model with type and description. The colored dot on the right is the lineage indicator:
  - 🟢 = leaf (no upstream)
  - 🟡 = transformed (modified)
  - 🔴 = passthrough (verbatim from upstream)
- **Compiled SQL** and **Raw SQL** expand to show the actual SQL.
- **Upstream** and **Downstream** sections list every other model this one depends on or is depended on by.

### Click a column to see its lineage sub-tree

Click any column row in the detail panel. You'll see a sub-tree showing:
- Where this column originated (the upstream source column)
- Every model that transforms it
- Every downstream model that uses it
- The chain of transformations in between

This is the killer feature — answering "what breaks if I change this column?" in one click.

### Use the search box

The sidebar has a search box that does fuzzy matching across model names, column names, and descriptions. Type `order_id` and jump straight to it.

### Use the filter chips

Top-left of the DAG: toggle **All / Models / Sources / Seeds / Snapshots** to focus on one type.

### Trigger a blast-radius report

At the bottom of the detail panel, click **View Full Blast Radius**. The app shows:
- A risk score (🟢 / 🟡 / 🔴) for changing this node
- The full downstream tree (every model, every column)
- Plain-language "why this score" reasons

This is what you show your PM when they ask "can we deprecate this model?".

---

## 6. Refresh after `dbt build`

When you re-run `dbt build` and the manifest changes, you don't need to restart Cascade. Just re-upload the new `manifest.json` — the app re-parses and re-renders.

---

## Troubleshooting

### `manifest.json` is too large

Cascade handles 200-500 node projects smoothly. For very large projects (1000+ models), the DAG may get crowded. Workarounds:

- Use the filter chips to focus on one resource type at a time.
- Zoom into a specific area of the DAG.
- For a full overview, take a screenshot from the DAG's "Fit to Screen" mode.

### Columns are missing descriptions

Cascade falls back to manifest descriptions. If your catalog has richer descriptions, drop `target/catalog.json` alongside the manifest.

### Parsing errors on edge-case SQL

If a model uses exotic SQL (e.g. some Snowflake or BigQuery UDFs) that SQLGlot doesn't understand, the column lineage for that model may be partial. The model will still appear in the DAG; just its column-level flows might be missing. Open an issue with the SQL snippet and we'll extend the parser.

### `dbt compile` fails

That's a dbt problem, not a Cascade problem. Fix it in your dbt project first.

### Port 8502 is already in use

```bash
streamlit run app.py --server.port 8503
```

---

## Next steps

- Read [ARCHITECTURE.md](ARCHITECTURE.md) to understand how the column-lineage extraction works.
- Read [COLUMN_LINEAGE.md](COLUMN_LINEAGE.md) for the technical details of the SQL parser.
- Open a feature request on GitHub if you have ideas.
