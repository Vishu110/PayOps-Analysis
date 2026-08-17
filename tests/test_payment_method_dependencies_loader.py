from database.loaders.customers import fetch_customers
from database.loaders.banks import fetch_banks


customers = fetch_customers()
banks = fetch_banks()


print(
    f"Loaded customers: {len(customers):,}"
)

print(
    f"Loaded banks: {len(banks)}"
)


# ---------------------------------------------------------------------------
# Basic validation
# ---------------------------------------------------------------------------

assert len(customers) == 50_000
assert len(banks) == 12


# ---------------------------------------------------------------------------
# Customer fields
# ---------------------------------------------------------------------------

required_customer_fields = {
    "id",
    "customer_id",
    "country_code",
    "country_name",
    "preferred_currency",
    "risk_segment",
    "customer_status",
}

for customer in customers:

    assert required_customer_fields.issubset(
        customer.keys()
    )


# ---------------------------------------------------------------------------
# Bank fields
# ---------------------------------------------------------------------------

required_bank_fields = {
    "id",
    "bank_id",
    "bank_name",
    "bank_code",
    "country_code",
    "country_name",
    "supported_card_networks",
    "bank_status",
}

for bank in banks:

    assert required_bank_fields.issubset(
        bank.keys()
    )


# ---------------------------------------------------------------------------
# Bank network validation
# ---------------------------------------------------------------------------

for bank in banks:

    assert isinstance(
        bank["supported_card_networks"],
        list,
    )

    assert len(
        bank["supported_card_networks"]
    ) > 0


print(
    "\nCustomer and bank dependency "
    "loaders passed."
)