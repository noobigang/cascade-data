-- Fact table: orders enriched with customer data
-- Demonstrates: JOIN across models, window function for surrogate key,
-- CASE expression, multiple column-level transformations

with orders as (

    select * from {{ ref('stg_orders') }}

),

customers as (

    select * from {{ ref('stg_customers') }}

),

enriched as (

    select
        -- Surrogate key from order_id using md5 hash
        md5(o.order_id) as order_key,
        o.order_id,
        c.customer_key,
        o.order_date,
        o.status,
        o.amount as gross_revenue,
        c.full_name as customer_name
    from orders o
    left join customers c on o.customer_id = c.customer_id

),

final as (

    select
        order_key,
        order_id,
        customer_key,
        order_date,
        case
            when status = 'placed' then 'PLACED'
            when status = 'shipped' then 'SHIPPED'
            when status = 'completed' then 'COMPLETED'
            when status = 'returned' then 'RETURNED'
            else 'UNKNOWN'
        end as status,
        gross_revenue,
        customer_name
    from enriched

)

select * from final
