from __future__ import annotations

import random
from datetime import date, timedelta


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

from simulator.engine.batch import (
    BATCH_MONTHS,
    get_next_batch,
)


# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------

DEFAULT_SEED = 20260823

# Database insertion batch.
#
# This is intentionally separate from the six-month historical
# simulation batch.
#
# It controls how many complete payment journeys are sent to
# PostgreSQL at one time.
DATABASE_BATCH_SIZE = 1000


# ----------------------------------------------------------------------
# Date helpers
# ----------------------------------------------------------------------

def parse_date(value) -> date:
    """
    Convert a YYYY-MM-DD configuration value to a date.
    """

    if isinstance(value, date):
        return value

    return date.fromisoformat(
        str(value)
    )


def derive_seed(base_seed: int, transaction_date: date, stream: int) -> int:
    """
    Derive a deterministic seed for a specific simulation date
    and RNG stream.

    The same base seed + date + stream always produces
    the same random sequence.
    """

    date_value = (
        transaction_date.year * 10000
        + transaction_date.month * 100
        + transaction_date.day
    )

    return (
        base_seed
        + (date_value * 100)
        + stream
    )


# ----------------------------------------------------------------------
# Simulator construction
# ----------------------------------------------------------------------

def build_simulator(
    config,
    seed,
    transaction_date: date,
):
    """
    Build the complete payment simulation pipeline.

    Architecture:

        Volume
            ↓
        Transaction
            ↓
        Lifecycle
            ↓
        Attempts
            ↓
        Complete Payment
            ↓
        Daily Simulation
    """

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

    # --------------------------------------------------------------
    # Volume configuration
    # --------------------------------------------------------------

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

    resolver = (
        TransactionDependencyResolver(
            dependencies
        )
    )

    # --------------------------------------------------------------
    # Deterministic RNG streams
    # --------------------------------------------------------------

    volume_rng = random.Random(
        derive_seed(
            seed,
            transaction_date,
            1,
        )
    )

    selector_rng = random.Random(
        derive_seed(
            seed,
            transaction_date,
            2,
        )
    )

    transaction_rng = random.Random(
        derive_seed(
            seed,
            transaction_date,
            3,
        )
    )

    lifecycle_rng = random.Random(
        derive_seed(
            seed,
            transaction_date,
            4,
        )
    )

    attempts_rng = random.Random(
        derive_seed(
            seed,
            transaction_date,
            5,
        )
    )

    # --------------------------------------------------------------
    # Volume generator
    # --------------------------------------------------------------

    volume_generator = (
        TransactionVolumeGenerator(
            volume_config=volume_config,
            rng=volume_rng,
        )
    )

    # --------------------------------------------------------------
    # Transaction selector
    # --------------------------------------------------------------

    selector = TransactionSelector(
        resolver=resolver,
        geography_config=config[
            "transactions"
        ]["geography"],
        rng=selector_rng,
    )

    # --------------------------------------------------------------
    # Transaction generator
    # --------------------------------------------------------------

    transaction_generator = (
        TransactionGenerator(
            selector=selector,
            transaction_config=transactions_config,
            rng=transaction_rng,
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
            rng=lifecycle_rng,
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
            rng=attempts_rng,
        )
    )

    # --------------------------------------------------------------
    # Complete payment simulator
    # --------------------------------------------------------------

    payment_simulator = PaymentSimulator(
        transaction_generator=
            transaction_generator,
        attempt_engine=
            attempt_engine,
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


# ----------------------------------------------------------------------
# Simulation
# ----------------------------------------------------------------------

def run_single_batch(
    start_date: date,
    end_date: date,
    config,
    seed: int,
    database_batch_size: int,
):
    """
    Generate and load exactly one historical batch.

    Each simulation date receives its own deterministic RNG streams.
    This makes generation independent of batch boundaries.

    Example:

        Generating Jan-Jun in one run
        and Jul-Dec in another

    produces the same Jan-Jun data as generating the whole
    period continuously.
    """

    print()
    print(
        "------------------------------------------------------------"
    )
    print(
        f"Generating batch: "
        f"{start_date} → {end_date}"
    )
    print(
        "------------------------------------------------------------"
    )

    loader = TransactionLoader()

    total_transactions = 0
    total_attempts = 0
    total_events = 0

    total_captured = 0
    total_failed = 0
    total_canceled = 0
    total_retried = 0
    total_cross_border = 0

    daily_summary = []

    current_generation_date = start_date

    while current_generation_date <= end_date:

        transaction_date = current_generation_date

        # ----------------------------------------------------------
        # Build a fresh simulator for this specific date.
        #
        # The RNG streams are derived from:
        #     base seed + date + stream
        #
        # Therefore this date is reproducible regardless of
        # which historical batch it belongs to.
        # ----------------------------------------------------------

        simulator = build_simulator(
            config=config,
            seed=seed,
            transaction_date=transaction_date,
        )

        payments = simulator.generate_day(
            transaction_date
        )

        # ----------------------------------------------------------
        # Daily counters
        # ----------------------------------------------------------

        day_transactions = 0
        day_attempts = 0
        day_events = 0

        day_captured = 0
        day_failed = 0
        day_canceled = 0
        day_retried = 0
        day_cross_border = 0

        # ----------------------------------------------------------
        # Load generated payments in database-sized chunks
        # ----------------------------------------------------------

        for offset in range(
            0,
            len(payments),
            database_batch_size,
        ):

            payment_batch = payments[
                offset:
                offset + database_batch_size
            ]

            if not payment_batch:
                continue

            loader_result = loader.load_batch(
                payment_batch
            )

            batch_transactions = (
                loader_result["transactions"]
            )

            batch_attempts = (
                loader_result["attempts"]
            )

            batch_events = (
                loader_result["events"]
            )

            batch_captured = (
                loader_result["captured"]
            )

            batch_failed = (
                loader_result["failed"]
            )

            batch_canceled = (
                loader_result["canceled"]
            )

            batch_retried = (
                loader_result["retried"]
            )

            batch_cross_border = (
                loader_result["cross_border"]
            )

            # ------------------------------------------------------
            # Daily totals
            # ------------------------------------------------------

            day_transactions += batch_transactions
            day_attempts += batch_attempts
            day_events += batch_events

            day_captured += batch_captured
            day_failed += batch_failed
            day_canceled += batch_canceled
            day_retried += batch_retried
            day_cross_border += batch_cross_border

            # ------------------------------------------------------
            # Overall totals
            # ------------------------------------------------------

            total_transactions += batch_transactions
            total_attempts += batch_attempts
            total_events += batch_events

            total_captured += batch_captured
            total_failed += batch_failed
            total_canceled += batch_canceled
            total_retried += batch_retried
            total_cross_border += batch_cross_border

        # ----------------------------------------------------------
        # Record daily result
        # ----------------------------------------------------------

        daily_summary.append(
            {
                "date": transaction_date,
                "transactions": day_transactions,
                "attempts": day_attempts,
                "events": day_events,
                "captured": day_captured,
                "failed": day_failed,
                "canceled": day_canceled,
                "retried": day_retried,
                "cross_border": day_cross_border,
            }
        )

        print(
            f"{transaction_date}: "
            f"{day_transactions:,} transactions | "
            f"{day_attempts:,} attempts | "
            f"{day_events:,} events"
        )

        # ----------------------------------------------------------
        # Move to next day
        # ----------------------------------------------------------

        current_generation_date += timedelta(
            days=1
        )

    return {
        "daily_summary": daily_summary,

        "total_transactions":
            total_transactions,

        "total_attempts":
            total_attempts,

        "total_events":
            total_events,

        "total_captured":
            total_captured,

        "total_failed":
            total_failed,

        "total_canceled":
            total_canceled,

        "total_retried":
            total_retried,

        "total_cross_border":
            total_cross_border,
    }


# ----------------------------------------------------------------------
# Resumable simulation
# ----------------------------------------------------------------------

def run_resumable_simulation(
    historical_start_date: date,
    historical_end_date: date,
    config,
    seed: int = DEFAULT_SEED,
    batch_months: int = BATCH_MONTHS,
    database_batch_size: int = DATABASE_BATCH_SIZE,
):
    """
    Generate historical payment data incrementally.

    The database determines where the previous simulation stopped.

    If the database is empty:
        start from historical_start_date.

    Otherwise:
        start from the day after MAX(initiated_at).

    Each batch is at most batch_months long and can never
    exceed historical_end_date.
    """

    loader = TransactionLoader()

    latest_date = (
        loader.get_latest_transaction_date()
    )

    # --------------------------------------------------------------
    # Determine starting point
    # --------------------------------------------------------------

    if latest_date is None:

        next_start_date = (
            historical_start_date
        )

        print(
            "Database contains no transaction data."
        )

    else:

        latest_date = parse_date(
            latest_date
        )

        if latest_date < historical_start_date:

            next_start_date = (
                historical_start_date
            )

        else:

            next_start_date = (
                latest_date
                + timedelta(days=1)
            )

        print(
            f"Latest transaction date in "
            f"database: {latest_date}"
        )

    # --------------------------------------------------------------
    # Already complete?
    # --------------------------------------------------------------

    if next_start_date > historical_end_date:

        print()
        print(
            "Simulation is already up to date."
        )

        print(
            f"Database through: "
            f"{latest_date}"
        )

        print(
            f"Configured end date: "
            f"{historical_end_date}"
        )

        return

    # --------------------------------------------------------------
    # Batch loop
    # --------------------------------------------------------------

    batch_number = 0

    while next_start_date <= historical_end_date:

        batch = get_next_batch(
            next_start_date=next_start_date,
            target_end_date=
                historical_end_date,
            batch_months=batch_months,
        )

        if batch is None:
            break

        batch_start, batch_end = batch

        batch_number += 1

        print()
        print(
            f"Starting historical batch "
            f"{batch_number}"
        )

        print(
            f"Period: "
            f"{batch_start} → {batch_end}"
        )

        result = run_single_batch(
            start_date=batch_start,
            end_date=batch_end,
            config=config,
            seed=seed,
            database_batch_size=
                database_batch_size,
        )

        # ----------------------------------------------------------
        # Batch-level summary
        # ----------------------------------------------------------

        print()
        print(
            f"Batch {batch_number} complete."
        )

        print(
            f"Transactions: "
            f"{result['total_transactions']:,}"
        )

        print(
            f"Payment attempts: "
            f"{result['total_attempts']:,}"
        )

        print(
            f"Payment events: "
            f"{result['total_events']:,}"
        )

        print(
            f"Captured: "
            f"{result['total_captured']:,}"
        )

        print(
            f"Failed: "
            f"{result['total_failed']:,}"
        )

        print(
            f"Canceled: "
            f"{result['total_canceled']:,}"
        )

        print(
            f"Retries: "
            f"{result['total_retried']:,}"
        )

        print(
            f"Cross-border: "
            f"{result['total_cross_border']:,}"
        )

        # ----------------------------------------------------------
        # IMPORTANT
        #
        # load_batch() commits the entire database batch
        # atomically. If it raises an exception, execution stops
        # here and we do NOT advance the simulation date.
        # ----------------------------------------------------------

        # Move to next ungenerated day only after the batch
        # completed successfully.

        next_start_date = (
            batch_end
            + timedelta(days=1)
        )

    print()
    print(
        "============================================================"
    )

    print(
        "Historical simulation complete."
    )

    print(
        f"Generated through: "
        f"{historical_end_date}"
    )

    print(
        "============================================================"
    )


# ----------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------

if __name__ == "__main__":

    config = load_generator_config()

    simulation_config = (
        config["simulation"]
    )

    historical_start_date = parse_date(
        simulation_config[
            "historical_start_date"
        ]
    )

    # --------------------------------------------------------------
    # Target end date
    #
    # Prefer historical_end_date if you add it to YAML.
    #
    # Keep current_date as a fallback so we don't unnecessarily
    # break your existing configuration.
    # --------------------------------------------------------------

    historical_end_value = (
        simulation_config.get(
            "historical_end_date"
        )
    )

    if historical_end_value is None:

        historical_end_value = (
            simulation_config[
                "current_date"
            ]
        )

    # # --------------------------------------------------------------
    # # TEMPORARY END DATE FOR END-TO-END VALIDATION
    # # --------------------------------------------------------------
    # #
    # # The database currently contains valid transaction data
    # # through 2023-03-11.
    # #
    # # We will first validate generation/loading for the next
    # # two days before launching the full historical run.
    # #

    # historical_end_date = date(2023, 3, 13)

    historical_end_date = parse_date(
        historical_end_value
    )

    print(
        "Starting payment simulation and "
        "database loading..."
    )

    print(
        f"Target historical period: "
        f"{historical_start_date} → "
        f"{historical_end_date}"
    )

    print(
        f"Historical batch size: "
        f"{BATCH_MONTHS} months"
    )

    print(
        f"Database batch size: "
        f"{DATABASE_BATCH_SIZE:,}"
    )

    print()

    run_resumable_simulation(
        historical_start_date=
            historical_start_date,
        historical_end_date=
            historical_end_date,
        config=config,
        seed=DEFAULT_SEED,
        batch_months=BATCH_MONTHS,
        database_batch_size=
            DATABASE_BATCH_SIZE,
    )