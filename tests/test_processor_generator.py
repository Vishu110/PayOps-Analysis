from simulator.master_data.processors import generate_processors


processors = generate_processors()


print(
    f"Total processors: {len(processors)}"
)


# ---------------------------------------------------------------------------
# Basic validation
# ---------------------------------------------------------------------------

assert len(processors) == 5


# ---------------------------------------------------------------------------
# Processor ID uniqueness
# ---------------------------------------------------------------------------

processor_ids = [
    processor["processor_id"]
    for processor in processors
]

assert len(processor_ids) == len(set(processor_ids))


# ---------------------------------------------------------------------------
# Processor name uniqueness
# ---------------------------------------------------------------------------

processor_names = [
    processor["processor_name"]
    for processor in processors
]

assert len(processor_names) == len(set(processor_names))


# ---------------------------------------------------------------------------
# Status validation
# ---------------------------------------------------------------------------

for processor in processors:

    assert processor["processor_status"] == "ACTIVE"


# ---------------------------------------------------------------------------
# Headquarters validation
# ---------------------------------------------------------------------------

for processor in processors:

    country_code = processor[
        "headquarters_country_code"
    ]

    country_name = processor[
        "headquarters_country_name"
    ]

    assert country_code
    assert country_name


# ---------------------------------------------------------------------------
# Supported regions validation
# ---------------------------------------------------------------------------

for processor in processors:

    assert processor["supported_regions"]

    for country_code in processor[
        "supported_regions"
    ]:

        assert len(country_code) == 2


# ---------------------------------------------------------------------------
# Card network validation
# ---------------------------------------------------------------------------

valid_networks = {
    "VISA",
    "MASTERCARD",
    "AMEX",
    "DISCOVER",
}

for processor in processors:

    assert processor["supported_card_networks"]

    for network in processor[
        "supported_card_networks"
    ]:

        assert network in valid_networks


# ---------------------------------------------------------------------------
# Processing fee validation
# ---------------------------------------------------------------------------

for processor in processors:

    fee = processor[
        "default_processing_fee_percentage"
    ]

    assert 0 <= fee <= 100


# ---------------------------------------------------------------------------
# Print generated records
# ---------------------------------------------------------------------------

for processor in processors:

    print(
        "\nProcessor:"
    )

    print(
        f"  ID: {processor['processor_id']}"
    )

    print(
        f"  Name: {processor['processor_name']}"
    )

    print(
        f"  Headquarters: "
        f"{processor['headquarters_country_name']} "
        f"({processor['headquarters_country_code']})"
    )

    print(
        f"  Regions: "
        f"{processor['supported_regions']}"
    )

    print(
        f"  Networks: "
        f"{processor['supported_card_networks']}"
    )

    print(
        f"  Fee: "
        f"{processor['default_processing_fee_percentage']}%"
    )

    print(
        f"  Status: "
        f"{processor['processor_status']}"
    )


print("\nAll processor validation tests passed.")