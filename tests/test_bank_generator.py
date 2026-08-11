from simulator.master_data.banks import generate_banks


banks = generate_banks()


print(
    f"Total banks: {len(banks)}"
)


# ---------------------------------------------------------------------------
# Basic validation
# ---------------------------------------------------------------------------

assert len(banks) == 12


# ---------------------------------------------------------------------------
# Bank ID uniqueness
# ---------------------------------------------------------------------------

bank_ids = [
    bank["bank_id"]
    for bank in banks
]

assert len(bank_ids) == len(set(bank_ids))


# ---------------------------------------------------------------------------
# Bank code uniqueness
# ---------------------------------------------------------------------------

bank_codes = [
    bank["bank_code"]
    for bank in banks
]

assert len(bank_codes) == len(set(bank_codes))


# ---------------------------------------------------------------------------
# Bank name uniqueness
# ---------------------------------------------------------------------------

bank_names = [
    bank["bank_name"]
    for bank in banks
]

assert len(bank_names) == len(set(bank_names))


# ---------------------------------------------------------------------------
# Status validation
# ---------------------------------------------------------------------------

for bank in banks:

    assert bank["bank_status"] == "ACTIVE"


# ---------------------------------------------------------------------------
# Country validation
# ---------------------------------------------------------------------------

for bank in banks:

    assert len(bank["country_code"]) == 2
    assert bank["country_name"]


# ---------------------------------------------------------------------------
# Card-network validation
# ---------------------------------------------------------------------------

valid_networks = {
    "VISA",
    "MASTERCARD",
    "AMEX",
    "DISCOVER",
    "RUPAY",
}

for bank in banks:

    assert bank["supported_card_networks"]

    for network in bank[
        "supported_card_networks"
    ]:

        assert network in valid_networks


# ---------------------------------------------------------------------------
# Print generated records
# ---------------------------------------------------------------------------

for bank in banks:

    print(
        "\nBank:"
    )

    print(
        f"  ID: {bank['bank_id']}"
    )

    print(
        f"  Name: {bank['bank_name']}"
    )

    print(
        f"  Code: {bank['bank_code']}"
    )

    print(
        f"  Country: "
        f"{bank['country_name']} "
        f"({bank['country_code']})"
    )

    print(
        f"  Networks: "
        f"{bank['supported_card_networks']}"
    )

    print(
        f"  Status: "
        f"{bank['bank_status']}"
    )


print("\nAll bank validation tests passed.")