import random
from datetime import date

from simulator.transactions.volume import (
    TransactionVolumeGenerator,
)

from simulator.transactions.daily_simulator import (
    DailyTransactionSimulator,
)

from simulator.transactions.generator import (
    TransactionGenerator,
)

from simulator.transactions.dependencies import (
    TransactionDependencyResolver,
)

from simulator.transactions.selector import (
    TransactionSelector,
)

from simulator.transactions.lifecycle import (
    TransactionLifecycle,
)

from simulator.transactions.attempts import (
    PaymentAttemptEngine,
)

from simulator.utils.config_loader import (
    load_generator_config,
)

from database.loaders.transaction_dependencies import (
    fetch_transaction_dependencies,
)


class TestCappedVolumeGenerator:
    """
    Test-only wrapper around the real transaction volume generator.

    The real volume model still calculates realistic daily volume,
    but the integration test caps the number of complete payment
    journeys generated so the test remains fast.
    """

    def __init__(
        self,
        volume_generator,
        max_volume=100,
    ):
        self.volume_generator = volume_generator
        self.max_volume = max_volume

    def generate_daily_volume(
        self,
        transaction_date,
    ):
        real_volume = (
            self.volume_generator.generate_daily_volume(
                transaction_date
            )
        )

        return min(
            real_volume,
            self.max_volume,
        )


def main():

    # --------------------------------------------------------------
    # Configuration
    # --------------------------------------------------------------

    config = load_generator_config()

    transactions_config = dict(
        config["transactions"]
    )

    transactions_config[
        "_simulation_current_date"
    ] = config[
        "simulation"
    ]["current_date"]

    transactions_config[
        "_historical_start_date"
    ] = config[
        "simulation"
    ]["historical_start_date"]

    volume_config = dict(
        config["simulation"]["volume"]
    )

    volume_config[
        "_historical_start_date"
    ] = config[
        "simulation"
    ]["historical_start_date"]

    volume_generator = TransactionVolumeGenerator(
        volume_config=volume_config,
        rng=random.Random(
            volume_config["random_seed"]
        )
    )

    # --------------------------------------------------------------
    # Dependencies
    # --------------------------------------------------------------

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
        rng=random.Random(20260823),
    )

    # --------------------------------------------------------------
    # Transaction generator
    # --------------------------------------------------------------

    transaction_generator = (
        TransactionGenerator(
            selector=selector,
            transaction_config=transactions_config,
            rng=random.Random(20260823),
        )
    )

    # --------------------------------------------------------------
    # Lifecycle engine
    # --------------------------------------------------------------

    lifecycle_engine = (
        TransactionLifecycle(
            lifecycle_config=
                transactions_config[
                    "lifecycle"
                ],
            rng=random.Random(20260823),
        )
    )

    # --------------------------------------------------------------
    # Payment attempt engine
    # --------------------------------------------------------------

    attempt_engine = (
        PaymentAttemptEngine(
            resolver=resolver,
            lifecycle_engine=lifecycle_engine,
            attempts_config=
                transactions_config[
                    "attempts"
                ],
            rng=random.Random(20260823),
        )
    )

    # --------------------------------------------------------------
    # Complete payment simulator
    # --------------------------------------------------------------

    from simulator.transactions.payment_simulator import (
        PaymentSimulator,
    )

    payment_simulator = PaymentSimulator(
        transaction_generator=
            transaction_generator,
        attempt_engine=
            attempt_engine,
    )

    # --------------------------------------------------------------
    # Volume generator
    # --------------------------------------------------------------

    volume_generator = (
        TransactionVolumeGenerator(
            volume_config=volume_config,
            rng=random.Random(20260823),
        )
    )

    # --------------------------------------------------------------
    # Daily simulator
    # --------------------------------------------------------------

    simulator = (
        DailyTransactionSimulator(
            volume_generator=
                volume_generator,
            payment_simulator=
                payment_simulator,
        )
    )

    # --------------------------------------------------------------
    # Test dates
    # --------------------------------------------------------------

    start_date = date(
        2026,
        8,
        10,
    )

    end_date = date(
        2026,
        8,
        12,
    )

    # --------------------------------------------------------------
    # Generate day by day
    # --------------------------------------------------------------

    total_transactions = 0
    seen_transaction_ids = set()

    daily_counts = []

    for transaction_date, payments in (
        simulator.generate_range(
            start_date,
            end_date,
        )
    ):

        print(
            f"{transaction_date}: "
            f"{len(payments):,} transactions"
        )

        daily_counts.append(
            (
                transaction_date,
                len(payments),
            )
        )

        if not payments:
            raise AssertionError(
                f"No payments generated for "
                f"{transaction_date}."
            )

        # ----------------------------------------------------------
        # Validate every payment in the day
        # ----------------------------------------------------------

        for payment in payments:

            transaction = payment[
                "transaction"
            ]

            transaction_id = transaction[
                "transaction_id"
            ]

            # Unique transaction ID
            if transaction_id in (
                seen_transaction_ids
            ):
                raise AssertionError(
                    f"Duplicate transaction ID: "
                    f"{transaction_id}"
                )

            seen_transaction_ids.add(
                transaction_id
            )

            # Transaction date must match
            # requested simulation date
            initiated_at = transaction[
                "initiated_at"
            ]

            if initiated_at.date() != (
                transaction_date
            ):
                raise AssertionError(
                    "Transaction timestamp date "
                    "does not match simulation date."
                )

            # Timestamp must be timezone-aware
            if initiated_at.tzinfo is None:
                raise AssertionError(
                    "Transaction timestamp "
                    "is not timezone-aware."
                )

            # Final status must agree with simulator
            if transaction[
                "current_status"
            ] != payment[
                "final_status"
            ]:
                raise AssertionError(
                    "Transaction status does not "
                    "match payment final status."
                )

            # Completed timestamp must exist
            if transaction[
                "completed_at"
            ] is None:
                raise AssertionError(
                    "Completed timestamp is missing."
                )

            # Completed after initiation
            if transaction[
                "completed_at"
            ] < initiated_at:
                raise AssertionError(
                    "Transaction completed before "
                    "it was initiated."
                )

            # At least one payment attempt
            if not payment[
                "attempts"
            ]:
                raise AssertionError(
                    "Transaction has no payment attempts."
                )

            total_transactions += 1

    # --------------------------------------------------------------
    # Validate number of generated days
    # --------------------------------------------------------------

    expected_days = (
        end_date - start_date
    ).days + 1

    if len(daily_counts) != (
        expected_days
    ):
        raise AssertionError(
            "Incorrect number of simulated days."
        )

    # --------------------------------------------------------------
    # Final output
    # --------------------------------------------------------------

    print()
    print(
        f"Simulation days: "
        f"{len(daily_counts)}"
    )

    print(
        f"Total transactions: "
        f"{total_transactions:,}"
    )

    print(
        f"Unique transaction IDs: "
        f"{len(seen_transaction_ids):,}"
    )

    print()
    print(
        "Daily transaction simulator "
        "validation passed."
    )


if __name__ == "__main__":
    main()