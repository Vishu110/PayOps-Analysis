from decimal import Decimal, ROUND_HALF_UP
import random

from database.loaders.merchants import fetch_merchants
from simulator.utils.config_loader import (
    load_generator_config,
    load_products,
)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PRODUCT_CONFIG = load_generator_config()["products"]
PRODUCT_REFERENCE = load_products()["products"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def generate_product_id() -> str:
    """
    Generate a unique product identifier.
    """

    characters = (
        "abcdefghijklmnopqrstuvwxyz"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "0123456789"
    )

    suffix = "".join(
        random.choices(
            characters,
            k=24,
        )
    )

    return f"prod_{suffix}"


def select_product_count(size_segment: str) -> int:
    """
    Select the number of products for a merchant
    based on its size segment.
    """

    configuration = PRODUCT_CONFIG[
        "products_per_merchant"
    ][size_segment]

    return random.randint(
        configuration["min"],
        configuration["max"],
    )


def select_product_category(
    merchant_category: str,
) -> str:
    """
    Select a valid product category for a merchant
    based on the merchant's business category.
    """

    allowed_categories = (
        PRODUCT_CONFIG[
            "merchant_category_mapping"
        ][merchant_category][
            "allowed_categories"
        ]
    )

    return random.choice(
        allowed_categories
    )


def select_product_name(
    product_category: str,
    used_names: set[str],
) -> str:
    """
    Select a unique product name for a merchant.
    """

    available_names = [
        name
        for name in PRODUCT_REFERENCE[
            product_category
        ]
        if name not in used_names
    ]

    if not available_names:
        raise ValueError(
            f"No unused products remain for "
            f"category: {product_category}"
        )

    return random.choice(
        available_names
    )


def generate_base_price(
    product_category: str,
) -> Decimal:
    """
    Generate a product price within the configured
    category-specific range.
    """

    configuration = PRODUCT_CONFIG[
        "price_ranges"
    ][product_category]

    minimum = Decimal(
        str(configuration["min"])
    )

    maximum = Decimal(
        str(configuration["max"])
    )

    price = Decimal(
        str(
            random.uniform(
                float(minimum),
                float(maximum),
            )
        )
    )

    return price.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


def generate_probability(
    configuration_name: str,
    product_category: str,
) -> Decimal:
    """
    Generate a probability within the configured
    category-specific range.
    """

    configuration = PRODUCT_CONFIG[
        configuration_name
    ][product_category]

    minimum = float(
        configuration["min"]
    )

    maximum = float(
        configuration["max"]
    )

    probability = random.uniform(
        minimum,
        maximum,
    )

    return Decimal(
        str(probability)
    ).quantize(
        Decimal("0.0001"),
        rounding=ROUND_HALF_UP,
    )


def select_refundable(
    product_category: str,
) -> bool:
    """
    Determine whether a product is refundable.

    Digital goods and subscriptions are treated as
    non-refundable by default. Physical goods are
    refundable.
    """

    non_refundable_categories = {
        "DIGITAL_GOODS",
        "SUBSCRIPTION",
    }

    return (
        product_category
        not in non_refundable_categories
    )


def select_product_status() -> str:
    """
    Select product status using configured weights.
    """

    distribution = PRODUCT_CONFIG[
        "status_distribution"
    ]

    statuses = list(
        distribution.keys()
    )

    weights = [
        distribution[status]["weight"]
        for status in statuses
    ]

    return random.choices(
        statuses,
        weights=weights,
        k=1,
    )[0]


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def generate_products() -> list[dict]:
    """
    Generate product master data for all merchants
    currently stored in PostgreSQL.
    """

    merchants = fetch_merchants()

    products = []

    for merchant in merchants:

        merchant_id = merchant["id"]

        merchant_category = (
            merchant["merchant_category"]
        )

        merchant_size = (
            merchant["size_segment"]
        )

        merchant_currency = (
            merchant["default_currency"]
        )

        product_count = select_product_count(
            merchant_size
        )

        used_names = set()

        for _ in range(product_count):

            product_category = (
                select_product_category(
                    merchant_category
                )
            )

            product_name = select_product_name(
                product_category,
                used_names,
            )

            used_names.add(product_name)

            product = {
                "product_id": generate_product_id(),

                "merchant_fk": merchant_id,

                "product_name": product_name,

                "product_category": (
                    product_category
                ),

                "base_price": generate_base_price(
                    product_category
                ),

                "currency": merchant_currency,

                "refundable": select_refundable(
                    product_category
                ),

                "refund_probability": (
                    generate_probability(
                        "refund_probability",
                        product_category,
                    )
                ),

                "chargeback_probability": (
                    generate_probability(
                        "chargeback_probability",
                        product_category,
                    )
                ),

                "product_status": (
                    select_product_status()
                ),
            }

            products.append(product)

    return products