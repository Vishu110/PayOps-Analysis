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

from simulator.transactions.generator import (
    TransactionGenerator,
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

    transaction_config = dict(
        config["transactions"]
    )

    transaction_config[
        "_simulation_current_date"
    ] = config[
        "simulation"
    ]["current_date"]

    generator = TransactionGenerator(
        selector=selector,
        transaction_config=transaction_config,
        rng=random.Random(20260818),
    )

    sample_size = 100

    transactions = [
        generator.generate_one()
        for _ in range(sample_size)
    ]

    # --------------------------------------------------------------
    # Basic validation
    # --------------------------------------------------------------

    if len(transactions) != sample_size:
        raise AssertionError(
            "Incorrect number of transactions generated."
        )

    transaction_ids = {
        transaction["transaction_id"]
        for transaction in transactions
    }

    if len(transaction_ids) != sample_size:
        raise AssertionError(
            "Duplicate transaction IDs generated."
        )

    # --------------------------------------------------------------
    # Field validation
    # --------------------------------------------------------------

    required_fields = {
        "transaction_id",
        "customer_fk",
        "merchant_fk",
        "product_fk",
        "payment_method_fk",
        "transaction_type",
        "amount",
        "currency",
        "quantity",
        "current_status",
        "initiated_at",
    }

    for transaction in transactions:

        missing_fields = (
            required_fields
            - transaction.keys()
        )

        if missing_fields:
            raise AssertionError(
                f"Missing transaction fields: "
                f"{missing_fields}"
            )

        if transaction[
            "transaction_type"
        ] != "PAYMENT":
            raise AssertionError(
                "Unexpected transaction type."
            )

        if transaction[
            "current_status"
        ] != "PENDING":
            raise AssertionError(
                "New transactions must begin "
                "in PENDING status."
            )

        if transaction[
            "amount"
        ] <= 0:
            raise AssertionError(
                "Transaction amount must be positive."
            )

        if transaction[
            "quantity"
        ] < 1:
            raise AssertionError(
                "Transaction quantity must be "
                "at least 1."
            )

        if transaction[
            "initiated_at"
        ].tzinfo is None:
            raise AssertionError(
                "Transaction timestamp must be "
                "timezone-aware."
            )

    # --------------------------------------------------------------
    # Display sample
    # --------------------------------------------------------------

    print(
        f"Generated transactions: "
        f"{len(transactions):,}"
    )

    print()
    print("First 5 transactions:")

    for transaction in transactions[:5]:

        print(transaction)

    # --------------------------------------------------------------
    # Final validation
    # --------------------------------------------------------------

    print()
    print(
        "All transaction generator "
        "validation tests passed."
    )


if __name__ == "__main__":
    main()