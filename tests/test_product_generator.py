from collections import Counter
from decimal import Decimal

from database.loaders.merchants import fetch_merchants
from simulator.master_data.products import generate_products
from simulator.utils.config_loader import load_generator_config


# ---------------------------------------------------------------------------
# Generate products
# ---------------------------------------------------------------------------

products = generate_products()

print(
    f"Total products: {len(products):,}"
)


# ---------------------------------------------------------------------------
# Load merchants for validation
# ---------------------------------------------------------------------------

merchants = fetch_merchants()

merchant_lookup = {
    merchant["id"]: merchant
    for merchant in merchants
}


# ---------------------------------------------------------------------------
# Load configuration
# ---------------------------------------------------------------------------

config = load_generator_config()["products"]

merchant_category_mapping = config[
    "merchant_category_mapping"
]

products_per_merchant = config[
    "products_per_merchant"
]

price_ranges = config[
    "price_ranges"
]

refund_probability = config[
    "refund_probability"
]

chargeback_probability = config[
    "chargeback_probability"
]

valid_statuses = {
    "ACTIVE",
    "DISCONTINUED",
}


# ---------------------------------------------------------------------------
# Basic validation
# ---------------------------------------------------------------------------

assert len(products) > 0


# ---------------------------------------------------------------------------
# Product ID uniqueness
# ---------------------------------------------------------------------------

product_ids = [
    product["product_id"]
    for product in products
]

assert len(product_ids) == len(
    set(product_ids)
)


# ---------------------------------------------------------------------------
# Merchant FK validation
# ---------------------------------------------------------------------------

for product in products:

    merchant_fk = product[
        "merchant_fk"
    ]

    assert merchant_fk in merchant_lookup


# ---------------------------------------------------------------------------
# Product name uniqueness per merchant
# ---------------------------------------------------------------------------

merchant_product_names = {}

for product in products:

    merchant_fk = product[
        "merchant_fk"
    ]

    product_name = product[
        "product_name"
    ]

    merchant_product_names.setdefault(
        merchant_fk,
        []
    ).append(product_name)


for merchant_fk, names in (
    merchant_product_names.items()
):

    assert len(names) == len(
        set(names)
    )


# ---------------------------------------------------------------------------
# Product category validation
# ---------------------------------------------------------------------------

valid_product_categories = {
    "ELECTRONICS",
    "CLOTHING",
    "DIGITAL_GOODS",
    "SUBSCRIPTION",
    "HOME_APPLIANCES",
}


for product in products:

    category = product[
        "product_category"
    ]

    assert category in (
        valid_product_categories
    )


# ---------------------------------------------------------------------------
# Merchant → product category validation
# ---------------------------------------------------------------------------

for product in products:

    merchant = merchant_lookup[
        product["merchant_fk"]
    ]

    merchant_category = merchant[
        "merchant_category"
    ]

    product_category = product[
        "product_category"
    ]

    allowed_categories = (
        merchant_category_mapping[
            merchant_category
        ]["allowed_categories"]
    )

    assert product_category in (
        allowed_categories
    )


# ---------------------------------------------------------------------------
# Product count per merchant
# ---------------------------------------------------------------------------

product_counts = Counter(
    product["merchant_fk"]
    for product in products
)


for merchant in merchants:

    merchant_fk = merchant["id"]

    size_segment = merchant[
        "size_segment"
    ]

    bounds = products_per_merchant[
        size_segment
    ]

    count = product_counts[
        merchant_fk
    ]

    assert (
        bounds["min"]
        <= count
        <= bounds["max"]
    )


# ---------------------------------------------------------------------------
# Currency validation
# ---------------------------------------------------------------------------

for product in products:

    merchant = merchant_lookup[
        product["merchant_fk"]
    ]

    assert product[
        "currency"
    ] == merchant[
        "default_currency"
    ]


# ---------------------------------------------------------------------------
# Price validation
# ---------------------------------------------------------------------------

for product in products:

    category = product[
        "product_category"
    ]

    price = product[
        "base_price"
    ]

    bounds = price_ranges[
        category
    ]

    assert isinstance(
        price,
        Decimal,
    )

    assert (
        Decimal(str(bounds["min"]))
        <= price
        <= Decimal(str(bounds["max"]))
    )


# ---------------------------------------------------------------------------
# Refund probability validation
# ---------------------------------------------------------------------------

for product in products:

    category = product[
        "product_category"
    ]

    probability = product[
        "refund_probability"
    ]

    bounds = refund_probability[
        category
    ]

    assert (
        Decimal(str(bounds["min"]))
        <= probability
        <= Decimal(str(bounds["max"]))
    )


# ---------------------------------------------------------------------------
# Chargeback probability validation
# ---------------------------------------------------------------------------

for product in products:

    category = product[
        "product_category"
    ]

    probability = product[
        "chargeback_probability"
    ]

    bounds = chargeback_probability[
        category
    ]

    assert (
        Decimal(str(bounds["min"]))
        <= probability
        <= Decimal(str(bounds["max"]))
    )


# ---------------------------------------------------------------------------
# Refundability validation
# ---------------------------------------------------------------------------

non_refundable_categories = {
    "DIGITAL_GOODS",
    "SUBSCRIPTION",
}

for product in products:

    category = product[
        "product_category"
    ]

    refundable = product[
        "refundable"
    ]

    if category in non_refundable_categories:

        assert refundable is False

    else:

        assert refundable is True


# ---------------------------------------------------------------------------
# Product status validation
# ---------------------------------------------------------------------------

for product in products:

    assert product[
        "product_status"
    ] in valid_statuses


# ---------------------------------------------------------------------------
# Print merchant-level summary
# ---------------------------------------------------------------------------

for merchant in merchants[:10]:

    merchant_fk = merchant["id"]

    count = product_counts[
        merchant_fk
    ]

    print(
        f"{merchant['merchant_name']}: "
        f"{count} products"
    )


# ---------------------------------------------------------------------------
# Final validation
# ---------------------------------------------------------------------------

print(
    "\nAll product generator "
    "validation tests passed."
)