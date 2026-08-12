from simulator.master_data.merchants import (
    generate_merchants,
)

from simulator.utils.config_loader import (
    load_merchants,
)

from database.loaders.processors import (
    fetch_processors,
)


# ---------------------------------------------------------------------------
# Generate merchant records
# ---------------------------------------------------------------------------

merchants = generate_merchants()

merchant_reference = load_merchants()["merchants"]

processors = fetch_processors()


print(
    f"Total merchants: {len(merchants)}"
)


# ---------------------------------------------------------------------------
# Build reference merchant lookup
# ---------------------------------------------------------------------------

reference_lookup = {}

for country_code, merchant_list in (
    merchant_reference.items()
):

    for merchant in merchant_list:

        merchant_key = merchant[
            "merchant_key"
        ]

        reference_lookup[
            merchant_key
        ] = {
            **merchant,
            "country_code": country_code,
        }


# ---------------------------------------------------------------------------
# Build processor lookup
# ---------------------------------------------------------------------------

processor_lookup = {
    processor["id"]: processor
    for processor in processors
}


# ---------------------------------------------------------------------------
# Basic validation
# ---------------------------------------------------------------------------

assert len(merchants) == 82, (
    f"Expected 82 merchants, "
    f"got {len(merchants)}."
)


# ---------------------------------------------------------------------------
# Merchant key uniqueness
# ---------------------------------------------------------------------------

merchant_keys = [
    merchant["merchant_key"]
    for merchant in merchants
]

assert len(merchant_keys) == len(
    set(merchant_keys)
), "Duplicate merchant_key detected."


# ---------------------------------------------------------------------------
# Merchant ID uniqueness
# ---------------------------------------------------------------------------

merchant_ids = [
    merchant["merchant_id"]
    for merchant in merchants
]

assert len(merchant_ids) == len(
    set(merchant_ids)
), "Duplicate merchant_id detected."


# ---------------------------------------------------------------------------
# Merchant name uniqueness
# ---------------------------------------------------------------------------

merchant_names = [
    merchant["merchant_name"]
    for merchant in merchants
]

assert len(merchant_names) == len(
    set(merchant_names)
), "Duplicate merchant_name detected."


# ---------------------------------------------------------------------------
# Legal name uniqueness
# ---------------------------------------------------------------------------

legal_names = [
    merchant["legal_name"]
    for merchant in merchants
]

assert len(legal_names) == len(
    set(legal_names)
), "Duplicate legal_name detected."


# ---------------------------------------------------------------------------
# Size segment validation
# ---------------------------------------------------------------------------

VALID_SIZE_SEGMENTS = {
    "SMALL",
    "MEDIUM",
    "LARGE",
    "ENTERPRISE",
}

for merchant in merchants:

    assert merchant[
        "size_segment"
    ] in VALID_SIZE_SEGMENTS, (
        f"Invalid size segment "
        f"'{merchant['size_segment']}' "
        f"for {merchant['merchant_name']}."
    )


# ---------------------------------------------------------------------------
# Country validation
# ---------------------------------------------------------------------------

VALID_COUNTRIES = {
    "IN",
    "US",
    "GB",
    "DE",
    "AU",
    "SG",
    "CA",
}

for merchant in merchants:

    country_code = merchant[
        "country_code"
    ]

    assert country_code in VALID_COUNTRIES, (
        f"Invalid country code "
        f"'{country_code}'."
    )

    assert merchant[
        "country_name"
    ], (
        f"Missing country name for "
        f"{merchant['merchant_name']}."
    )

    assert merchant[
        "default_currency"
    ], (
        f"Missing currency for "
        f"{merchant['merchant_name']}."
    )


# ---------------------------------------------------------------------------
# Category validation
# ---------------------------------------------------------------------------

VALID_CATEGORIES = {
    "ECOMMERCE",
    "SAAS",
    "MARKETPLACE",
    "DIGITAL_GOODS",
}

for merchant in merchants:

    category = merchant[
        "merchant_category"
    ]

    assert category in VALID_CATEGORIES, (
        f"Invalid category "
        f"'{category}' for "
        f"{merchant['merchant_name']}."
    )


# ---------------------------------------------------------------------------
# Category integrity against reference data
# ---------------------------------------------------------------------------

for merchant in merchants:

    merchant_key = merchant[
        "merchant_key"
    ]

    reference = reference_lookup[
        merchant_key
    ]

    assert (
        merchant["merchant_category"]
        in reference["categories"]
    ), (
        f"Generated category "
        f"'{merchant['merchant_category']}' "
        f"is not allowed for "
        f"{merchant['merchant_name']}."
    )


# ---------------------------------------------------------------------------
# Size segment integrity against reference data
# ---------------------------------------------------------------------------

for merchant in merchants:

    merchant_key = merchant[
        "merchant_key"
    ]

    reference = reference_lookup[
        merchant_key
    ]

    assert (
        merchant["size_segment"]
        == reference["size_segment"]
    ), (
        f"Size segment mismatch for "
        f"{merchant['merchant_name']}."
    )


# ---------------------------------------------------------------------------
# Risk validation
# ---------------------------------------------------------------------------

VALID_RISK_SEGMENTS = {
    "LOW",
    "MEDIUM",
    "HIGH",
}

for merchant in merchants:

    assert merchant[
        "risk_segment"
    ] in VALID_RISK_SEGMENTS, (
        f"Invalid risk segment "
        f"'{merchant['risk_segment']}' "
        f"for {merchant['merchant_name']}."
    )


# ---------------------------------------------------------------------------
# Status validation
# ---------------------------------------------------------------------------

VALID_STATUSES = {
    "ACTIVE",
    "SUSPENDED",
    "TERMINATED",
}

for merchant in merchants:

    assert merchant[
        "merchant_status"
    ] in VALID_STATUSES, (
        f"Invalid merchant status "
        f"'{merchant['merchant_status']}' "
        f"for {merchant['merchant_name']}."
    )


# ---------------------------------------------------------------------------
# Settlement cycle validation
# ---------------------------------------------------------------------------

VALID_SETTLEMENT_CYCLES = {
    0,
    1,
    2,
    3,
    7,
}

for merchant in merchants:

    assert merchant[
        "settlement_cycle"
    ] in VALID_SETTLEMENT_CYCLES, (
        f"Invalid settlement cycle "
        f"'{merchant['settlement_cycle']}' "
        f"for {merchant['merchant_name']}."
    )


# ---------------------------------------------------------------------------
# Processing fee validation
# ---------------------------------------------------------------------------

for merchant in merchants:

    fee = merchant[
        "default_processing_fee_percentage"
    ]

    assert 0 <= fee <= 100, (
        f"Invalid processing fee "
        f"{fee} for "
        f"{merchant['merchant_name']}."
    )


# ---------------------------------------------------------------------------
# Processor FK validation
# ---------------------------------------------------------------------------

for merchant in merchants:

    processor_fk = merchant[
        "preferred_processor_fk"
    ]

    assert processor_fk in processor_lookup, (
        f"Processor FK {processor_fk} "
        f"does not exist for "
        f"{merchant['merchant_name']}."
    )


# ---------------------------------------------------------------------------
# Processor-country eligibility validation
# ---------------------------------------------------------------------------

for merchant in merchants:

    processor = processor_lookup[
        merchant["preferred_processor_fk"]
    ]

    assert (
        merchant["country_code"]
        in processor["supported_regions"]
    ), (
        f"Merchant "
        f"{merchant['merchant_name']} "
        f"was assigned processor "
        f"{processor['processor_name']} "
        f"which does not support "
        f"country "
        f"{merchant['country_code']}."
    )


# ---------------------------------------------------------------------------
# Merchant identity consistency
# ---------------------------------------------------------------------------

for merchant in merchants:

    reference = reference_lookup[
        merchant["merchant_key"]
    ]

    assert (
        merchant["merchant_name"]
        == reference["merchant_name"]
    ), (
        f"Merchant name mismatch for "
        f"{merchant['merchant_key']}."
    )

    assert (
        merchant["legal_name"]
        == reference["legal_name"]
    ), (
        f"Legal name mismatch for "
        f"{merchant['merchant_key']}."
    )

    assert (
        merchant["country_code"]
        == reference["country_code"]
    ), (
        f"Country mismatch for "
        f"{merchant['merchant_key']}."
    )


# ---------------------------------------------------------------------------
# Print sample records
# ---------------------------------------------------------------------------

for merchant in merchants[:10]:

    print(
        "\nMerchant:"
    )

    print(
        f"  Key: "
        f"{merchant['merchant_key']}"
    )

    print(
        f"  ID: "
        f"{merchant['merchant_id']}"
    )

    print(
        f"  Name: "
        f"{merchant['merchant_name']}"
    )

    print(
        f"  Legal Name: "
        f"{merchant['legal_name']}"
    )

    print(
        f"  Category: "
        f"{merchant['merchant_category']}"
    )

    print(
        f"  Size: "
        f"{merchant['size_segment']}"
    )

    print(
        f"  Country: "
        f"{merchant['country_name']} "
        f"({merchant['country_code']})"
    )

    print(
        f"  Currency: "
        f"{merchant['default_currency']}"
    )

    processor = processor_lookup[
        merchant["preferred_processor_fk"]
    ]

    print(
        f"  Processor: "
        f"{processor['processor_name']} "
        f"(FK: "
        f"{merchant['preferred_processor_fk']})"
    )

    print(
        f"  Settlement: "
        f"T+{merchant['settlement_cycle']}"
    )

    print(
        f"  Processing Fee: "
        f"{merchant['default_processing_fee_percentage']}%"
    )

    print(
        f"  Risk: "
        f"{merchant['risk_segment']}"
    )

    print(
        f"  Status: "
        f"{merchant['merchant_status']}"
    )

    print(
        f"  Onboarded: "
        f"{merchant['onboarded_date']}"
    )


print(
    "\nAll merchant generator "
    "validation tests passed."
)