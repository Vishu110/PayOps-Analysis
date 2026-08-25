import random
from datetime import date
from decimal import Decimal

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

from simulator.transactions.payment_simulator import (
    PaymentSimulator,
)

from simulator.utils.config_loader import (
    load_generator_config,
)

from database.loaders.transaction_dependencies import (
    fetch_transaction_dependencies,
)

from database.loaders.transactions import (
    TransactionLoader,
)


SEED = 20260823


def build_simulator():

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

    # --------------------------------------------------------------
    # Dependencies
    # --------------------------------------------------------------

    dependencies = (
        fetch_transaction_dependencies()
    )

    resolver = TransactionDependencyResolver(
        dependencies
    )

    # --------------------------------------------------------------
    # Selector
    # --------------------------------------------------------------

    selector = TransactionSelector(
        resolver=resolver,
        geography_config=config[
            "transactions"
        ]["geography"],
        rng=random.Random(SEED),
    )

    # --------------------------------------------------------------
    # Transaction generator
    # --------------------------------------------------------------

    transaction_generator = TransactionGenerator(
        selector=selector,
        transaction_config=transactions_config,
        rng=random.Random(SEED),
    )

    # --------------------------------------------------------------
    # Lifecycle
    # --------------------------------------------------------------

    lifecycle_engine = TransactionLifecycle(
        lifecycle_config=
            transactions_config[
                "lifecycle"
            ],
        rng=random.Random(SEED),
    )

    # --------------------------------------------------------------
    # Payment attempts
    # --------------------------------------------------------------

    attempt_engine = PaymentAttemptEngine(
        resolver=resolver,
        lifecycle_engine=lifecycle_engine,
        attempts_config=
            transactions_config[
                "attempts"
            ],
        rng=random.Random(SEED),
    )

    # --------------------------------------------------------------
    # Payment simulator
    # --------------------------------------------------------------

    payment_simulator = PaymentSimulator(
        transaction_generator=
            transaction_generator,
        attempt_engine=
            attempt_engine,
    )

    # --------------------------------------------------------------
    # Volume generator
    # --------------------------------------------------------------

    volume_generator = TransactionVolumeGenerator(
        volume_config=volume_config,
        rng=random.Random(SEED),
    )

    # --------------------------------------------------------------
    # Daily simulator
    # --------------------------------------------------------------

    return DailyTransactionSimulator(
        volume_generator=
            volume_generator,
        payment_simulator=
            payment_simulator,
    )


def validate_transaction_context(
    transaction,
    context,
):

    customer = context["customer"]
    merchant = context["merchant"]
    product = context["product"]
    payment_method = context["payment_method"]

    # --------------------------------------------------------------
    # Customer relationship
    # --------------------------------------------------------------

    if transaction["customer_fk"] != customer["id"]:
        raise AssertionError(
            "Transaction customer_fk does not "
            "match selected customer."
        )

    # --------------------------------------------------------------
    # Merchant relationship
    # --------------------------------------------------------------

    if transaction["merchant_fk"] != merchant["id"]:
        raise AssertionError(
            "Transaction merchant_fk does not "
            "match selected merchant."
        )

    # --------------------------------------------------------------
    # Product relationship
    # --------------------------------------------------------------

    if transaction["product_fk"] != product["id"]:
        raise AssertionError(
            "Transaction product_fk does not "
            "match selected product."
        )

    if product["merchant_fk"] != merchant["id"]:
        raise AssertionError(
            "Product does not belong to "
            "selected merchant."
        )

    # --------------------------------------------------------------
    # Payment method relationship
    # --------------------------------------------------------------

    if transaction[
        "payment_method_fk"
    ] != payment_method["id"]:

        raise AssertionError(
            "Transaction payment_method_fk "
            "does not match selected payment method."
        )

    if payment_method[
        "customer_fk"
    ] != customer["id"]:

        raise AssertionError(
            "Payment method does not belong "
            "to selected customer."
        )

    # --------------------------------------------------------------
    # Currency
    # --------------------------------------------------------------

    if product["currency"] != (
        merchant["default_currency"]
    ):
        raise AssertionError(
            "Product currency does not match "
            "merchant currency."
        )

    if transaction["currency"] != (
        product["currency"]
    ):
        raise AssertionError(
            "Transaction currency does not "
            "match product currency."
        )

    # --------------------------------------------------------------
    # Amount
    # --------------------------------------------------------------

    expected_amount = (
        Decimal(str(product["base_price"]))
        * Decimal(transaction["quantity"])
    ).quantize(
        Decimal("0.01")
    )

    if transaction["amount"] != expected_amount:

        raise AssertionError(
            "Transaction amount does not equal "
            "product base price × quantity."
        )

    # --------------------------------------------------------------
    # Quantity
    # --------------------------------------------------------------

    if transaction["quantity"] < 1:
        raise AssertionError(
            "Transaction quantity must be positive."
        )

    # --------------------------------------------------------------
    # Geography
    # --------------------------------------------------------------

    is_cross_border = context[
        "is_cross_border"
    ]

    countries_match = (
        customer["country_code"]
        == merchant["country_code"]
    )

    if is_cross_border and countries_match:
        raise AssertionError(
            "Transaction marked cross-border "
            "but customer and merchant countries "
            "are identical."
        )

    if not is_cross_border and not countries_match:
        raise AssertionError(
            "Transaction marked domestic "
            "but customer and merchant countries "
            "differ."
        )

    # --------------------------------------------------------------
    # Timezone
    # --------------------------------------------------------------

    initiated_at = transaction[
        "initiated_at"
    ]

    if initiated_at.tzinfo is None:
        raise AssertionError(
            "Transaction timestamp is not timezone-aware."
        )

    # Python zoneinfo comparison through key
    timezone_name = getattr(
        initiated_at.tzinfo,
        "key",
        None,
    )

    if timezone_name != customer["timezone"]:
        raise AssertionError(
            "Transaction timezone does not "
            "match customer timezone."
        )


def validate_attempts(
    payment,
    context,
):

    transaction = payment["transaction"]
    attempts = payment["attempts"]

    if not attempts:
        raise AssertionError(
            "Transaction has no payment attempts."
        )

    transaction_started = (
        transaction["initiated_at"]
    )

    previous_completed_at = None

    for expected_number, attempt in enumerate(
        attempts,
        start=1,
    ):

        # ----------------------------------------------------------
        # Attempt numbering
        # ----------------------------------------------------------

        if attempt["attempt_number"] != (
            expected_number
        ):
            raise AssertionError(
                "Payment attempt numbering is not sequential."
            )

        # ----------------------------------------------------------
        # Attempt timestamps
        # ----------------------------------------------------------

        initiated_at = attempt[
            "initiated_at"
        ]

        completed_at = attempt[
            "completed_at"
        ]

        if initiated_at < transaction_started:
            raise AssertionError(
                "Payment attempt starts before "
                "transaction initiation."
            )

        if completed_at < initiated_at:
            raise AssertionError(
                "Payment attempt completed "
                "before it started."
            )

        if previous_completed_at is not None:

            if initiated_at < previous_completed_at:
                raise AssertionError(
                    "Retry attempt begins before "
                    "previous attempt completed."
                )

        previous_completed_at = completed_at

        # ----------------------------------------------------------
        # Processor eligibility
        # ----------------------------------------------------------

        processor = attempt["processor"]

        eligible_processors = context[
            "eligible_processors"
        ]

        eligible_ids = {
            processor_item["id"]
            for processor_item
            in eligible_processors
        }

        if processor["id"] not in eligible_ids:

            raise AssertionError(
                "Payment attempt selected "
                "an ineligible processor."
            )

        # ----------------------------------------------------------
        # Attempt status
        # ----------------------------------------------------------

        if attempt["attempt_status"] not in {
            "CAPTURED",
            "FAILED",
            "CANCELED",
        }:

            raise AssertionError(
                "Invalid payment attempt status."
            )

        # ----------------------------------------------------------
        # Failure reason
        # ----------------------------------------------------------

        if attempt["attempt_status"] == "FAILED":

            if not attempt["failure_reason"]:
                raise AssertionError(
                    "Failed payment attempt is missing "
                    "failure_reason."
                )

        else:

            if attempt["failure_reason"] is not None:
                raise AssertionError(
                    "Non-failed payment attempt has "
                    "a failure reason."
                )


def validate_events(
    payment,
):

    transaction = payment["transaction"]
    attempts = payment["attempts"]

    previous_attempt_completed_at = None

    for attempt in attempts:

        events = attempt["events"]

        if not events:
            raise AssertionError(
                "Payment attempt has no events."
            )

        # ----------------------------------------------------------
        # Sequence numbers
        # ----------------------------------------------------------

        expected_sequence = 1

        previous_event_at = None

        for event in events:

            if event["sequence_number"] != (
                expected_sequence
            ):
                raise AssertionError(
                    "Payment event sequence numbers "
                    "are not sequential."
                )

            expected_sequence += 1

            event_at = event["event_at"]

            # Event must not occur before attempt
            if event_at < attempt[
                "initiated_at"
            ]:
                raise AssertionError(
                    "Payment event occurs before "
                    "attempt initiation."
                )

            # Events must be chronological
            if previous_event_at is not None:

                if event_at < previous_event_at:
                    raise AssertionError(
                        "Payment events are not "
                        "chronologically ordered."
                    )

            previous_event_at = event_at

            # Event cannot occur after attempt completion
            if event_at > attempt[
                "completed_at"
            ]:
                raise AssertionError(
                    "Payment event occurs after "
                    "attempt completion."
                )

        # Last event should align with attempt completion
        if events[-1]["event_at"] != (
            attempt["completed_at"]
        ):
            raise AssertionError(
                "Final payment event timestamp does not "
                "match attempt completion."
            )

        # Retry must start after previous attempt
        if previous_attempt_completed_at is not None:

            if attempt["initiated_at"] < (
                previous_attempt_completed_at
            ):
                raise AssertionError(
                    "Retry begins before previous "
                    "attempt completed."
                )

        previous_attempt_completed_at = (
            attempt["completed_at"]
        )

    # --------------------------------------------------------------
    # Transaction completion
    # --------------------------------------------------------------

    if attempts[-1]["completed_at"] != (
        transaction["completed_at"]
    ):
        raise AssertionError(
            "Transaction completion timestamp does not "
            "match final payment attempt."
        )


def main():

    simulator = build_simulator()

    config = load_generator_config()

    historical_start_date = config[
        "simulation"
    ]["historical_start_date"]

    loader = TransactionLoader()

    latest_transaction_date = (
        loader.get_latest_transaction_date()
    )

    if latest_transaction_date is None:
        raise AssertionError(
            "No transactions found in the database."
        )

    if not isinstance(
        latest_transaction_date,
        date,
    ):
        latest_transaction_date = date.fromisoformat(
            str(latest_transaction_date)
        )

    start_date = historical_start_date
    end_date = latest_transaction_date

    print(
        f"Validation period: "
        f"{start_date} → {end_date}"
    )

    total_transactions = 0
    total_attempts = 0
    total_events = 0

    status_counts = {
        "CAPTURED": 0,
        "FAILED": 0,
        "CANCELED": 0,
    }

    retry_transactions = 0
    cross_border_transactions = 0

    seen_transaction_ids = set()

    print(
        "Starting transaction integrity validation..."
    )

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

        for payment in payments:

            transaction = payment[
                "transaction"
            ]

            simulation_date = transaction[
                "simulation_date"
            ]

            if simulation_date != transaction_date:
                raise AssertionError(
                    "Simulation date mismatch: "
                    f"transaction_id="
                    f"{transaction['transaction_id']}, "
                    f"expected={transaction_date}, "
                    f"actual={simulation_date}"
                )

            context = payment[
                "context"
            ]

            transaction_id = transaction[
                "transaction_id"
            ]

            # ------------------------------------------------------
            # ID uniqueness
            # ------------------------------------------------------

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

            # ------------------------------------------------------
            # Transaction ↔ context
            # ------------------------------------------------------

            validate_transaction_context(
                transaction,
                context,
            )

            # ------------------------------------------------------
            # Final status
            # ------------------------------------------------------

            if transaction[
                "current_status"
            ] != payment["final_status"]:

                raise AssertionError(
                    "Transaction status does not "
                    "match payment final status."
                )

            if payment["final_status"] not in (
                status_counts
            ):

                raise AssertionError(
                    "Unexpected transaction final status."
                )

            status_counts[
                payment["final_status"]
            ] += 1

            # ------------------------------------------------------
            # Attempts
            # ------------------------------------------------------

            attempts = payment[
                "attempts"
            ]

            validate_attempts(
                payment,
                context,
            )

            total_attempts += len(
                attempts
            )

            if len(attempts) > 1:
                retry_transactions += 1

            # ------------------------------------------------------
            # Events
            # ------------------------------------------------------

            validate_events(
                payment
            )

            total_events += sum(
                len(attempt["events"])
                for attempt in attempts
            )

            # ------------------------------------------------------
            # Cross-border
            # ------------------------------------------------------

            if context[
                "is_cross_border"
            ]:
                cross_border_transactions += 1

            total_transactions += 1

    # --------------------------------------------------------------
    # Final validation
    # --------------------------------------------------------------

    if len(seen_transaction_ids) != (
        total_transactions
    ):
        raise AssertionError(
            "Transaction ID uniqueness check failed."
        )

    if total_attempts < total_transactions:
        raise AssertionError(
            "There must be at least one attempt "
            "per transaction."
        )

    if total_events < total_attempts:
        raise AssertionError(
            "There must be at least one event "
            "per payment attempt."
        )

    print()
    print(
        f"Transactions validated: "
        f"{total_transactions:,}"
    )

    print(
        f"Payment attempts validated: "
        f"{total_attempts:,}"
    )

    print(
        f"Payment events validated: "
        f"{total_events:,}"
    )

    print()

    print("Final status distribution:")

    for status, count in status_counts.items():

        percentage = (
            count / total_transactions * 100
        )

        print(
            f"{status}: "
            f"{count:,} "
            f"({percentage:.2f}%)"
        )

    print()

    print(
        f"Transactions with retries: "
        f"{retry_transactions:,}"
    )

    print(
        f"Cross-border transactions: "
        f"{cross_border_transactions:,}"
    )

    print()

    print(
        "All transaction integrity validation "
        "tests passed."
    )


if __name__ == "__main__":
    main()