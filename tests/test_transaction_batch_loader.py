import random

from database.loaders.transaction_dependencies import (
    fetch_transaction_dependencies,
)

from database.loaders.transactions import (
    TransactionLoader,
)

from simulator.utils.config_loader import (
    load_generator_config,
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

from simulator.transactions.lifecycle import (
    TransactionLifecycle,
)

from simulator.transactions.attempts import (
    PaymentAttemptEngine,
)

from simulator.transactions.payment_simulator import (
    PaymentSimulator,
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
        rng=random.Random(20260820),
    )

    transaction_config = dict(
        config["transactions"]
    )

    transaction_config[
        "_simulation_current_date"
    ] = config[
        "simulation"
    ]["current_date"]

    transaction_generator = (
        TransactionGenerator(
            selector=selector,
            transaction_config=transaction_config,
            rng=random.Random(20260820),
        )
    )

    lifecycle_engine = (
        TransactionLifecycle(
            lifecycle_config=config[
                "transactions"
            ]["lifecycle"],
            rng=random.Random(20260820),
        )
    )

    attempt_engine = PaymentAttemptEngine(
        resolver=resolver,
        lifecycle_engine=lifecycle_engine,
        attempts_config=config[
            "transactions"
        ]["attempts"],
        rng=random.Random(20260820),
    )

    simulator = PaymentSimulator(
        transaction_generator=(
            transaction_generator
        ),
        attempt_engine=attempt_engine,
    )

    loader = TransactionLoader()

    # --------------------------------------------------------------
    # Generate controlled batch
    # --------------------------------------------------------------

    batch_size = 1_000

    payments = simulator.generate_many(
        batch_size
    )

    if len(payments) != batch_size:
        raise AssertionError(
            "Incorrect number of payments generated."
        )

    # --------------------------------------------------------------
    # Validate transaction IDs before touching DB
    # --------------------------------------------------------------

    transaction_ids = [
        payment["transaction"][
            "transaction_id"
        ]
        for payment in payments
    ]

    if len(transaction_ids) != len(
        set(transaction_ids)
    ):
        raise AssertionError(
            "Duplicate transaction IDs detected "
            "before database insertion."
        )

    # --------------------------------------------------------------
    # Load batch
    # --------------------------------------------------------------

    result = loader.load_batch(
        payments
    )

    # --------------------------------------------------------------
    # Validate returned counts
    # --------------------------------------------------------------

    if result[
        "transactions"
    ] != batch_size:

        raise AssertionError(
            "Database transaction count does "
            "not match generated batch size."
        )

    if result[
        "attempts"
    ] < batch_size:

        raise AssertionError(
            "Attempt count cannot be lower "
            "than transaction count."
        )

    if result[
        "events"
    ] < result[
        "attempts"
    ]:

        raise AssertionError(
            "Event count cannot be lower "
            "than attempt count."
        )

    if (
        result["captured"]
        + result["failed"]
        + result["canceled"]
        != batch_size
    ):

        raise AssertionError(
            "Terminal outcome counts do not "
            "sum to transaction count."
        )

    # --------------------------------------------------------------
    # Summary
    # --------------------------------------------------------------

    print(
        f"Generated transactions: "
        f"{batch_size:,}"
    )

    print(
        f"Inserted transactions: "
        f"{result['transactions']:,}"
    )

    print(
        f"Inserted payment attempts: "
        f"{result['attempts']:,}"
    )

    print(
        f"Inserted payment events: "
        f"{result['events']:,}"
    )

    print()

    print(
        f"Captured: "
        f"{result['captured']:,}"
    )

    print(
        f"Failed: "
        f"{result['failed']:,}"
    )

    print(
        f"Canceled: "
        f"{result['canceled']:,}"
    )

    print(
        f"Transactions with retries: "
        f"{result['retried']:,}"
    )

    print(
        f"Cross-border transactions: "
        f"{result['cross_border']:,}"
    )

    print()
    print(
        "Transaction batch loader test passed."
    )


if __name__ == "__main__":
    main()