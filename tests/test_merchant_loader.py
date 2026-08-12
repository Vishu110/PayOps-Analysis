from simulator.master_data.merchants import generate_merchants
from database.loaders.merchants import load_merchants


# ---------------------------------------------------------------------------
# Generate merchants
# ---------------------------------------------------------------------------

merchants = generate_merchants()

print(
    f"Generated {len(merchants):,} merchants."
)


# ---------------------------------------------------------------------------
# Load merchants
# ---------------------------------------------------------------------------

inserted_count = load_merchants(merchants)

print(
    f"Successfully inserted {inserted_count:,} merchants."
)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

assert inserted_count == len(merchants)

assert inserted_count == 82