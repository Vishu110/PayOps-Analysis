import random

from database.loaders.transaction_dependencies import (
    fetch_transaction_dependencies,
)

from simulator.transactions.dependencies import (
    TransactionDependencyResolver,
)

from simulator.transactions.selector import (
    TransactionSelector,
)

from simulator.utils.config_loader import (
    load_generator_config,
)


def main():

    config = load_generator_config()

    dependencies = (
        fetch_transaction_dependencies()
    )

    resolver = (
        TransactionDependencyResolver(
            dependencies
        )
    )

    selector = TransactionSelector(
        resolver=resolver,
        geography_config=config[
            "transactions"
        ]["geography"],
        rng=random.Random(20260818),
    )

    sample_size = 1000

    domestic_count = 0
    cross_border_count = 0

    for _ in range(sample_size):

        context = selector.select()

        customer = context["customer"]
        merchant = context["merchant"]
        product = context["product"]
        payment_method = context[
            "payment_method"
        ]
        processors = context[
            "eligible_processors"
        ]

        # ----------------------------------------------------------
        # Customer → payment method
        # ----------------------------------------------------------

        if (
            payment_method["customer_fk"]
            != customer["id"]
        ):
            raise AssertionError(
                "Payment method does not belong "
                "to selected customer."
            )

        # ----------------------------------------------------------
        # Merchant → product
        # ----------------------------------------------------------

        if (
            product["merchant_fk"]
            != merchant["id"]
        ):
            raise AssertionError(
                "Product does not belong "
                "to selected merchant."
            )

        # ----------------------------------------------------------
        # Currency
        # ----------------------------------------------------------

        if (
            product["currency"]
            != merchant["default_currency"]
        ):
            raise AssertionError(
                "Product and merchant currencies "
                "do not match."
            )

        # ----------------------------------------------------------
        # Geography
        # ----------------------------------------------------------

        expected_cross_border = (
            customer["country_code"]
            != merchant["country_code"]
        )

        if (
            context["is_cross_border"]
            != expected_cross_border
        ):
            raise AssertionError(
                "Cross-border flag is inconsistent "
                "with customer and merchant countries."
            )

        if context["is_cross_border"]:
            cross_border_count += 1
        else:
            domestic_count += 1

        # ----------------------------------------------------------
        # Processor eligibility
        # ----------------------------------------------------------

        for processor in processors:

            if (
                merchant["country_code"]
                not in processor[
                    "supported_regions"
                ]
            ):
                raise AssertionError(
                    "Processor does not support "
                    "merchant country."
                )

            if (
                payment_method["card_network"]
                not in processor[
                    "supported_card_networks"
                ]
            ):
                raise AssertionError(
                    "Processor does not support "
                    "payment method card network."
                )

    # --------------------------------------------------------------
    # Distribution
    # --------------------------------------------------------------

    domestic_percentage = (
        domestic_count
        / sample_size
        * 100
    )

    cross_border_percentage = (
        cross_border_count
        / sample_size
        * 100
    )

    print(
        f"Generated contexts: {sample_size:,}"
    )

    print(
        f"Domestic: "
        f"{domestic_count:,} "
        f"({domestic_percentage:.2f}%)"
    )

    print(
        f"Cross-border: "
        f"{cross_border_count:,} "
        f"({cross_border_percentage:.2f}%)"
    )

    print()

    print(
        "All transaction selector "
        "validation tests passed."
    )


if __name__ == "__main__":
    main()