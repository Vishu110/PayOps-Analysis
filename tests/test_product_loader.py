from simulator.master_data.products import generate_products
from database.loaders.products import load_products


# ---------------------------------------------------------------------------
# Generate products
# ---------------------------------------------------------------------------

products = generate_products()

print(
    f"Generated {len(products):,} products."
)


# ---------------------------------------------------------------------------
# Load products
# ---------------------------------------------------------------------------

inserted_count = load_products(
    products
)

print(
    f"Successfully inserted "
    f"{inserted_count:,} products."
)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

assert inserted_count == len(products)

assert inserted_count > 0