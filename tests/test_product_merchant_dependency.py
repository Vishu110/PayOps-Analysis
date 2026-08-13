from database.loaders.merchants import fetch_merchants
from simulator.utils.config_loader import load_generator_config


# ---------------------------------------------------------------------------
# Load merchants
# ---------------------------------------------------------------------------

merchants = fetch_merchants()

print(
    f"Loaded {len(merchants)} merchants from PostgreSQL."
)


# ---------------------------------------------------------------------------
# Basic validation
# ---------------------------------------------------------------------------

assert len(merchants) == 82


# ---------------------------------------------------------------------------
# Required fields
# ---------------------------------------------------------------------------

required_fields = {
    "id",
    "merchant_id",
    "merchant_name",
    "merchant_category",
    "size_segment",
    "country_code",
    "country_name",
    "default_currency",
}


for merchant in merchants:

    assert required_fields.issubset(
        merchant.keys()
    )


# ---------------------------------------------------------------------------
# Merchant ID validation
# ---------------------------------------------------------------------------

merchant_ids = [
    merchant["id"]
    for merchant in merchants
]

assert len(merchant_ids) == len(
    set(merchant_ids)
)


# ---------------------------------------------------------------------------
# Configuration validation
# ---------------------------------------------------------------------------

config = load_generator_config()

merchant_category_mapping = config[
    "products"
]["merchant_category_mapping"]

products_per_merchant = config[
    "products"
]["products_per_merchant"]


# ---------------------------------------------------------------------------
# Merchant business-rule validation
# ---------------------------------------------------------------------------

for merchant in merchants:

    merchant_category = merchant[
        "merchant_category"
    ]

    size_segment = merchant[
        "size_segment"
    ]

    assert merchant_category in (
        merchant_category_mapping
    )

    assert size_segment in (
        products_per_merchant
    )

    allowed_categories = (
        merchant_category_mapping[
            merchant_category
        ]["allowed_categories"]
    )

    assert len(allowed_categories) > 0


# ---------------------------------------------------------------------------
# Sample output
# ---------------------------------------------------------------------------

for merchant in merchants[:10]:

    merchant_category = merchant[
        "merchant_category"
    ]

    allowed_categories = (
        merchant_category_mapping[
            merchant_category
        ]["allowed_categories"]
    )

    size_segment = merchant[
        "size_segment"
    ]

    product_range = products_per_merchant[
        size_segment
    ]

    print(
        f"\n{merchant['merchant_name']}:"
    )

    print(
        f"  Category: {merchant_category}"
    )

    print(
        f"  Size: {size_segment}"
    )

    print(
        f"  Currency: "
        f"{merchant['default_currency']}"
    )

    print(
        f"  Allowed product categories: "
        f"{allowed_categories}"
    )

    print(
        f"  Product count range: "
        f"{product_range['min']}"
        f"-"
        f"{product_range['max']}"
    )


print(
    "\nAll product-merchant dependency "
    "tests passed."
)