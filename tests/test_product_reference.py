from simulator.utils.config_loader import load_products


# ---------------------------------------------------------------------------
# Load reference data
# ---------------------------------------------------------------------------

product_reference = load_products()

products = product_reference["products"]


# ---------------------------------------------------------------------------
# Required categories
# ---------------------------------------------------------------------------

EXPECTED_CATEGORIES = {
    "ELECTRONICS",
    "CLOTHING",
    "DIGITAL_GOODS",
    "SUBSCRIPTION",
    "HOME_APPLIANCES",
}


assert set(products.keys()) == EXPECTED_CATEGORIES


# ---------------------------------------------------------------------------
# Category validation
# ---------------------------------------------------------------------------

for category, product_names in products.items():

    assert isinstance(
        product_names,
        list,
    )

    assert len(product_names) > 0


# ---------------------------------------------------------------------------
# Product name validation
# ---------------------------------------------------------------------------

all_product_names = []


for category, product_names in products.items():

    for product_name in product_names:

        assert isinstance(
            product_name,
            str,
        )

        assert product_name.strip()

        all_product_names.append(
            product_name
        )


# ---------------------------------------------------------------------------
# Duplicate validation
# ---------------------------------------------------------------------------

assert len(all_product_names) == len(
    set(all_product_names)
)


# ---------------------------------------------------------------------------
# Category-level product counts
# ---------------------------------------------------------------------------

for category, product_names in products.items():

    print(
        f"{category}: "
        f"{len(product_names)} products"
    )


# ---------------------------------------------------------------------------
# Overall validation
# ---------------------------------------------------------------------------

print(
    f"\nTotal reference products: "
    f"{len(all_product_names)}"
)

print(
    "All product reference "
    "validation tests passed."
)