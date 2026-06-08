# Cascade Demo — E-Commerce Analytics Dataset

This manifest represents a realistic e-commerce data warehouse built with dbt. It contains **15 nodes** across 5 layers: source → staging → intermediate → mart → seed.

---

## Layer Overview

| Layer | Count | Description |
|---|---|---|
| **Source** | 4 | Raw tables from Shopify (orders, customers, products) and ad platforms (Google Ads, Meta Ads) |
| **Seed** | 2 | Static reference tables: `dim_date` (fiscal calendar) and `dim_channel` (marketing channel taxonomy) |
| **Staging** | 4 | Clean, normalized, UTC-normalized copies of source data |
| **Intermediate** | 3 | Business logic joins; computed metrics (order items, daily sales, customer cohorts) |
| **Mart** | 5 | Business-ready aggregates for analytics teams |

---

## DAG Structure

```
                    ┌─────────────────────┐
                    │  source.ecommerce.raw_orders      │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │   stg_orders        │──────┐
                    └──────────┬──────────┘      │
                               │                │
              ┌────────────────┼────────────────┤
              │                │                │
    ┌─────────▼───┐   ┌─────────▼───┐   ┌──────▼──────┐
    │ stg_customers│   │ stg_products │   │stg_marketing│
    └──────┬──────┘   └──────┬──────┘   └──────┬──────┘
           │                 │                 │
           └────────┬────────┘                 │
                    │                          │
          ┌─────────▼──────────┐    ┌──────────▼──────────┐
          │ int_order_items   │    │stg_marketing_events │
          └─────────┬──────────┘    └──────────┬──────────┘
                    │                          │
          ┌─────────┼──────────────┐           │
          │         │              │           │
┌─────────▼───┐  ┌──▼──┐    ┌─────▼──────┐   │
│mart_revenue  │  │mart │    │ mart_mktg_roi │
└─────────────┘  │_inv.│    └─────┬──────┘   │
                  └──┬──┘          │          │
                     │            │           │
        ┌────────────┼────────────┼──────────┘
        │            │            │
┌───────▼────┐  ┌───▼──────┐  ┌─▼──────────────┐
│mart_product│  │mart_cust  │
│_perf       │  │_analytics │
└────────────┘  └──────────┘

seed.dim_date  ─────── feeds all marts
seed.dim_channel ───── feeds stg_marketing_events & mart_product_performance
```

---

## Node Catalog

### Sources (raw)

| Node | Description |
|---|---|
| `raw_orders` | All Shopify orders including pending/cancelled. 7 columns. |
| `raw_customers` | Shopify customer profiles. 8 columns. |
| `raw_products` | Product catalog with inventory. 8 columns. |
| `raw_marketing` | Google Ads + Meta Ads daily spend. 8 columns. |

### Seeds

| Node | Description |
|---|---|
| `dim_date` | Fiscal calendar, 2020–2030. **Feeds all 5 marts.** Priority: **MEDIUM**. |
| `dim_channel` | Marketing channel taxonomy (paid/owned/earned). |

### Staging Models

| Node | Depends On | Description |
|---|---|---|
| `stg_orders` | `raw_orders` | Completed orders only, UTC-normalized. |
| `stg_customers` | `raw_customers` | Deduplicated latest record per customer. |
| `stg_products` | `raw_products` | Normalized categories, computed margin. |
| `stg_marketing_events` | `raw_marketing`, `dim_channel` | Daily channel aggregates with group labels. |

### Intermediate Models

| Node | Depends On | Description |
|---|---|---|
| `int_order_items` | `stg_orders`, `stg_customers`, `stg_products` | Line-level joins: order × product. Core computation node. |
| `int_customer_signups` | `stg_customers` | Cohort signup counts by date/country. |
| `int_daily_sales` | `stg_orders` | Daily rollup with date_key for dim_date join. |

### Mart Models

| Node | Priority | Depends On | Description |
|---|---|---|---|
| `mart_revenue` | **HIGH** | `int_order_items`, `dim_date` | Revenue, margin, order count. Feeds exec dashboards. |
| `mart_customer_analytics` | MEDIUM | `int_customer_signups`, `dim_date` | Cohort retention curves. Feeds growth team. |
| `mart_marketing_roi` | **HIGH** (leaf) | `int_order_items`, `int_daily_sales`, `stg_marketing_events` | Channel ROAS, CPA. Feeds budget decisions. |
| `mart_product_performance` | MEDIUM | `int_order_items`, `dim_date`, `dim_channel` | Sales by category/channel. Feeds merchandising. |
| `mart_inventory` | MEDIUM | `int_order_items`, `dim_date` | Stock levels, sell-through, reorder alerts. |

---

## Key Lineage Facts

- **`stg_orders`** is the most critical staging node — it feeds **3 marts** (`mart_revenue`, `mart_marketing_roi`, `mart_inventory`) making it the highest-risk change point.
- **`dim_date`** is a low-change seed that every mart depends on — a schema change here would require full refresh of all 5 marts.
- **`mart_marketing_roi`** is the only leaf mart with no downstream consumers — it is the terminal node of the DAG.
- **`int_order_items`** is the widest intermediate node — joins orders, customers, and products to produce line-level financial data.

---

## Testing Cascade on This Dataset

Use the **"Try Demo"** button in the Cascade UI to load this manifest instantly without uploading a file.

Or upload manually: run `dbt build` in your dbt project, then upload `target/manifest.json`.

Try these queries in Cascade:
1. Select `stg_orders` → see its blast radius (3 downstream marts)
2. Select `mart_marketing_roi` → see it has no downstream consumers
3. Search `mart_` → see all 5 mart nodes and their dependencies
4. Filter by type: uncheck "Sources" to focus on models only