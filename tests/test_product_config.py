from simulator.utils.config_loader import load_generator_config


config = load_generator_config()
products_config = config["products"]


# ---------------------------------------------------------------------------
# Expected values
# ---------------------------------------------------------------------------

VALID_SIZE_SEGMENTS = {
    "SMALL",
    "MEDIUM",
    "LARGE",
    "ENTERPRISE",
}

VALID_STATUSES = {
    "ACTIVE",
    "DISCONTINUED",
}

VALID_MERCHANT_CATEGORIES = {
    "ECOMMERCE",
    "MARKETPLACE",
    "SAAS",
    "DIGITAL_GOODS",
}

VALID_PRODUCT_CATEGORIES = {
    "ELECTRONICS",
    "CLOTHING",
    "DIGITAL_GOODS",
    "SUBSCRIPTION",
    "HOME_APPLIANCES",
}


# ---------------------------------------------------------------------------
# Products per merchant validation
# ---------------------------------------------------------------------------

products_per_merchant = products_config[
    "products_per_merchant"
]

assert set(products_per_merchant.keys()) == (
    VALID_SIZE_SEGMENTS
)

for size_segment, bounds in products_per_merchant.items():

    minimum = bounds["min"]
    maximum = bounds["max"]

    assert isinstance(minimum, int)
    assert isinstance(maximum, int)

    assert minimum > 0
    assert maximum >= minimum


# ---------------------------------------------------------------------------
# Status distribution validation
# ---------------------------------------------------------------------------

status_distribution = products_config[
    "status_distribution"
]

assert set(status_distribution.keys()) == (
    VALID_STATUSES
)

status_weight_total = sum(
    status["weight"]
    for status in status_distribution.values()
)

assert abs(status_weight_total - 100.0) < 0.01

for status, configuration in status_distribution.items():

    weight = configuration["weight"]

    assert 0 <= weight <= 100


# ---------------------------------------------------------------------------
# Merchant category mapping validation
# ---------------------------------------------------------------------------

merchant_category_mapping = products_config[
    "merchant_category_mapping"
]

assert set(
    merchant_category_mapping.keys()
) == VALID_MERCHANT_CATEGORIES

for merchant_category, configuration in (
    merchant_category_mapping.items()
):

    allowed_categories = configuration[
        "allowed_categories"
    ]

    assert isinstance(
        allowed_categories,
        list,
    )

    assert len(allowed_categories) > 0

    for product_category in allowed_categories:

        assert product_category in (
            VALID_PRODUCT_CATEGORIES
        )


# ---------------------------------------------------------------------------
# Price range validation
# ---------------------------------------------------------------------------

price_ranges = products_config[
    "price_ranges"
]

assert set(price_ranges.keys()) == (
    VALID_PRODUCT_CATEGORIES
)

for product_category, bounds in price_ranges.items():

    minimum = bounds["min"]
    maximum = bounds["max"]

    assert isinstance(
        minimum,
        (int, float),
    )

    assert isinstance(
        maximum,
        (int, float),
    )

    assert minimum >= 0
    assert maximum > minimum


# ---------------------------------------------------------------------------
# Refund probability validation
# ---------------------------------------------------------------------------

refund_probability = products_config[
    "refund_probability"
]

assert set(refund_probability.keys()) == (
    VALID_PRODUCT_CATEGORIES
)

for product_category, bounds in (
    refund_probability.items()
):

    minimum = bounds["min"]
    maximum = bounds["max"]

    assert 0 <= minimum <= 1
    assert 0 <= maximum <= 1

    assert maximum >= minimum


# ---------------------------------------------------------------------------
# Chargeback probability validation
# ---------------------------------------------------------------------------

chargeback_probability = products_config[
    "chargeback_probability"
]

assert set(chargeback_probability.keys()) == (
    VALID_PRODUCT_CATEGORIES
)

for product_category, bounds in (
    chargeback_probability.items()
):

    minimum = bounds["min"]
    maximum = bounds["max"]

    assert 0 <= minimum <= 1
    assert 0 <= maximum <= 1

    assert maximum >= minimum


print(
    "All product configuration "
    "validation tests passed."
)