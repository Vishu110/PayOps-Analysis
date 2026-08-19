import random

from database.loaders.transaction_dependencies import (
    fetch_transaction_dependencies,
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

from database.loaders.transactions import (
    TransactionLoader,
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
        rng=random.Random(20260819),
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
            rng=random.Random(20260819),
        )
    )

    lifecycle_engine = (
        TransactionLifecycle(
            lifecycle_config=config[
                "transactions"
            ]["lifecycle"],
            rng=random.Random(20260819),
        )
    )

    attempt_engine = PaymentAttemptEngine(
        resolver=resolver,
        lifecycle_engine=lifecycle_engine,
        attempts_config=config[
            "transactions"
        ]["attempts"],
        rng=random.Random(20260819),
    )

    simulator = PaymentSimulator(
        transaction_generator=(
            transaction_generator
        ),
        attempt_engine=attempt_engine,
    )

    loader = TransactionLoader()

    # --------------------------------------------------------------
    # Generate ONE controlled payment
    # --------------------------------------------------------------

    payment = simulator.generate_one()

    transaction = payment[
        "transaction"
    ]

    attempts = payment[
        "attempts"
    ]

    # --------------------------------------------------------------
    # Load
    # --------------------------------------------------------------

    result = loader.load_payment(
        payment
    )

    print(
        "Transaction inserted successfully."
    )

    print(
        f"Transaction ID: "
        f"{result['transaction_id']}"
    )

    print(
        f"Database transaction ID: "
        f"{result['transaction_db_id']}"
    )

    print(
        f"Payment attempts inserted: "
        f"{result['attempt_count']}"
    )

    print(
        f"Payment events inserted: "
        f"{result['event_count']}"
    )

    print()
    print(
        "Transaction loader test passed."
    )


if __name__ == "__main__":
    main()