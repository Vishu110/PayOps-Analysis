from datetime import date

from simulator.utils.config_loader import (
    load_generator_config,
)


config = load_generator_config()

payment_config = config[
    "payment_methods"
]

simulation_config = config[
    "simulation"
]


# ---------------------------------------------------------------------------
# Expected enum values
# ---------------------------------------------------------------------------

VALID_STATUSES = {
    "ACTIVE",
    "EXPIRED",
    "BLOCKED",
}

VALID_CARD_TYPES = {
    "CREDIT",
    "DEBIT",
}


# ---------------------------------------------------------------------------
# Status distribution
# ---------------------------------------------------------------------------

status_distribution = payment_config[
    "status_distribution"
]

assert set(
    status_distribution.keys()
) == VALID_STATUSES

status_total = sum(
    configuration["weight"]
    for configuration
    in status_distribution.values()
)

assert abs(
    status_total - 100.0
) < 0.01

for configuration in (
    status_distribution.values()
):

    assert 0 <= configuration[
        "weight"
    ] <= 100


# ---------------------------------------------------------------------------
# Card type distribution
# ---------------------------------------------------------------------------

card_type_distribution = payment_config[
    "card_type_distribution"
]

assert set(
    card_type_distribution.keys()
) == VALID_CARD_TYPES

card_type_total = sum(
    configuration["weight"]
    for configuration
    in card_type_distribution.values()
)

assert abs(
    card_type_total - 100.0
) < 0.01

for configuration in (
    card_type_distribution.values()
):

    assert 0 <= configuration[
        "weight"
    ] <= 100


# ---------------------------------------------------------------------------
# Payment method type
# ---------------------------------------------------------------------------

# The current generator intentionally generates CARD payment
# methods only because the payment_methods schema contains
# card-specific fields that are NOT nullable.

assert payment_config[
    "payment_method_type"
] == "CARD"


# ---------------------------------------------------------------------------
# Expiry configuration
# ---------------------------------------------------------------------------

expiry_config = payment_config[
    "expiry"
]

active_expiry = expiry_config[
    "active"
]

expired_expiry = expiry_config[
    "expired"
]


# Active expiry range

assert isinstance(
    active_expiry["min_year"],
    int,
)

assert isinstance(
    active_expiry["max_year"],
    int,
)

assert (
    active_expiry["min_year"]
    <= active_expiry["max_year"]
)


# Expired expiry range

assert isinstance(
    expired_expiry["min_year"],
    int,
)

assert isinstance(
    expired_expiry["max_year"],
    int,
)

assert (
    expired_expiry["min_year"]
    <= expired_expiry["max_year"]
)


# ---------------------------------------------------------------------------
# Simulation date
# ---------------------------------------------------------------------------

simulation_date = simulation_config[
    "current_date"
]

assert isinstance(
    simulation_date,
    date,
)


# ---------------------------------------------------------------------------
# Expiry-year relationship with simulation date
# ---------------------------------------------------------------------------

assert (
    active_expiry["min_year"]
    > simulation_date.year
)

assert (
    expired_expiry["min_year"]
    < simulation_date.year
)

assert (
    expired_expiry["max_year"]
    <= simulation_date.year
)


print(
    "All payment method configuration "
    "validation tests passed."
)