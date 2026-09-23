from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from database.connection import get_connection
from database.loaders.settlement_candidates import fetch_settlement_candidates
from database.loaders.settlements import SettlementLoader
from simulator.settlements.expected import calculate_expected_settlements
from simulator.settlements.processor_feed import generate_processor_settlements


DEFAULT_SEED = 20260907


@dataclass(frozen=True)
class SettlementRunResult:
    simulation_date: date
    simulation_seed: int
    candidate_count: int
    expected_settlement_count: int
    processor_entry_count: int
    missing_settlement_count: int
    settlement_batch_count: int
    status: str
    elapsed_seconds: float


def _validate_date_range(
    start_date: date,
    end_date: date,
) -> None:
    if not isinstance(start_date, date):
        raise TypeError("start_date must be a date.")

    if not isinstance(end_date, date):
        raise TypeError("end_date must be a date.")

    if start_date > end_date:
        raise ValueError("start_date cannot be after end_date.")


def _validate_seed(seed: int) -> None:
    if not isinstance(seed, int):
        raise TypeError("seed must be an integer.")


def _get_completed_run(
    connection,
    simulation_date: date,
) -> tuple | None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                simulation_date,
                simulation_seed,
                simulation_status,
                candidate_count,
                expected_settlement_count,
                processor_entry_count,
                missing_settlement_count,
                settlement_batch_count
            FROM settlement_simulation_runs
            WHERE simulation_date = %s
              AND simulation_status = 'COMPLETE'
            """,
            (simulation_date,),
        )

        return cursor.fetchone()


def _validate_existing_seed(
    existing_run: tuple,
    seed: int,
) -> None:
    existing_seed = existing_run[1]

    if existing_seed != seed:
        raise ValueError(
            "Simulation date is already COMPLETE with a different seed. "
            f"Existing seed={existing_seed}, requested seed={seed}. "
            "Use the original seed or explicitly reset the simulation date."
        )


def _start_checkpoint(
    connection,
    simulation_date: date,
    seed: int,
    started_at: datetime,
) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO settlement_simulation_runs (
                simulation_date,
                simulation_seed,
                simulation_status,
                started_at
            )
            VALUES (%s, %s, 'RUNNING', %s)
            """,
            (
                simulation_date,
                seed,
                started_at,
            ),
        )


def _complete_checkpoint(
    connection,
    simulation_date: date,
    seed: int,
    candidate_count: int,
    expected_settlement_count: int,
    processor_entry_count: int,
    missing_settlement_count: int,
    settlement_batch_count: int,
    completed_at: datetime,
) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE settlement_simulation_runs
            SET
                simulation_seed = %s,
                simulation_status = 'COMPLETE',
                candidate_count = %s,
                expected_settlement_count = %s,
                processor_entry_count = %s,
                missing_settlement_count = %s,
                settlement_batch_count = %s,
                completed_at = %s
            WHERE simulation_date = %s
              AND simulation_status = 'RUNNING'
            """,
            (
                seed,
                candidate_count,
                expected_settlement_count,
                processor_entry_count,
                missing_settlement_count,
                settlement_batch_count,
                completed_at,
                simulation_date,
            ),
        )

        if cursor.rowcount != 1:
            raise RuntimeError(
                "Failed to mark settlement simulation checkpoint COMPLETE "
                f"for {simulation_date}."
            )


def _print_stage(
    stage_number: int,
    total_stages: int,
    message: str,
) -> None:
    print(
        f"    [{stage_number}/{total_stages}] {message}",
        flush=True,
    )


def _process_simulation_date(
    simulation_date: date,
    seed: int,
) -> SettlementRunResult | None:

    start_time = time.perf_counter()
    started_at = datetime.now(timezone.utc)

    connection = get_connection()

    try:
        print()
        print("=" * 72)
        print(
            f"Settlement simulation: {simulation_date}"
        )
        print("=" * 72, flush=True)

        # ==============================================================
        # 0. Checkpoint / resume check
        # ==============================================================

        print(
            "    Checking simulation checkpoint...",
            flush=True,
        )

        existing_run = _get_completed_run(
            connection,
            simulation_date,
        )

        if existing_run is not None:
            _validate_existing_seed(
                existing_run,
                seed,
            )

            elapsed = time.perf_counter() - start_time

            print(
                f"    Already COMPLETE — skipping "
                f"({elapsed:.2f}s)",
                flush=True,
            )

            return SettlementRunResult(
                simulation_date=simulation_date,
                simulation_seed=existing_run[1],
                candidate_count=existing_run[3],
                expected_settlement_count=existing_run[4],
                processor_entry_count=existing_run[5],
                missing_settlement_count=existing_run[6],
                settlement_batch_count=existing_run[7],
                status="SKIPPED",
                elapsed_seconds=elapsed,
            )

        connection.rollback()

        _start_checkpoint(
            connection=connection,
            simulation_date=simulation_date,
            seed=seed,
            started_at=started_at,
        )

        # ==============================================================
        # 1. Fetch candidates
        # ==============================================================

        stage_start = time.perf_counter()

        _print_stage(
            1,
            5,
            "Fetching settlement candidates...",
        )

        candidates = fetch_settlement_candidates(
            start_date=simulation_date,
            end_date=simulation_date,
        )

        candidate_count = len(candidates)

        stage_elapsed = time.perf_counter() - stage_start

        print(
            f"           Candidates fetched : {candidate_count:,}",
            flush=True,
        )
        print(
            f"           Stage time          : {stage_elapsed:.2f}s",
            flush=True,
        )

        # ==============================================================
        # 2. Calculate expected settlements
        # ==============================================================

        stage_start = time.perf_counter()

        _print_stage(
            2,
            5,
            "Calculating expected settlements...",
        )

        expected_settlements = calculate_expected_settlements(
            candidates
        )

        expected_settlement_count = len(
            expected_settlements
        )

        stage_elapsed = time.perf_counter() - stage_start

        if expected_settlement_count != candidate_count:
            raise RuntimeError(
                "Expected settlement count does not match "
                "candidate count. "
                f"Candidates={candidate_count}, "
                f"Expected={expected_settlement_count}."
            )

        print(
            f"           Expected settlements: "
            f"{expected_settlement_count:,}",
            flush=True,
        )
        print(
            f"           Stage time          : "
            f"{stage_elapsed:.2f}s",
            flush=True,
        )

        # ==============================================================
        # 3. Generate processor settlement feed
        # ==============================================================

        stage_start = time.perf_counter()

        _print_stage(
            3,
            5,
            "Generating processor settlement feed...",
        )

        processor_entries = generate_processor_settlements(
            expected_settlements,
            seed=seed,
        )

        processor_entry_count = len(
            processor_entries
        )

        missing_settlement_count = (
            expected_settlement_count
            - processor_entry_count
        )

        stage_elapsed = time.perf_counter() - stage_start

        if missing_settlement_count < 0:
            raise RuntimeError(
                "Processor entry count cannot exceed "
                "expected settlement count."
            )

        print(
            f"           Processor entries   : "
            f"{processor_entry_count:,}",
            flush=True,
        )
        print(
            f"           Missing settlements : "
            f"{missing_settlement_count:,}",
            flush=True,
        )
        print(
            f"           Stage time          : "
            f"{stage_elapsed:.2f}s",
            flush=True,
        )

        # ==============================================================
        # 4. Persist settlement data
        # ==============================================================

        stage_start = time.perf_counter()

        _print_stage(
            4,
            5,
            "Loading settlement batches and entries...",
        )

        loader = SettlementLoader(connection)

        load_result = loader.load_batch(
            processor_entries
        )

        settlement_batch_count = load_result[
            "batches"
        ]

        loaded_entry_count = load_result[
            "entries"
        ]

        stage_elapsed = time.perf_counter() - stage_start

        if loaded_entry_count != processor_entry_count:
            raise RuntimeError(
                "Settlement loader entry count does not "
                "match generated processor entry count. "
                f"Generated={processor_entry_count}, "
                f"Loaded={loaded_entry_count}."
            )

        print(
            f"           Entries loaded       : "
            f"{loaded_entry_count:,}",
            flush=True,
        )
        print(
            f"           Batches affected     : "
            f"{settlement_batch_count:,}",
            flush=True,
        )
        print(
            f"           Stage time          : "
            f"{stage_elapsed:.2f}s",
            flush=True,
        )

        # ==============================================================
        # 5. Complete checkpoint and commit
        # ==============================================================

        stage_start = time.perf_counter()

        _print_stage(
            5,
            5,
            "Completing checkpoint and committing transaction...",
        )

        completed_at = datetime.now(timezone.utc)

        _complete_checkpoint(
            connection=connection,
            simulation_date=simulation_date,
            seed=seed,
            candidate_count=candidate_count,
            expected_settlement_count=expected_settlement_count,
            processor_entry_count=processor_entry_count,
            missing_settlement_count=missing_settlement_count,
            settlement_batch_count=settlement_batch_count,
            completed_at=completed_at,
        )

        connection.commit()

        stage_elapsed = time.perf_counter() - stage_start

        print(
            f"           Commit complete      : "
            f"{stage_elapsed:.2f}s",
            flush=True,
        )

        # ==============================================================
        # Final result
        # ==============================================================

        elapsed = time.perf_counter() - start_time

        rate = (
            candidate_count / elapsed
            if elapsed > 0
            else 0
        )

        print()
        print(
            f"    {simulation_date} | COMPLETE | "
            f"candidates={candidate_count:,} | "
            f"expected={expected_settlement_count:,} | "
            f"entries={processor_entry_count:,} | "
            f"missing={missing_settlement_count:,} | "
            f"batches={settlement_batch_count:,} | "
            f"rate={rate:,.0f}/sec | "
            f"elapsed={elapsed:.2f}s",
            flush=True,
        )

        return SettlementRunResult(
            simulation_date=simulation_date,
            simulation_seed=seed,
            candidate_count=candidate_count,
            expected_settlement_count=expected_settlement_count,
            processor_entry_count=processor_entry_count,
            missing_settlement_count=missing_settlement_count,
            settlement_batch_count=settlement_batch_count,
            status="COMPLETE",
            elapsed_seconds=elapsed,
        )

    except Exception as exc:

        connection.rollback()

        elapsed = time.perf_counter() - start_time

        print(
            f"{simulation_date} | FAILED  | "
            f"transaction rolled back | "
            f"elapsed={elapsed:.2f}s | "
            f"error={type(exc).__name__}: {exc}",
            flush=True,
        )

        raise

    finally:
        connection.close()


def run_settlement_simulation(
    start_date: date,
    end_date: date,
    seed: int = DEFAULT_SEED,
) -> list[SettlementRunResult]:
    """
    Run settlement simulation for an inclusive date range.

    Each simulation date is processed in its own database transaction.

    A completed simulation date is skipped on subsequent runs, provided
    the same seed is supplied.

    If processing fails before commit, all settlement data and the
    checkpoint for that date are rolled back.
    """

    _validate_date_range(
        start_date,
        end_date,
    )

    _validate_seed(seed)

    total_days = (
        end_date - start_date
    ).days + 1

    print()
    print("=" * 72)
    print("SETTLEMENT DATA GENERATION")
    print("=" * 72)
    print(
        f"Date range : {start_date} → {end_date}"
    )
    print(
        f"Days       : {total_days:,}"
    )
    print(
        f"Seed       : {seed}"
    )
    print("=" * 72, flush=True)

    results: list[SettlementRunResult] = []

    current_date = start_date
    day_number = 0

    while current_date <= end_date:

        day_number += 1

        print()
        print(
            f"Progress: day {day_number:,}/{total_days:,} "
            f"({current_date})",
            flush=True,
        )

        result = _process_simulation_date(
            simulation_date=current_date,
            seed=seed,
        )

        if result is not None:
            results.append(result)

        current_date += timedelta(days=1)

    return results


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)

    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid date '{value}'. Expected YYYY-MM-DD."
        ) from exc


def main() -> None:

    parser = argparse.ArgumentParser(
        description=(
            "Generate and persist synthetic processor settlement "
            "data with date-level checkpoints."
        )
    )

    parser.add_argument(
        "--start-date",
        required=True,
        type=_parse_date,
        help="Inclusive simulation start date (YYYY-MM-DD).",
    )

    parser.add_argument(
        "--end-date",
        required=True,
        type=_parse_date,
        help="Inclusive simulation end date (YYYY-MM-DD).",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=(
            f"Deterministic processor-feed seed. "
            f"Default: {DEFAULT_SEED}."
        ),
    )

    args = parser.parse_args()

    results = run_settlement_simulation(
        start_date=args.start_date,
        end_date=args.end_date,
        seed=args.seed,
    )

    total_candidates = sum(
        result.candidate_count
        for result in results
    )

    total_entries = sum(
        result.processor_entry_count
        for result in results
    )

    total_missing = sum(
        result.missing_settlement_count
        for result in results
    )

    total_batches = sum(
        result.settlement_batch_count
        for result in results
    )

    completed_dates = sum(
        result.status == "COMPLETE"
        for result in results
    )

    skipped_dates = sum(
        result.status == "SKIPPED"
        for result in results
    )

    print()
    print("=" * 72)
    print("SETTLEMENT SIMULATION SUMMARY")
    print("=" * 72)
    print(
        f"Dates processed   : {len(results):,}"
    )
    print(
        f"New dates         : {completed_dates:,}"
    )
    print(
        f"Skipped dates     : {skipped_dates:,}"
    )
    print(
        f"Candidates        : {total_candidates:,}"
    )
    print(
        f"Processor entries : {total_entries:,}"
    )
    print(
        f"Missing           : {total_missing:,}"
    )
    print(
        f"Settlement batches: {total_batches:,}"
    )
    print("=" * 72)


if __name__ == "__main__":
    main()