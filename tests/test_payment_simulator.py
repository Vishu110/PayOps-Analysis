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

    # --------------------------------------------------------------
    # Generate sample
    # --------------------------------------------------------------

    payments = simulator.generate_many(
        100
    )

    if len(payments) != 100:
        raise AssertionError(
            "Incorrect number of payments generated."
        )

    transaction_ids = set()

    for payment in payments:

        transaction = payment[
            "transaction"
        ]

        context = payment[
            "context"
        ]

        attempts = payment[
            "attempts"
        ]

        # ----------------------------------------------------------
        # Transaction identity
        # ----------------------------------------------------------

        transaction_id = transaction[
            "transaction_id"
        ]

        if transaction_id in transaction_ids:
            raise AssertionError(
                "Duplicate transaction ID generated."
            )

        transaction_ids.add(
            transaction_id
        )

        # ----------------------------------------------------------
        # Context consistency
        # ----------------------------------------------------------

        if (
            transaction["customer_fk"]
            != context["customer"]["id"]
        ):
            raise AssertionError(
                "Transaction customer does not "
                "match selected context."
            )

        if (
            transaction["merchant_fk"]
            != context["merchant"]["id"]
        ):
            raise AssertionError(
                "Transaction merchant does not "
                "match selected context."
            )

        if (
            transaction["product_fk"]
            != context["product"]["id"]
        ):
            raise AssertionError(
                "Transaction product does not "
                "match selected context."
            )

        if (
            transaction["payment_method_fk"]
            != context["payment_method"]["id"]
        ):
            raise AssertionError(
                "Transaction payment method does "
                "not match selected context."
            )

        # ----------------------------------------------------------
        # Transaction final state
        # ----------------------------------------------------------

        if transaction[
            "current_status"
        ] != payment[
            "final_status"
        ]:
            raise AssertionError(
                "Transaction current_status does "
                "not match final payment status."
            )

        if transaction[
            "completed_at"
        ] != payment[
            "completed_at"
        ]:
            raise AssertionError(
                "Transaction completed_at does "
                "not match payment completion."
            )

        if transaction[
            "completed_at"
        ] < transaction[
            "initiated_at"
        ]:
            raise AssertionError(
                "Transaction completed before "
                "it was initiated."
            )

        # ----------------------------------------------------------
        # Attempt validation
        # ----------------------------------------------------------

        if not attempts:
            raise AssertionError(
                "Payment contains no attempts."
            )

        previous_completed_at = (
            transaction["initiated_at"]
        )

        for attempt in attempts:

            if attempt[
                "initiated_at"
            ] < previous_completed_at:

                raise AssertionError(
                    "Attempt started before "
                    "previous attempt completed."
                )

            if attempt[
                "completed_at"
            ] < attempt[
                "initiated_at"
            ]:

                raise AssertionError(
                    "Attempt completed before "
                    "attempt initiation."
                )

            events = attempt[
                "events"
            ]

            if not events:
                raise AssertionError(
                    "Attempt contains no events."
                )

            # First event = attempt initiation
            if events[0][
                "event_at"
            ] != attempt[
                "initiated_at"
            ]:

                raise AssertionError(
                    "First event does not match "
                    "attempt initiation."
                )

            # Last event = attempt completion
            if events[-1][
                "event_at"
            ] != attempt[
                "completed_at"
            ]:

                raise AssertionError(
                    "Last event does not match "
                    "attempt completion."
                )

            previous_event_at = (
                events[0]["event_at"]
            )

            for event in events[1:]:

                if event[
                    "event_at"
                ] <= previous_event_at:

                    raise AssertionError(
                        "Payment events are not "
                        "strictly chronological."
                    )

                previous_event_at = (
                    event["event_at"]
                )

            previous_completed_at = (
                attempt["completed_at"]
            )

        # ----------------------------------------------------------
        # Final attempt must determine transaction outcome
        # ----------------------------------------------------------

        if attempts[-1][
            "attempt_status"
        ] != transaction[
            "current_status"
        ]:

            raise AssertionError(
                "Final attempt status does not "
                "match transaction status."
            )

    print(
        "Generated complete payments: 100"
    )

    print(
        "Transaction → context consistency passed."
    )

    print(
        "Transaction → attempt consistency passed."
    )

    print(
        "Attempt → event consistency passed."
    )

    print(
        "Temporal ordering validation passed."
    )

    print(
        "Final transaction status validation passed."
    )

    print()
    print(
        "All payment simulator integration "
        "tests passed."
    )


if __name__ == "__main__":
    main()