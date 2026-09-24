from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from datetime import date, datetime

from database.connection import get_connection
from database.loaders.reconciliation import reconcile_settlements


# ======================================================================
# Data structures
# ======================================================================


@dataclass(frozen=True)
class ReconciliationRunResult:
    simulation_date: date
    status: str
    reconciliation_count: int
    matched_count: int
    amount_mismatch_count: int
    missing_settlement_count: int
    timing_exception_count: int
    status_mismatch_count: int
    processor_mismatch_count: int
    unmatched_processor_entry_count: int
    elapsed_seconds: float


# ======================================================================
# Validation
# ======================================================================


def _validate_date_range(
    start_date: date,
    end_date: date,
) -> None:
    if not isinstance(start_date, date):
        raise TypeError("start_date must be a date.")

    if not isinstance(end_date, date):
        raise TypeError("end_date must be a date.")

    if start_date > end_date:
        raise ValueError(
            "start_date cannot be after end_date."
        )


# ======================================================================
# Database helpers
# ======================================================================


def _get_completed_simulation_dates(
    start_date: date,
    end_date: date,
) -> list[date]:
    """
    Return settlement simulation dates that completed successfully.

    Reconciliation should only run against dates for which the settlement
    simulation itself completed successfully.
    """

    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT simulation_date
                FROM settlement_simulation_runs
                WHERE simulation_status = 'COMPLETE'
                  AND simulation_date BETWEEN %s AND %s
                ORDER BY simulation_date;
                """,
                (
                    start_date,
                    end_date,
                ),
            )

            return [
                row[0]
                for row in cursor.fetchall()
            ]

    finally:
        connection.close()


def _get_existing_reconciliation_count(
    simulation_date: date,
) -> int:
    """
    Return the number of reconciliation rows already persisted
    for a simulation date.

    A non-zero result means the date has already been reconciled.

    The reconciliation loader is atomic, so a failed run should not
    leave a partially populated date.
    """

    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM reconciliation_settlements
                WHERE simulation_date = %s;
                """,
                (simulation_date,),
            )

            return cursor.fetchone()[0]

    finally:
        connection.close()


# ======================================================================
# Reporting
# ======================================================================


def _format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"

    minutes, remaining_seconds = divmod(seconds, 60)

    if minutes < 60:
        return (
            f"{int(minutes)}m "
            f"{remaining_seconds:.0f}s"
        )

    hours, remaining_minutes = divmod(minutes, 60)

    return (
        f"{int(hours)}h "
        f"{int(remaining_minutes)}m "
        f"{remaining_seconds:.0f}s"
    )


def _format_rate(
    completed_dates: int,
    elapsed_seconds: float,
) -> str:
    if elapsed_seconds <= 0:
        return "0.00 dates/sec"

    rate = completed_dates / elapsed_seconds

    return f"{rate:.3f} dates/sec"


def _print_progress(
    *,
    completed: int,
    total: int,
    elapsed_seconds: float,
) -> None:
    if total <= 0:
        return

    percentage = (
        completed / total
    ) * 100

    remaining = total - completed

    if completed > 0:
        average_seconds = (
            elapsed_seconds / completed
        )

        eta_seconds = (
            average_seconds * remaining
        )
    else:
        eta_seconds = 0

    print()
    print(
        f"Progress: "
        f"{completed:,}/{total:,} "
        f"({percentage:.1f}%)"
    )

    print(
        f"Elapsed : "
        f"{_format_duration(elapsed_seconds)}"
    )

    print(
        f"Rate    : "
        f"{_format_rate(completed, elapsed_seconds)}"
    )

    print(
        f"ETA     : "
        f"{_format_duration(eta_seconds)}"
    )

    print(
        f"Remaining dates: "
        f"{remaining:,}",
        flush=True,
    )


# ======================================================================
# Per-date processing
# ======================================================================


def _process_date(
    simulation_date: date,
    *,
    force: bool = False,
) -> ReconciliationRunResult:
    """
    Reconcile one simulation date.

    The actual reconciliation transaction is owned by
    reconcile_settlements(). Therefore each date is committed or rolled
    back independently.
    """

    start_time = time.perf_counter()

    print()
    print("-" * 72)
    print(
        f"Reconciliation: {simulation_date}"
    )
    print("-" * 72)

    # --------------------------------------------------------------
    # Resume / idempotency check
    # --------------------------------------------------------------

    if not force:
        existing_count = _get_existing_reconciliation_count(
            simulation_date
        )

        if existing_count > 0:
            elapsed = time.perf_counter() - start_time

            print(
                f"    Already reconciled — "
                f"{existing_count:,} rows found."
            )

            print(
                f"    Skipping "
                f"({elapsed:.2f}s).",
                flush=True,
            )

            return ReconciliationRunResult(
                simulation_date=simulation_date,
                status="SKIPPED",
                reconciliation_count=existing_count,
                matched_count=0,
                amount_mismatch_count=0,
                missing_settlement_count=0,
                timing_exception_count=0,
                status_mismatch_count=0,
                processor_mismatch_count=0,
                unmatched_processor_entry_count=0,
                elapsed_seconds=elapsed,
            )

    # --------------------------------------------------------------
    # Execute reconciliation
    # --------------------------------------------------------------

    print(
        "    Running reconciliation...",
        flush=True,
    )

    try:
        result = reconcile_settlements(
            simulation_date
        )

    except Exception as exc:
        elapsed = time.perf_counter() - start_time

        print(
            f"    FAILED after "
            f"{elapsed:.2f}s",
            flush=True,
        )

        print(
            f"    Error: "
            f"{type(exc).__name__}: {exc}",
            flush=True,
        )

        raise

    # --------------------------------------------------------------
    # Result
    # --------------------------------------------------------------

    elapsed = time.perf_counter() - start_time

    print(
        f"    Reconciliation rows : "
        f"{result['reconciliation_count']:,}"
    )

    print(
        f"    Matched              : "
        f"{result['matched_count']:,}"
    )

    print(
        f"    Amount mismatches    : "
        f"{result['amount_mismatch_count']:,}"
    )

    print(
        f"    Missing settlements  : "
        f"{result['missing_settlement_count']:,}"
    )

    print(
        f"    Timing exceptions    : "
        f"{result['timing_exception_count']:,}"
    )

    print(
        f"    Status mismatches    : "
        f"{result['status_mismatch_count']:,}"
    )

    print(
        f"    Processor mismatches : "
        f"{result['processor_mismatch_count']:,}"
    )

    print(
        f"    Unmatched processor  : "
        f"{result['unmatched_processor_entry_count']:,}"
    )

    print(
        f"    Completed in         : "
        f"{elapsed:.2f}s",
        flush=True,
    )

    return ReconciliationRunResult(
        simulation_date=simulation_date,
        status="COMPLETE",
        reconciliation_count=result[
            "reconciliation_count"
        ],
        matched_count=result[
            "matched_count"
        ],
        amount_mismatch_count=result[
            "amount_mismatch_count"
        ],
        missing_settlement_count=result[
            "missing_settlement_count"
        ],
        timing_exception_count=result[
            "timing_exception_count"
        ],
        status_mismatch_count=result[
            "status_mismatch_count"
        ],
        processor_mismatch_count=result[
            "processor_mismatch_count"
        ],
        unmatched_processor_entry_count=result[
            "unmatched_processor_entry_count"
        ],
        elapsed_seconds=elapsed,
    )


# ======================================================================
# Historical runner
# ======================================================================


def run_reconciliation(
    start_date: date,
    end_date: date,
    *,
    force: bool = False,
) -> list[ReconciliationRunResult]:
    """
    Run reconciliation across an inclusive date range.

    Only settlement simulation dates marked COMPLETE are processed.

    Each date is an independent transaction.

    Existing reconciliation dates are skipped unless force=True.

    If a date fails, the exception is raised and the dates already
    committed remain intact.
    """

    _validate_date_range(
        start_date,
        end_date,
    )

    print()
    print("=" * 72)
    print("SETTLEMENT RECONCILIATION")
    print("=" * 72)

    print(
        f"Requested range : "
        f"{start_date} → {end_date}"
    )

    print(
        f"Force rebuild   : "
        f"{force}"
    )

    print(
        "Discovering completed settlement dates...",
        flush=True,
    )

    simulation_dates = _get_completed_simulation_dates(
        start_date,
        end_date,
    )

    total_dates = len(simulation_dates)

    print(
        f"Completed settlement dates available: "
        f"{total_dates:,}",
        flush=True,
    )

    if total_dates == 0:
        print()
        print(
            "No completed settlement simulation dates "
            "were found in the requested range."
        )
        return []

    print("=" * 72, flush=True)

    results: list[ReconciliationRunResult] = []

    overall_start = time.perf_counter()

    for index, simulation_date in enumerate(
        simulation_dates,
        start=1,
    ):

        print()
        print(
            f"[{index:,}/{total_dates:,}] "
            f"Processing {simulation_date}",
            flush=True,
        )

        result = _process_date(
            simulation_date,
            force=force,
        )

        results.append(result)

        overall_elapsed = (
            time.perf_counter()
            - overall_start
        )

        _print_progress(
            completed=index,
            total=total_dates,
            elapsed_seconds=overall_elapsed,
        )

    return results


# ======================================================================
# Summary
# ======================================================================


def _print_summary(
    results: list[ReconciliationRunResult],
    overall_elapsed: float,
) -> None:
    total_dates = len(results)

    completed_dates = sum(
        result.status == "COMPLETE"
        for result in results
    )

    skipped_dates = sum(
        result.status == "SKIPPED"
        for result in results
    )

    total_rows = sum(
        result.reconciliation_count
        for result in results
    )

    total_matched = sum(
        result.matched_count
        for result in results
    )

    total_amount_mismatches = sum(
        result.amount_mismatch_count
        for result in results
    )

    total_missing = sum(
        result.missing_settlement_count
        for result in results
    )

    total_timing = sum(
        result.timing_exception_count
        for result in results
    )

    total_status = sum(
        result.status_mismatch_count
        for result in results
    )

    total_processor_mismatch = sum(
        result.processor_mismatch_count
        for result in results
    )

    total_unmatched = sum(
        result.unmatched_processor_entry_count
        for result in results
    )

    print()
    print()
    print("=" * 72)
    print("RECONCILIATION SUMMARY")
    print("=" * 72)

    print(
        f"Dates processed             : "
        f"{total_dates:,}"
    )

    print(
        f"New dates                   : "
        f"{completed_dates:,}"
    )

    print(
        f"Skipped dates               : "
        f"{skipped_dates:,}"
    )

    print(
        f"Reconciliation rows         : "
        f"{total_rows:,}"
    )

    print(
        f"Matched                     : "
        f"{total_matched:,}"
    )

    print(
        f"Amount mismatches           : "
        f"{total_amount_mismatches:,}"
    )

    print(
        f"Missing settlements         : "
        f"{total_missing:,}"
    )

    print(
        f"Timing exceptions           : "
        f"{total_timing:,}"
    )

    print(
        f"Status mismatches           : "
        f"{total_status:,}"
    )

    print(
        f"Processor mismatches        : "
        f"{total_processor_mismatch:,}"
    )

    print(
        f"Unmatched processor entries: "
        f"{total_unmatched:,}"
    )

    print(
        f"Total elapsed               : "
        f"{_format_duration(overall_elapsed)}"
    )

    if total_dates > 0:
        print(
            f"Average/date               : "
            f"{overall_elapsed / total_dates:.2f}s"
        )

    print("=" * 72)


# ======================================================================
# CLI
# ======================================================================


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)

    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid date '{value}'. "
            "Expected YYYY-MM-DD."
        ) from exc


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run settlement reconciliation across "
            "completed simulation dates."
        )
    )

    parser.add_argument(
        "--start-date",
        required=True,
        type=_parse_date,
        help=(
            "Inclusive reconciliation start date "
            "(YYYY-MM-DD)."
        ),
    )

    parser.add_argument(
        "--end-date",
        required=True,
        type=_parse_date,
        help=(
            "Inclusive reconciliation end date "
            "(YYYY-MM-DD)."
        ),
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Rebuild reconciliation results even when "
            "rows already exist for a date."
        ),
    )

    args = parser.parse_args()

    started_at = datetime.now()

    results = run_reconciliation(
        start_date=args.start_date,
        end_date=args.end_date,
        force=args.force,
    )

    overall_elapsed = (
        datetime.now() - started_at
    ).total_seconds()

    _print_summary(
        results,
        overall_elapsed,
    )


if __name__ == "__main__":
    main()