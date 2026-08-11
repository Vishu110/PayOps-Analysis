from collections import Counter

from simulator.master_data.customers import (
    COUNTRIES,
    generate_customers,
)

from simulator.master_data.customers import (
    COUNTRIES,
    generate_customers,
    normalize_name,
)


customers = generate_customers()

print(
    f"Total customers: {len(customers)}"
)


# ---------------------------------------------------------------------------
# Basic validation
# ---------------------------------------------------------------------------

assert len(customers) == 50_000

customer_ids = [
    customer["customer_id"]
    for customer in customers
]

emails = [
    customer["email"]
    for customer in customers
]

assert len(set(customer_ids)) == 50_000
assert len(set(emails)) == 50_000


# ---------------------------------------------------------------------------
# Country validation
# ---------------------------------------------------------------------------

country_counts = Counter(
    customer["country_code"]
    for customer in customers
)

print("\nCountry distribution:")

for country, count in country_counts.items():

    percentage = (
        count / len(customers)
    ) * 100

    print(
        f"{country}: "
        f"{count:,} "
        f"({percentage:.2f}%)"
    )


# ---------------------------------------------------------------------------
# Geographic consistency
# ---------------------------------------------------------------------------

for customer in customers:

    country_code = customer[
        "country_code"
    ]

    country = COUNTRIES[
        country_code
    ]

    # Country name
    assert (
        customer["country_name"]
        == country["name"]
    )

    # Currency
    assert (
        customer["preferred_currency"]
        == country["currency"]
    )

    # Timezone
    assert (
        customer["timezone"]
        == country["timezone"]
    )

    # State and city relationship
    valid_locations = []

    for state in country["states"].values():

        for city in state["cities"]:

            valid_locations.append(
                (state["name"], city)
            )

    assert (
        customer["state"],
        customer["city"],
    ) in valid_locations


# ---------------------------------------------------------------------------
# Signup date validation
# ---------------------------------------------------------------------------

for customer in customers:

    assert customer[
        "signup_date"
    ].year in {
        2021,
        2022,
        2023,
        2024,
        2025,
        2026,
    }


# ---------------------------------------------------------------------------
# Status / risk validation
# ---------------------------------------------------------------------------

valid_risk_segments = {
    "LOW",
    "MEDIUM",
    "HIGH",
}

valid_statuses = {
    "ACTIVE",
    "BLOCKED",
    "CLOSED",
}

for customer in customers:

    assert (
        customer["risk_segment"]
        in valid_risk_segments
    )

    assert (
        customer["customer_status"]
        in valid_statuses
    )


# ---------------------------------------------------------------------------
# Email/name relationship validation
# ---------------------------------------------------------------------------

for customer in customers:

    first = normalize_name(
        customer["first_name"]
    )

    last = normalize_name(
        customer["last_name"]
    )

    email_local_part = (
        customer["email"]
        .split("@")[0]
    )

    assert (
        first in email_local_part
        or last in email_local_part
    )


# ---------------------------------------------------------------------------
# Email validation
# ---------------------------------------------------------------------------

for customer in customers:

    email = customer["email"]

    assert "@" in email

    local_part, domain = email.split("@", 1)

    assert local_part
    assert domain
    assert "." in domain

print("\nAll customer validation tests passed.")