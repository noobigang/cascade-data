-- Staging model: cleaned and typed orders
-- Source: raw.orders
-- Demonstrates: simple SELECT, column rename, type casting

with source as (

    select
        id as order_id,
        user_id as customer_id,
        order_date,
        status,
        coalesce(amount, 0) as amount
    from {{ source('raw', 'orders') }}

),

renamed as (

    select
        order_id,
        customer_id,
        order_date,
        status,
        amount
    from source

)

select * from renamed
