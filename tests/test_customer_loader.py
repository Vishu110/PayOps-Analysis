from simulator.master_data.customers import generate_customers
from database.loaders.customers import load_customers


customers = generate_customers()

print(
    f"Generated {len(customers):,} customers."
)

inserted_count = load_customers(customers)

print(
    f"Successfully inserted "
    f"{inserted_count:,} customers."
)

assert inserted_count == 50_000