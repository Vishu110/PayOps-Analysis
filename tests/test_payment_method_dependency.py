from database.loaders.customers import fetch_customers
from database.loaders.banks import fetch_banks
from simulator.utils.config_loader import load_generator_config


# ---------------------------------------------------------------------------
# Load dependencies
# ---------------------------------------------------------------------------

customers = fetch_customers()
banks = fetch_banks()

print(
    f"Loaded {len(customers):,} customers from PostgreSQL."
)

print(
    f"Loaded {len(banks)} issuing banks from PostgreSQL."
)


# ---------------------------------------------------------------------------
# Expected values
# ---------------------------------------------------------------------------

VALID_CARD_NETWORKS = {
    "VISA",
    "MASTERCARD",
    "AMEX",
}


# ---------------------------------------------------------------------------
# Basic validation
# ---------------------------------------------------------------------------

assert len(customers) == 50_000
assert len(banks) == 12


# ---------------------------------------------------------------------------
# Build bank lookup by country
# ---------------------------------------------------------------------------

banks_by_country = {}

for bank in banks:

    country_code = bank[
        "country_code"
    ]

    banks_by_country.setdefault(
        country_code,
        []
    ).append(bank)


# ---------------------------------------------------------------------------
# Validate customer countries have eligible banks
# ---------------------------------------------------------------------------

customer_countries = {
    customer["country_code"]
    for customer in customers
}

for country_code in customer_countries:

    eligible_banks = banks_by_country.get(
        country_code,
        []
    )

    assert len(
        eligible_banks
    ) > 0


# ---------------------------------------------------------------------------
# Validate bank → card network compatibility
# ---------------------------------------------------------------------------

for bank in banks:

    supported_networks = set(
        bank["supported_card_networks"]
    )

    eligible_networks = (
        supported_networks
        & VALID_CARD_NETWORKS
    )

    assert len(
        eligible_networks
    ) > 0


# ---------------------------------------------------------------------------
# Validate payment-method configuration
# ---------------------------------------------------------------------------

config = load_generator_config()

payment_config = config[
    "payment_methods"
]

customer_config = config[
    "customers"
]


# ---------------------------------------------------------------------------
# Payment method type
# ---------------------------------------------------------------------------

assert payment_config[
    "payment_method_type"
] == "CARD"


# ---------------------------------------------------------------------------
# Payment methods per customer
# ---------------------------------------------------------------------------

payment_method_distribution = (
    customer_config[
        "payment_methods_per_customer"
    ]
)

expected_counts = {
    1,
    2,
    3,
    4,
}

assert set(
    int(count)
    for count
    in payment_method_distribution.keys()
) == expected_counts


distribution_total = sum(
    configuration["weight"]
    for configuration
    in payment_method_distribution.values()
)

assert abs(
    distribution_total - 100.0
) < 0.01


# ---------------------------------------------------------------------------
# Print country → bank relationship
# ---------------------------------------------------------------------------

for country_code in sorted(
    customer_countries
):

    customer_count = sum(
        1
        for customer in customers
        if customer["country_code"]
        == country_code
    )

    eligible_banks = banks_by_country[
        country_code
    ]

    print(
        f"\n{country_code}:"
    )

    print(
        f"  Customers: "
        f"{customer_count:,}"
    )

    print(
        f"  Eligible banks: "
        f"{len(eligible_banks)}"
    )

    for bank in eligible_banks:

        networks = (
            set(
                bank[
                    "supported_card_networks"
                ]
            )
            & VALID_CARD_NETWORKS
        )

        print(
            f"    {bank['bank_name']}: "
            f"{sorted(networks)}"
        )


# ---------------------------------------------------------------------------
# Final validation
# ---------------------------------------------------------------------------

print(
    "\nAll payment method dependency "
    "tests passed."
)