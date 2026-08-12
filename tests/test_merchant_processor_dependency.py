from simulator.master_data.merchants import (
    MERCHANT_CONFIG,
    get_eligible_processors,
    select_preferred_processor,
)

from database.loaders.processors import fetch_processors


# ---------------------------------------------------------------------------
# Load existing processors from PostgreSQL
# ---------------------------------------------------------------------------

processors = fetch_processors()

assert processors, (
    "No processors found in PostgreSQL."
)

print(
    f"Loaded {len(processors)} processors "
    "from PostgreSQL."
)


# ---------------------------------------------------------------------------
# Load merchants from reference configuration
# ---------------------------------------------------------------------------

merchants_by_country = (
    MERCHANT_CONFIG["merchants"]
)


total_merchants = 0
total_eligible_relationships = 0


# ---------------------------------------------------------------------------
# Validate every merchant's processor eligibility
# ---------------------------------------------------------------------------

for country_code, merchants in (
    merchants_by_country.items()
):

    print(
        f"\n{country_code}:"
    )

    for merchant in merchants:

        total_merchants += 1

        merchant_name = merchant[
            "merchant_name"
        ]

        eligible_processors = (
            get_eligible_processors(
                country_code=country_code,
                processors=processors,
            )
        )

        assert eligible_processors, (
            f"No eligible processor found for "
            f"{merchant_name} ({country_code})."
        )

        total_eligible_relationships += (
            len(eligible_processors)
        )

        print(
            f"  {merchant_name}: "
            f"{len(eligible_processors)} "
            f"eligible processors"
        )


# ---------------------------------------------------------------------------
# Validate processor selection
# ---------------------------------------------------------------------------

for country_code, merchants in (
    merchants_by_country.items()
):

    for merchant in merchants:

        eligible_processors = (
            get_eligible_processors(
                country_code=country_code,
                processors=processors,
            )
        )

        selected_processor = (
            select_preferred_processor(
                eligible_processors
            )
        )

        assert selected_processor in (
            eligible_processors
        ), (
            f"Selected processor is not eligible "
            f"for {merchant['merchant_name']}."
        )


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

print(
    f"\nTotal merchants validated: "
    f"{total_merchants}"
)

print(
    f"Total eligible merchant-processor "
    f"relationships: "
    f"{total_eligible_relationships}"
)

print(
    "\nAll merchant-processor dependency "
    "tests passed."
)