-- Customer dimension table
-- Demonstrates: column rename, surrogate key generation, computed column

with customers as (

    select * from {{ ref('stg_customers') }}

),

renamed as (

    select
        md5(customer_id) as customer_key,
        customer_id,
        full_name,
        email,
        created_at
    from customers

)

select * from renamed
