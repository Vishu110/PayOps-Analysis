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

from simulator.transactions.database_rows import (
    TransactionDatabaseRowBuilder,
)

import random


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

    builder = (
        TransactionDatabaseRowBuilder()
    )

    payments = simulator.generate_many(
        100
    )

    for payment in payments:

        # Simulate PostgreSQL generated transaction.id
        transaction_db_id = random.randint(
            1,
            10_000_000,
        )

        transaction_row = (
            builder.build_transaction_row(
                payment
            )
        )

        attempt_rows = (
            builder.build_attempt_rows(
                payment,
                transaction_db_id,
            )
        )

        attempt_db_ids = [
            random.randint(
                1,
                10_000_000,
            )
            for _ in attempt_rows
        ]

        event_rows = (
            builder.build_event_rows(
                payment,
                attempt_db_ids,
            )
        )

        # ----------------------------------------------------------
        # Transaction validation
        # ----------------------------------------------------------

        if not transaction_row[
            "transaction_id"
        ]:
            raise AssertionError(
                "Missing transaction_id."
            )

        if transaction_row[
            "transaction_type"
        ] != "PAYMENT":

            raise AssertionError(
                "Unexpected transaction type."
            )

        if transaction_row[
            "current_status"
        ] not in {
            "CAPTURED",
            "FAILED",
            "CANCELED",
        }:

            raise AssertionError(
                "Invalid final transaction status."
            )

        if transaction_row[
            "completed_at"
        ] < transaction_row[
            "initiated_at"
        ]:

            raise AssertionError(
                "Transaction completed before "
                "it was initiated."
            )

        # ----------------------------------------------------------
        # Attempt validation
        # ----------------------------------------------------------

        if len(attempt_rows) < 1:
            raise AssertionError(
                "Transaction has no payment attempts."
            )

        for attempt in attempt_rows:

            if attempt[
                "transaction_fk"
            ] != transaction_db_id:

                raise AssertionError(
                    "Attempt references the "
                    "wrong transaction."
                )

            if attempt[
                "attempt_status"
            ] == "FAILED":

                if not attempt[
                    "failure_reason"
                ]:

                    raise AssertionError(
                        "Failed attempt is missing "
                        "failure reason."
                    )

            else:

                if attempt[
                    "failure_reason"
                ] is not None:

                    raise AssertionError(
                        "Non-failed attempt has "
                        "a failure reason."
                    )

        # ----------------------------------------------------------
        # Event validation
        # ----------------------------------------------------------

        expected_event_count = sum(
            len(
                attempt["events"]
            )
            for attempt in payment[
                "attempts"
            ]
        )

        if len(event_rows) != (
            expected_event_count
        ):

            raise AssertionError(
                "Incorrect number of event rows."
            )

        for event in event_rows:

            if event[
                "payment_attempt_fk"
            ] not in attempt_db_ids:

                raise AssertionError(
                    "Event references an "
                    "unknown attempt."
                )

            if event[
                "sequence_number"
            ] < 1:

                raise AssertionError(
                    "Invalid event sequence."
                )

    print(
        "Generated payments: 100"
    )

    print(
        "Transaction row validation passed."
    )

    print(
        "Payment attempt row validation passed."
    )

    print(
        "Payment event row validation passed."
    )

    print()
    print(
        "All transaction database row "
        "validation tests passed."
    )


if __name__ == "__main__":
    main()