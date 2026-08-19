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


def find_required_scenarios(
    simulator,
    max_payments=10_000,
):

    found = {
        "captured_single": None,
        "captured_retry": None,
        "failed": None,
        "canceled": None,
    }

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
            return found

    missing = [
        name
        for name, value in found.items()
        if value is None
    ]

    raise AssertionError(
        "Could not generate required scenarios: "
        + ", ".join(missing)
    )


def validate_scenario(
    scenario_name,
    payment,
):

    transaction = payment[
        "transaction"
    ]

    attempts = payment[
        "attempts"
    ]

    final_status = payment[
        "final_status"
    ]

    if scenario_name == "captured_single":

        if final_status != "CAPTURED":
            raise AssertionError(
                "captured_single does not "
                "end in CAPTURED."
            )

        if len(attempts) != 1:
            raise AssertionError(
                "captured_single does not "
                "contain exactly one attempt."
            )

    elif scenario_name == "captured_retry":

        if final_status != "CAPTURED":
            raise AssertionError(
                "captured_retry does not "
                "end in CAPTURED."
            )

        if len(attempts) < 2:
            raise AssertionError(
                "captured_retry does not "
                "contain multiple attempts."
            )

        for previous, current in zip(
            attempts,
            attempts[1:],
        ):

            if current[
                "initiated_at"
            ] <= previous[
                "completed_at"
            ]:

                raise AssertionError(
                    "Retry attempt does not "
                    "start after previous "
                    "attempt completed."
                )

    elif scenario_name == "failed":

        if final_status != "FAILED":
            raise AssertionError(
                "Failed scenario does not "
                "end in FAILED."
            )

        if attempts[-1][
            "attempt_status"
        ] != "FAILED":

            raise AssertionError(
                "Final attempt of failed "
                "transaction is not FAILED."
            )

        if not attempts[-1][
            "failure_reason"
        ]:

            raise AssertionError(
                "Failed attempt is missing "
                "failure reason."
            )

    elif scenario_name == "canceled":

        if final_status != "CANCELED":
            raise AssertionError(
                "Canceled scenario does not "
                "end in CANCELED."
            )

        if attempts[-1][
            "attempt_status"
        ] != "CANCELED":

            raise AssertionError(
                "Final attempt of canceled "
                "transaction is not CANCELED."
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


def main():

    # --------------------------------------------------------------
    # Build simulator
    # --------------------------------------------------------------

    simulator = build_simulator(
        20260821
    )

    # --------------------------------------------------------------
    # Generate all four scenarios
    # --------------------------------------------------------------

    found = find_required_scenarios(
        simulator
    )

    # --------------------------------------------------------------
    # Validate before database insertion
    # --------------------------------------------------------------

    for scenario_name, payment in found.items():

        validate_scenario(
            scenario_name,
            payment,
        )

    # --------------------------------------------------------------
    # Load scenarios into PostgreSQL
    # --------------------------------------------------------------

    loader = TransactionLoader()

    results = {}

    for scenario_name, payment in found.items():

        result = loader.load_payment(
            payment
        )

        results[
            scenario_name
        ] = result

        print()
        print(
            f"Loaded scenario: "
            f"{scenario_name}"
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

    # --------------------------------------------------------------
    # Final validation
    # --------------------------------------------------------------

    if len(results) != 4:

        raise AssertionError(
            "Expected four loaded scenarios."
        )

    print()
    print(
        "All four transaction scenarios "
        "were successfully persisted."
    )

    print(
        "Transaction scenario loader test passed."
    )


if __name__ == "__main__":
    main()