# Column-Level Lineage

Cascade tracks data dependencies at the **column** level — not just model-to-model, but which specific column in model A flows into which specific column in model B.

---

## How It Works

### Step 1 — Extract Nodes and Columns from manifest.json

Each model node in the manifest has a `columns` dict and a `depends_on` list:

```json
{
  "nodes": {
    "model.my_project.stg_orders": {
      "columns": {
        "order_id":    { "name": "order_id",    "type": "string", "description": "Primary key" },
        "order_value": { "name": "order_value", "type": "float",  "description": "Total order amount" },
        "customer_id": { "name": "customer_id", "type": "integer" }
      },
      "depends_on": ["model.my_project.stg_payments"]
    }
  }
}
```

Cascade parses all nodes, extracts their columns, and stores column metadata (name, data type, description) as **node attributes** on the NetworkX graph.

### Step 2 — Build Column-Level Edges

For each `depends_on` relationship, Cascade traverses the dependency and attempts to match columns by name:

```
stg_payments                 stg_orders
  ├── payment_id ────────────────► order_id        (same name → column link)
  ├── amount    ────────────────► order_value      (same name → column link)
  └── customer_id ───────────────► customer_id     (same name → column link)
```

This name-matching heuristic covers the vast majority of dbt projects. The assumption: if `model_A` depends on `model_B` and both have a column named `user_id`, the column flows through.

> **Limitation**: Rename transformations (e.g., `order_id AS order_number`) are not tracked in the manifest and cannot be resolved automatically. See [Limitations](#limitations) below.

### Step 3 — Store as Edge Attributes

The column-level relationship is stored as an **edge attribute** on the NetworkX graph:

```python
G.add_edge(
    "stg_payments",
    "stg_orders",
    columns=["payment_id", "amount", "customer_id"]
)
```

This preserves the full graph at column resolution while keeping the model-level DAG clean for rendering.

### Step 4 — Render at the Right Level

| View | What is shown |
|---|---|
| **Full DAG** | Model-level nodes + column labels on hover |
| **Node click** | Upstream/downstream columns listed in detail panel |
| **Column search** | Full column-level dependency tree |
| **Blast radius** | Column-level expansion when user queries a specific column |

---

## Column Resolver Algorithm

The column resolver (`column_resolver.py`) handles the tricky cases:

```python
def resolve_columns(upstream_node, downstream_node) -> list[str]:
    """
    Given an upstream model and a downstream model that depends on it,
    return the list of column names that flow between them.
    """
    upstream_cols = set(upstream_node.columns.keys())
    downstream_cols = set(downstream_node.columns.keys())

    # 1. Exact name match
    exact = upstream_cols & downstream_cols

    # 2. Alias match (configurable)
    #    e.g., stg_payments.amount → stg_orders.order_value
    #    requires explicit column-level config in dbt_project.yml

    # 3. Wildcard match (e.g., * → *)
    #    not implemented in v0.1 — too noisy

    return sorted(exact)
```

---

## Limitations

### Rename Transformations

dbt's manifest does not record column rename operations (e.g., `order_id AS order_number`). Cascade cannot infer these and will treat `order_number` in the downstream model as having no upstream source.

**Workaround**: Document column-level dependencies in the model's description field using `@cascade upstream: model.column` annotations. Future versions will parse these annotations.

### Multiple Sources

If a column is populated by a `UNION ALL` of multiple upstream models, Cascade will show edges from each source. This is correct but may produce visually noisy graphs.

### dbt Tests as Lineage

dbt tests (`unique`, `not_null`, `relationships`) are stored as separate node types in the manifest. Cascade extracts them and attaches them as node attributes (e.g., "order_id is unique and not null"). They do not currently appear as graph edges, but this is planned for v1.1.

---

## Hypergraph Model

Strictly speaking, column-level lineage is a **hypergraph**: an edge can connect one upstream node to one downstream node but carry multiple column labels.

Cascade models this as a **directed multigraph** where:
- Each node is a model (or source/seed)
- Each edge is a dependency relationship
- Edge attributes carry the list of flowing columns

This is more compact than a true hypergraph representation and works with standard NetworkX algorithms.

---

## Future Enhancements

- [ ] Parse `@cascade upstream:` annotations in model descriptions
- [ ] Parse dbt `macro` calls for macro-level lineage
- [ ] Column popularity scoring (how many downstream consumers)
- [ ] dbt test results overlay (highlight columns with test failures)
- [ ] SQL-level column tracking via `dbt ls --output json` + AST parsing