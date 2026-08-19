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


def build_simulator(seed):

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
        rng=random.Random(seed),
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
            rng=random.Random(seed + 1),
        )
    )

    lifecycle_engine = (
        TransactionLifecycle(
            lifecycle_config=config[
                "transactions"
            ]["lifecycle"],
            rng=random.Random(seed + 2),
        )
    )

    attempt_engine = PaymentAttemptEngine(
        resolver=resolver,
        lifecycle_engine=lifecycle_engine,
        attempts_config=config[
            "transactions"
        ]["attempts"],
        rng=random.Random(seed + 3),
    )

    return PaymentSimulator(
        transaction_generator=(
            transaction_generator
        ),
        attempt_engine=attempt_engine,
    )


def main():

    simulator = build_simulator(
        20260820
    )

    found = {
        "captured_single": None,
        "captured_retry": None,
        "failed": None,
        "canceled": None,
    }

    max_payments = 10_000

    for _ in range(max_payments):

        payment = simulator.generate_one()

        status = payment[
            "final_status"
        ]

        attempts = payment[
            "attempts"
        ]

        if (
            status == "CAPTURED"
            and len(attempts) == 1
            and found[
                "captured_single"
            ] is None
        ):
            found[
                "captured_single"
            ] = payment

        if (
            status == "CAPTURED"
            and len(attempts) > 1
            and found[
                "captured_retry"
            ] is None
        ):
            found[
                "captured_retry"
            ] = payment

        if (
            status == "FAILED"
            and found[
                "failed"
            ] is None
        ):
            found[
                "failed"
            ] = payment

        if (
            status == "CANCELED"
            and found[
                "canceled"
            ] is None
        ):
            found[
                "canceled"
            ] = payment

        if all(
            value is not None
            for value in found.values()
        ):
            break

    missing = [
        name
        for name, value in found.items()
        if value is None
    ]

    if missing:
        raise AssertionError(
            "Could not generate required scenarios: "
            + ", ".join(missing)
        )

    # --------------------------------------------------------------
    # Validate each scenario
    # --------------------------------------------------------------

    for name, payment in found.items():

        transaction = payment[
            "transaction"
        ]

        attempts = payment[
            "attempts"
        ]

        print()
        print(
            f"Scenario: {name}"
        )

        print(
            f"Transaction: "
            f"{transaction['transaction_id']}"
        )

        print(
            f"Final status: "
            f"{payment['final_status']}"
        )

        print(
            f"Attempts: "
            f"{len(attempts)}"
        )

        for attempt in attempts:

            print(
                f"  Attempt "
                f"{attempt['attempt_number']}: "
                f"{attempt['attempt_status']}"
            )

            if attempt[
                "failure_reason"
            ]:

                print(
                    f"    Failure reason: "
                    f"{attempt['failure_reason']}"
                )

            print(
                f"    Events: "
                f"{len(attempt['events'])}"
            )

    # --------------------------------------------------------------
    # Retry chronology validation
    # --------------------------------------------------------------

    retry_payment = found[
        "captured_retry"
    ]

    retry_attempts = retry_payment[
        "attempts"
    ]

    if len(retry_attempts) < 2:
        raise AssertionError(
            "Retry scenario does not contain "
            "multiple attempts."
        )

    for previous, current in zip(
        retry_attempts,
        retry_attempts[1:],
    ):

        if current[
            "initiated_at"
        ] <= previous[
            "completed_at"
        ]:

            raise AssertionError(
                "Retry attempt does not start "
                "after the previous attempt "
                "completed."
            )

    # --------------------------------------------------------------
    # Failed transaction validation
    # --------------------------------------------------------------

    failed_payment = found[
        "failed"
    ]

    if failed_payment[
        "final_status"
    ] != "FAILED":

        raise AssertionError(
            "Failed scenario has incorrect "
            "final status."
        )

    # --------------------------------------------------------------
    # Canceled transaction validation
    # --------------------------------------------------------------

    canceled_payment = found[
        "canceled"
    ]

    if canceled_payment[
        "final_status"
    ] != "CANCELED":

        raise AssertionError(
            "Canceled scenario has incorrect "
            "final status."
        )

    print()
    print(
        "All required transaction scenarios "
        "were generated successfully."
    )


if __name__ == "__main__":
    main()