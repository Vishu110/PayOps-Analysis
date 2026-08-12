from collections import Counter

from database.loaders.processors import fetch_processors
from simulator.master_data.merchants import (
    get_eligible_processors,
    select_preferred_processor,
)


# ---------------------------------------------------------------------------
# Load processors
# ---------------------------------------------------------------------------

processors = fetch_processors()

assert len(processors) == 5


# ---------------------------------------------------------------------------
# Get India-eligible processors
# ---------------------------------------------------------------------------

eligible_processors = get_eligible_processors(
    country_code="IN",
    processors=processors,
)

eligible_names = {
    processor["processor_name"]
    for processor in eligible_processors
}


# ---------------------------------------------------------------------------
# India eligibility validation
# ---------------------------------------------------------------------------

assert "Worldpay" not in eligible_names

assert eligible_names == {
    "Stripe",
    "Adyen",
    "Checkout.com",
    "PayPal",
}


# ---------------------------------------------------------------------------
# Simulate processor selection
# ---------------------------------------------------------------------------

iterations = 10_000

selections = [
    select_preferred_processor(
        eligible_processors
    )["processor_name"]
    for _ in range(iterations)
]

counts = Counter(selections)


# ---------------------------------------------------------------------------
# Worldpay must never be selected
# ---------------------------------------------------------------------------

assert counts.get("Worldpay", 0) == 0


# ---------------------------------------------------------------------------
# All eligible processors should be selectable
# ---------------------------------------------------------------------------

for processor_name in eligible_names:

    assert counts[processor_name] > 0


# ---------------------------------------------------------------------------
# Expected normalized probabilities
# ---------------------------------------------------------------------------

expected_weights = {
    "Stripe": 37.95,
    "Adyen": 27.93,
    "Checkout.com": 21.86,
    "PayPal": 12.26,
}


# ---------------------------------------------------------------------------
# Validate observed distribution
# ---------------------------------------------------------------------------

for processor_name, expected_percentage in (
    expected_weights.items()
):

    observed_percentage = (
        counts[processor_name]
        / iterations
        * 100
    )

    print(
        f"{processor_name}: "
        f"{counts[processor_name]} "
        f"({observed_percentage:.2f}%) "
        f"expected ~{expected_percentage:.2f}%"
    )

    # Random sampling means we should not expect exact percentages.
    assert abs(
        observed_percentage
        - expected_percentage
    ) <= 3.0


print(
    "\nProcessor selection weighting "
    "validation passed."
)