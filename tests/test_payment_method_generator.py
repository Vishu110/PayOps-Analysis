from collections import Counter, defaultdict
from datetime import date

from database.loaders.banks import fetch_banks
from database.loaders.customers import fetch_customers
from simulator.master_data.payment_methods import (
    generate_payment_methods,
)
from simulator.utils.config_loader import (
    load_generator_config,
)


# ---------------------------------------------------------------------------
# Generate data
# ---------------------------------------------------------------------------

payment_methods = generate_payment_methods()

customers = fetch_customers()
banks = fetch_banks()

config = load_generator_config()

simulation_date = config[
    "simulation"
]["current_date"]


print(
    f"Total payment methods: "
    f"{len(payment_methods):,}"
)


# ---------------------------------------------------------------------------
# Basic validation
# ---------------------------------------------------------------------------

assert len(payment_methods) > 0

assert len(customers) == 50_000

assert len(banks) == 12


# ---------------------------------------------------------------------------
# Lookup tables
# ---------------------------------------------------------------------------

customers_by_id = {
    customer["id"]: customer
    for customer in customers
}

banks_by_id = {
    bank["id"]: bank
    for bank in banks
}


# ---------------------------------------------------------------------------
# Expected enum values
# ---------------------------------------------------------------------------

VALID_PAYMENT_METHOD_TYPES = {
    "CARD",
}

VALID_CARD_NETWORKS = {
    "VISA",
    "MASTERCARD",
    "AMEX",
}

VALID_CARD_TYPES = {
    "CREDIT",
    "DEBIT",
}

VALID_STATUSES = {
    "ACTIVE",
    "EXPIRED",
    "BLOCKED",
}


# ---------------------------------------------------------------------------
# Payment-method ID uniqueness
# ---------------------------------------------------------------------------

payment_method_ids = [
    payment_method[
        "payment_method_id"
    ]
    for payment_method in payment_methods
]

assert len(
    payment_method_ids
) == len(
    set(payment_method_ids)
)


# ---------------------------------------------------------------------------
# Customer FK validation
# ---------------------------------------------------------------------------

for payment_method in payment_methods:

    customer_fk = payment_method[
        "customer_fk"
    ]

    assert customer_fk in customers_by_id


# ---------------------------------------------------------------------------
# Issuing-bank FK validation
# ---------------------------------------------------------------------------

for payment_method in payment_methods:

    bank_fk = payment_method[
        "issuing_bank_fk"
    ]

    assert bank_fk in banks_by_id


# ---------------------------------------------------------------------------
# Payment-method type validation
# ---------------------------------------------------------------------------

for payment_method in payment_methods:

    assert payment_method[
        "payment_method_type"
    ] in VALID_PAYMENT_METHOD_TYPES


# ---------------------------------------------------------------------------
# Card network validation
# ---------------------------------------------------------------------------

for payment_method in payment_methods:

    card_network = payment_method[
        "card_network"
    ]

    assert card_network in VALID_CARD_NETWORKS


# ---------------------------------------------------------------------------
# Card type validation
# ---------------------------------------------------------------------------

for payment_method in payment_methods:

    assert payment_method[
        "card_type"
    ] in VALID_CARD_TYPES


# ---------------------------------------------------------------------------
# Payment-method status validation
# ---------------------------------------------------------------------------

for payment_method in payment_methods:

    assert payment_method[
        "payment_method_status"
    ] in VALID_STATUSES


# ---------------------------------------------------------------------------
# Card last-four validation
# ---------------------------------------------------------------------------

for payment_method in payment_methods:

    last_four = payment_method[
        "card_last_four"
    ]

    assert len(last_four) == 4

    assert last_four.isdigit()


# ---------------------------------------------------------------------------
# Expiry month validation
# ---------------------------------------------------------------------------

for payment_method in payment_methods:

    expiry_month = payment_method[
        "expiry_month"
    ]

    assert 1 <= expiry_month <= 12


# ---------------------------------------------------------------------------
# Expiry/status consistency
# ---------------------------------------------------------------------------

for payment_method in payment_methods:

    status = payment_method[
        "payment_method_status"
    ]

    expiry_year = payment_method[
        "expiry_year"
    ]

    expiry_month = payment_method[
        "expiry_month"
    ]

    expiry_date = date(
        expiry_year,
        expiry_month,
        1,
    )

    # Active cards must not already be expired.
    if status == "ACTIVE":

        assert expiry_date > date(
            simulation_date.year,
            simulation_date.month,
            1,
        )

    # Expired cards must actually be expired.
    elif status == "EXPIRED":

        assert expiry_date < date(
            simulation_date.year,
            simulation_date.month,
            1,
        )


# ---------------------------------------------------------------------------
# Customer → bank country consistency
# ---------------------------------------------------------------------------

for payment_method in payment_methods:

    customer = customers_by_id[
        payment_method["customer_fk"]
    ]

    bank = banks_by_id[
        payment_method["issuing_bank_fk"]
    ]

    assert (
        customer["country_code"]
        == bank["country_code"]
    )


# ---------------------------------------------------------------------------
# Bank → card-network compatibility
# ---------------------------------------------------------------------------

for payment_method in payment_methods:

    bank = banks_by_id[
        payment_method["issuing_bank_fk"]
    ]

    supported_networks = set(
        bank[
            "supported_card_networks"
        ]
    )

    assert (
        payment_method["card_network"]
        in supported_networks
    )


# ---------------------------------------------------------------------------
# Group payment methods by customer
# ---------------------------------------------------------------------------

payment_methods_by_customer = (
    defaultdict(list)
)

for payment_method in payment_methods:

    payment_methods_by_customer[
        payment_method["customer_fk"]
    ].append(
        payment_method
    )


# ---------------------------------------------------------------------------
# Payment-method count validation
# ---------------------------------------------------------------------------

valid_payment_method_counts = {
    1,
    2,
    3,
    4,
}

for customer_id, methods in (
    payment_methods_by_customer.items()
):

    assert len(methods) in valid_payment_method_counts


# ---------------------------------------------------------------------------
# Exactly one default per customer
# ---------------------------------------------------------------------------

for customer_id, methods in (
    payment_methods_by_customer.items()
):

    default_count = sum(
        1
        for method in methods
        if method["is_default"]
    )

    assert default_count == 1


# ---------------------------------------------------------------------------
# No duplicate last-four per customer
# ---------------------------------------------------------------------------

for customer_id, methods in (
    payment_methods_by_customer.items()
):

    last_four_values = [
        method["card_last_four"]
        for method in methods
    ]

    assert len(
        last_four_values
    ) == len(
        set(last_four_values)
    )


# ---------------------------------------------------------------------------
# Distribution validation
# ---------------------------------------------------------------------------

method_count_distribution = Counter(
    len(methods)
    for methods
    in payment_methods_by_customer.values()
)

total_customers_with_methods = sum(
    method_count_distribution.values()
)

assert (
    total_customers_with_methods
    == len(payment_methods_by_customer)
)


print(
    "\nPayment-method count distribution:"
)

for count in sorted(
    method_count_distribution
):

    number_of_customers = (
        method_count_distribution[count]
    )

    percentage = (
        number_of_customers
        / total_customers_with_methods
        * 100
    )

    print(
        f"{count} payment method(s): "
        f"{number_of_customers:,} "
        f"({percentage:.2f}%)"
    )


# ---------------------------------------------------------------------------
# Card-type distribution
# ---------------------------------------------------------------------------

card_type_counts = Counter(
    payment_method["card_type"]
    for payment_method
    in payment_methods
)

print(
    "\nCard type distribution:"
)

for card_type, count in (
    card_type_counts.items()
):

    percentage = (
        count
        / len(payment_methods)
        * 100
    )

    print(
        f"{card_type}: "
        f"{count:,} "
        f"({percentage:.2f}%)"
    )


# ---------------------------------------------------------------------------
# Status distribution
# ---------------------------------------------------------------------------

status_counts = Counter(
    payment_method[
        "payment_method_status"
    ]
    for payment_method
    in payment_methods
)

print(
    "\nStatus distribution:"
)

for status, count in (
    status_counts.items()
):

    percentage = (
        count
        / len(payment_methods)
        * 100
    )

    print(
        f"{status}: "
        f"{count:,} "
        f"({percentage:.2f}%)"
    )


# ---------------------------------------------------------------------------
# Final validation
# ---------------------------------------------------------------------------

print(
    "\nAll payment method generator "
    "validation tests passed."
)