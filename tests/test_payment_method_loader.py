from simulator.master_data.payment_methods import (
    generate_payment_methods,
)

from database.loaders.payment_methods import (
    load_payment_methods,
)


# ---------------------------------------------------------------------------
# Generate payment methods
# ---------------------------------------------------------------------------

payment_methods = generate_payment_methods()

print(
    f"Generated "
    f"{len(payment_methods):,} payment methods."
)


# ---------------------------------------------------------------------------
# Load payment methods
# ---------------------------------------------------------------------------

inserted_count = load_payment_methods(
    payment_methods
)


print(
    f"Successfully inserted "
    f"{inserted_count:,} payment methods."
)


# ---------------------------------------------------------------------------
# Basic validation
# ---------------------------------------------------------------------------

assert inserted_count == len(
    payment_methods
)