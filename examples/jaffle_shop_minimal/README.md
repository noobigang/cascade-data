# Example dbt project for Cascade

This is a minimal dbt project you can use to test Cascade. It's a 4-model
e-commerce pipeline: `raw_orders` and `raw_customers` (sources) → 
`stg_orders` and `stg_customers` (staging) → `fct_orders` and 
`dim_customers` (marts).

## Quick start

```bash
# 1. Install dbt (pick your adapter — postgres shown here)
pip install dbt-postgres

# 2. Configure your warehouse connection
#    Edit profiles.yml or set DBT_PROFILES_DIR

# 3. Run the project
cd jaffle_shop_minimal
dbt build

# 4. Open Cascade and upload target/manifest.json
#    (in another terminal)
streamlit run path/to/cascade-data/app.py
```

## Layout

```
jaffle_shop_minimal/
├── dbt_project.yml
├── profiles.yml
├── models/
│   ├── staging/
│   │   ├── stg_orders.sql
│   │   └── stg_customers.sql
│   └── marts/
│       ├── fct_orders.sql
│       └── dim_customers.sql
└── seeds/
    └── (empty — uses sources instead)
```

## Notes

- Sources (`raw_orders`, `raw_customers`) are defined in the staging models'
  `sources.yml` files. If you don't have a real warehouse with these tables,
  you can either:
  - Replace them with `seeds/` (CSV files loaded into the warehouse)
  - Mock the sources with `dbt seed` + small CSVs
- Column names use `snake_case` throughout. Cascade handles any naming
  convention, but this is the dbt-idiomatic style.
- Descriptions are provided in `sources.yml` and schema YAMLs. Cascade
  reads these for the column descriptions in the detail panel.
