from simulator.utils.config_loader import (
    load_countries,
    load_merchants,
)


# ---------------------------------------------------------------------------
# Load configuration
# ---------------------------------------------------------------------------

countries_config = load_countries()
merchants_config = load_merchants()

countries = countries_config["countries"]
merchants_by_country = merchants_config["merchants"]


# ---------------------------------------------------------------------------
# Expected configuration values
# ---------------------------------------------------------------------------

VALID_CATEGORIES = {
    "ECOMMERCE",
    "SAAS",
    "MARKETPLACE",
    "DIGITAL_GOODS",
}

VALID_SIZE_SEGMENTS = {
    "SMALL",
    "MEDIUM",
    "LARGE",
    "ENTERPRISE",
}


# ---------------------------------------------------------------------------
# Basic structure validation
# ---------------------------------------------------------------------------

assert merchants_by_country, (
    "Merchant configuration is empty."
)


# ---------------------------------------------------------------------------
# Country validation
# ---------------------------------------------------------------------------

for country_code in merchants_by_country:

    assert country_code in countries, (
        f"Unknown country code '{country_code}' "
        "in merchants.yaml."
    )


# ---------------------------------------------------------------------------
# Merchant validation
# ---------------------------------------------------------------------------

merchant_keys = []
merchant_names = []
legal_names = []

total_merchants = 0

for country_code, merchants in merchants_by_country.items():

    assert merchants, (
        f"No merchants configured for "
        f"country '{country_code}'."
    )

    for merchant in merchants:

        total_merchants += 1

        # Required fields
        required_fields = {
            "merchant_key",
            "merchant_name",
            "legal_name",
            "categories",
            "size_segment",
        }

        missing_fields = (
            required_fields
            - merchant.keys()
        )

        assert not missing_fields, (
            f"Merchant '{merchant.get('merchant_key')}' "
            f"is missing fields: {missing_fields}"
        )

        # ---------------------------------------------------------------
        # Merchant key
        # ---------------------------------------------------------------

        merchant_key = merchant["merchant_key"]

        assert merchant_key, (
            "merchant_key cannot be empty."
        )

        merchant_keys.append(merchant_key)

        # ---------------------------------------------------------------
        # Merchant name
        # ---------------------------------------------------------------

        merchant_name = merchant["merchant_name"]

        assert merchant_name, (
            f"Empty merchant_name for "
            f"'{merchant_key}'."
        )

        merchant_names.append(merchant_name)

        # ---------------------------------------------------------------
        # Legal name
        # ---------------------------------------------------------------

        legal_name = merchant["legal_name"]

        assert legal_name, (
            f"Empty legal_name for "
            f"'{merchant_key}'."
        )

        legal_names.append(legal_name)

        # ---------------------------------------------------------------
        # Categories
        # ---------------------------------------------------------------

        categories = merchant["categories"]

        assert categories, (
            f"Merchant '{merchant_key}' "
            "must have at least one category."
        )

        for category in categories:

            assert category in VALID_CATEGORIES, (
                f"Invalid category '{category}' "
                f"for merchant '{merchant_key}'."
            )

        # ---------------------------------------------------------------
        # Size segment
        # ---------------------------------------------------------------

        size_segment = merchant["size_segment"]

        assert size_segment in VALID_SIZE_SEGMENTS, (
            f"Invalid size segment "
            f"'{size_segment}' "
            f"for merchant '{merchant_key}'."
        )


# ---------------------------------------------------------------------------
# Uniqueness validation
# ---------------------------------------------------------------------------

assert len(merchant_keys) == len(set(merchant_keys)), (
    "Duplicate merchant_key detected."
)

assert len(merchant_names) == len(set(merchant_names)), (
    "Duplicate merchant_name detected."
)

assert len(legal_names) == len(set(legal_names)), (
    "Duplicate legal_name detected."
)


# ---------------------------------------------------------------------------
# Expected countries
# ---------------------------------------------------------------------------

expected_countries = {
    "IN",
    "US",
    "GB",
    "DE",
    "AU",
    "SG",
    "CA",
}

assert set(merchants_by_country.keys()) == expected_countries, (
    "Merchant geography does not match "
    "the configured project geography."
)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

print(
    f"Total merchant reference records: "
    f"{total_merchants}"
)

print(
    f"Countries represented: "
    f"{len(merchants_by_country)}"
)

print(
    "\nMerchant reference distribution:"
)

for country_code, merchants in merchants_by_country.items():

    print(
        f"{country_code}: "
        f"{len(merchants)} merchants"
    )


print(
    "\nAll merchant reference "
    "validation tests passed."
)