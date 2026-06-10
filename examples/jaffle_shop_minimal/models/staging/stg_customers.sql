-- Staging model: cleaned and typed customers
-- Source: raw.customers
-- Demonstrates: simple SELECT, string concatenation

with source as (

    select
        id as customer_id,
        first_name,
        last_name,
        first_name || ' ' || last_name as full_name,
        email,
        created_at
    from {{ source('raw', 'customers') }}

),

renamed as (

    select
        customer_id,
        first_name,
        last_name,
        full_name,
        email,
        created_at
    from source

)

select * from renamed
