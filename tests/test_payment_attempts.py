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

    # --------------------------------------------------------------
    # Generate sample transactions
    # --------------------------------------------------------------

    sample_size = 500

    generated_payments = []

    for _ in range(sample_size):

        generated_payment = (
            transaction_generator.generate_one()
        )

        generated_payments.append(
            generated_payment
        )

    # --------------------------------------------------------------
    # Generate payment attempts
    # --------------------------------------------------------------

    total_attempts = 0
    retry_transactions = 0
    captured_transactions = 0
    failed_transactions = 0
    canceled_transactions = 0

    for generated_payment in generated_payments:

        transaction = generated_payment[
            "transaction"
        ]

        context = generated_payment[
            "context"
        ]

        result = (
            attempt_engine.generate(
                transaction,
                context,
            )
        )

        attempts = result[
            "attempts"
        ]

        total_attempts += len(
            attempts
        )

        if len(attempts) > 1:
            retry_transactions += 1

        if result[
            "final_status"
        ] == "CAPTURED":
            captured_transactions += 1

        elif result[
            "final_status"
        ] == "FAILED":
            failed_transactions += 1

        elif result[
            "final_status"
        ] == "CANCELED":
            canceled_transactions += 1

        # ----------------------------------------------------------
        # Attempt-level validation
        # ----------------------------------------------------------

        previous_completed_at = (
            transaction["initiated_at"]
        )

        for index, attempt in enumerate(
            attempts,
            start=1,
        ):

            if (
                attempt[
                    "attempt_number"
                ]
                != index
            ):
                raise AssertionError(
                    "Attempt numbers are not "
                    "continuous."
                )

            if (
                attempt[
                    "initiated_at"
                ]
                < previous_completed_at
            ):
                raise AssertionError(
                    "Attempt chronology is invalid."
                )

            if (
                attempt[
                    "completed_at"
                ]
                < attempt[
                    "initiated_at"
                ]
            ):
                raise AssertionError(
                    "Attempt completed before "
                    "it was initiated."
                )

            # ------------------------------------------------------
            # Processor validation
            # ------------------------------------------------------

            processor = attempt[
                "processor"
            ]

            if (
                context["merchant"]["country_code"]
                not in processor[
                    "supported_regions"
                ]
            ):
                raise AssertionError(
                    "Processor does not support "
                    "merchant country."
                )

            if (
                context["payment_method"]["card_network"]
                not in processor[
                    "supported_card_networks"
                ]
            ):
                raise AssertionError(
                    "Processor does not support "
                    "card network."
                )

            # ------------------------------------------------------
            # Event validation
            # ------------------------------------------------------

            events = attempt[
                "events"
            ]

            if not events:
                raise AssertionError(
                    "Attempt contains no events."
                )

            if (
                events[0]["event_at"]
                != attempt[
                    "initiated_at"
                ]
            ):
                raise AssertionError(
                    "First event must equal "
                    "attempt initiation."
                )

            if (
                events[-1]["event_at"]
                != attempt[
                    "completed_at"
                ]
            ):
                raise AssertionError(
                    "Last event must equal "
                    "attempt completion."
                )

            previous_event_at = (
                events[0]["event_at"]
            )

            for event in events[1:]:

                if (
                    event["event_at"]
                    <= previous_event_at
                ):
                    raise AssertionError(
                        "Events are not "
                        "chronological."
                    )

                previous_event_at = (
                    event["event_at"]
                )

            previous_completed_at = (
                attempt["completed_at"]
            )

        # ----------------------------------------------------------
        # Final transaction chronology
        # ----------------------------------------------------------

        if (
            result["completed_at"]
            < transaction["initiated_at"]
        ):
            raise AssertionError(
                "Transaction completed before "
                "it was initiated."
            )

    # --------------------------------------------------------------
    # Summary
    # --------------------------------------------------------------

    print(
        f"Transactions tested: "
        f"{sample_size:,}"
    )

    print(
        f"Total payment attempts: "
        f"{total_attempts:,}"
    )

    print(
        f"Transactions requiring retry: "
        f"{retry_transactions:,}"
    )

    print(
        f"Captured: "
        f"{captured_transactions:,}"
    )

    print(
        f"Failed: "
        f"{failed_transactions:,}"
    )

    print(
        f"Canceled: "
        f"{canceled_transactions:,}"
    )

    print()

    print(
        "All payment attempt validation "
        "tests passed."
    )


if __name__ == "__main__":
    main()