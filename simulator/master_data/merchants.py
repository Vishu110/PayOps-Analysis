import random
from datetime import date, timedelta
from decimal import Decimal

from simulator.utils.config_loader import (
    load_generator_config,
    load_merchants,
)
from simulator.utils.id_generator import generate_id

from database.loaders.processors import fetch_processors

from simulator.utils.config_loader import (
    load_countries,
    load_generator_config,
    load_merchants,
)


MERCHANT_CONFIG = load_merchants()
GENERATOR_CONFIG = load_generator_config()
COUNTRIES_CONFIG = load_countries()
COUNTRIES = COUNTRIES_CONFIG["countries"]


def get_eligible_processors(
    country_code: str,
    processors: list[dict],
) -> list[dict]:
    """
    Return processors that support the merchant's country.
    """

    eligible_processors = []

    for processor in processors:

        if country_code in processor["supported_regions"]:
            eligible_processors.append(processor)

    if not eligible_processors:
        raise ValueError(
            f"No eligible processor found "
            f"for country '{country_code}'."
        )

    return eligible_processors


def select_preferred_processor(
    processors: list[dict],
) -> dict:
    """
    Select an eligible processor using the configured
    processor preference weights.
    """

    preference_config = GENERATOR_CONFIG[
        "merchants"
    ]["processor_preference"]

    eligible_processors = []
    weights = []

    for processor in processors:

        processor_name = processor["processor_name"]

        preference = preference_config.get(
            processor_name
        )

        if preference is None:
            raise ValueError(
                f"No processor preference configured "
                f"for '{processor_name}'."
            )

        eligible_processors.append(processor)
        weights.append(preference["weight"])

    return random.choices(
        eligible_processors,
        weights=weights,
        k=1,
    )[0]


def select_merchant_category(
    categories: list[str],
) -> str:
    """
    Select a merchant category using the global category
    distribution while restricting the selection to the
    categories supported by the reference merchant.
    """

    category_distribution = GENERATOR_CONFIG[
        "merchants"
    ]["category_distribution"]

    eligible_categories = []
    weights = []

    for category in categories:

        configuration = category_distribution.get(
            category
        )

        if configuration is None:
            raise ValueError(
                f"No category distribution configured "
                f"for '{category}'."
            )

        eligible_categories.append(category)

        weights.append(
            configuration["weight"]
        )

    return random.choices(
        eligible_categories,
        weights=weights,
        k=1,
    )[0]


def weighted_choice(
    distribution: dict,
):
    """
    Select one value from a configuration distribution
    using its configured weights.

    Example:

        LOW: 80.0
        MEDIUM: 15.0
        HIGH: 5.0
    """

    values = []
    weights = []

    for value, configuration in distribution.items():

        values.append(value)
        weights.append(configuration["weight"])

    return random.choices(
        values,
        weights=weights,
        k=1,
    )[0]


def generate_settlement_cycle() -> int:
    """
    Generate merchant settlement cycle from the
    configured distribution.
    """

    distribution = GENERATOR_CONFIG[
        "merchants"
    ]["settlement_cycle_distribution"]

    return int(
        weighted_choice(distribution)
    )


def generate_risk_segment() -> str:
    """
    Generate merchant risk segment.
    """

    distribution = GENERATOR_CONFIG[
        "merchants"
    ]["risk_distribution"]

    return weighted_choice(distribution)


def generate_merchant_status() -> str:
    """
    Generate merchant operational status.
    """

    distribution = GENERATOR_CONFIG[
        "merchants"
    ]["status_distribution"]

    return weighted_choice(distribution)


def calculate_processing_fee(
    processor_fee: Decimal,
    risk_segment: str,
    merchant_category: str,
) -> Decimal:
    """
    Calculate merchant processing fee from the processor
    baseline plus controlled business adjustments.

    Decimal is used because processing fees are financial
    values and PostgreSQL NUMERIC values are returned as Decimal.
    """

    risk_adjustments = {
        "LOW": Decimal("0.00"),
        "MEDIUM": Decimal("0.15"),
        "HIGH": Decimal("0.40"),
    }

    category_adjustments = {
        "ECOMMERCE": Decimal("0.00"),
        "SAAS": Decimal("-0.05"),
        "MARKETPLACE": Decimal("0.15"),
        "DIGITAL_GOODS": Decimal("0.20"),
    }

    adjustment = (
        risk_adjustments[risk_segment]
        + category_adjustments[merchant_category]
    )

    fee = processor_fee + adjustment

    fee = max(
        Decimal("0.00"),
        min(fee, Decimal("100.00")),
    )

    return fee.quantize(
        Decimal("0.01")
    )


def generate_onboarded_date() -> date:
    """
    Generate a synthetic merchant onboarding date
    within the project's historical simulation window.
    """

    start_date = date(2021, 1, 1)
    end_date = date(2026, 6, 30)

    days = (
        end_date - start_date
    ).days

    random_days = random.randint(
        0,
        days,
    )

    return start_date + timedelta(
        days=random_days
    )



def generate_merchants() -> list[dict]:
    """
    Generate the complete merchant master dataset.
    """

    processors = fetch_processors()

    if not processors:
        raise ValueError(
            "No processors available in PostgreSQL."
        )

    merchants = []

    merchants_by_country = (
        MERCHANT_CONFIG["merchants"]
    )

    for country_code, merchant_list in (
        merchants_by_country.items()
    ):

        for merchant_reference in merchant_list:

            merchant_category = (
                select_merchant_category(
                    merchant_reference["categories"]
                )
            )

            risk_segment = (
                generate_risk_segment()
            )

            merchant_status = (
                generate_merchant_status()
            )

            settlement_cycle = (
                generate_settlement_cycle()
            )

            eligible_processors = (
                get_eligible_processors(
                    country_code=country_code,
                    processors=processors,
                )
            )

            preferred_processor = (
                select_preferred_processor(
                    eligible_processors
                )
            )

            processing_fee = (
                calculate_processing_fee(
                    processor_fee=(
                        preferred_processor[
                            "default_processing_fee_percentage"
                        ]
                    ),
                    risk_segment=risk_segment,
                    merchant_category=(
                        merchant_category
                    ),
                )
            )

            merchant = {
                "merchant_key": merchant_reference["merchant_key"],
                
                "merchant_id": generate_id("mer"),

                "merchant_name": (
                    merchant_reference[
                        "merchant_name"
                    ]
                ),

                "legal_name": (
                    merchant_reference[
                        "legal_name"
                    ]
                ),

                "merchant_category": (
                    merchant_category
                ),

                "size_segment": (
                    merchant_reference["size_segment"]
                ),

                "country_code": country_code,

                "country_name": COUNTRIES[
                    country_code
                ]["name"],

                "default_currency": COUNTRIES[
                    country_code
                ]["currency"],

                "preferred_processor_fk": (
                    preferred_processor["id"]
                ),

                "settlement_cycle": (
                    settlement_cycle
                ),

                "default_processing_fee_percentage": (
                    processing_fee
                ),

                "risk_segment": risk_segment,

                "merchant_status": merchant_status,

                "onboarded_date": (
                    generate_onboarded_date()
                ),
            }

            merchants.append(merchant)

    return merchants