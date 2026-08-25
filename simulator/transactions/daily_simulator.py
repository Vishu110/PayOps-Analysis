from __future__ import annotations

from datetime import date, timedelta
from collections.abc import Iterator


class DailyTransactionSimulator:
    """
    Generate complete payment journeys day by day according to
    the daily transaction-volume model.

    The simulator does not write to the database.

    Payments can be generated in smaller batches so the caller can
    generate -> load -> discard batches instead of holding an entire
    day's payment journeys in memory.

    IMPORTANT:
    This class does not alter any business rules. It only controls
    how payment journeys are yielded.
    """

    def __init__(
        self,
        volume_generator,
        payment_simulator,
    ):
        self.volume_generator = volume_generator
        self.payment_simulator = payment_simulator

    # ------------------------------------------------------------------
    # Date range
    # ------------------------------------------------------------------

    def _date_range(
        self,
        start_date: date,
        end_date: date,
    ) -> Iterator[date]:

        if start_date > end_date:
            raise ValueError(
                "Start date cannot be after end date."
            )

        current_date = start_date

        while current_date <= end_date:
            yield current_date

            current_date += timedelta(days=1)

    # ------------------------------------------------------------------
    # Daily volume
    # ------------------------------------------------------------------

    def get_daily_volume(
        self,
        transaction_date: date,
    ) -> int:
        """
        Return the transaction volume for a single day.

        This uses the existing volume generator without modifying
        its business rules.
        """

        volume = (
            self.volume_generator
            .generate_daily_volume(
                transaction_date
            )
        )

        if volume < 0:
            raise ValueError(
                "Daily transaction volume cannot be negative."
            )

        return int(volume)

    # ------------------------------------------------------------------
    # Generate one day - full list
    # ------------------------------------------------------------------

    def generate_day(
        self,
        transaction_date: date,
    ) -> list[dict]:
        """
        Generate all payment journeys for one day.

        This method is retained for compatibility with the existing
        tests and code.

        For large simulations, prefer generate_day_batches().
        """

        daily_volume = self.get_daily_volume(
            transaction_date
        )

        payments = []

        for _ in range(daily_volume):

            payment = (
                self.payment_simulator
                .generate_one(
                    transaction_date=transaction_date
                )
            )

            payments.append(payment)

        return payments

    # ------------------------------------------------------------------
    # Generate one day - batches
    # ------------------------------------------------------------------

    def generate_day_batches(
        self,
        transaction_date: date,
        batch_size: int = 1000,
    ) -> Iterator[list[dict]]:
        """
        Generate payment journeys for one day in smaller batches.

        Example:

            18,000 transactions
            batch_size = 1,000

        produces:

            batch 1 -> 1,000
            batch 2 -> 1,000
            ...
            batch 18 -> 1,000

        The payment-generation logic itself is unchanged.
        Only the number of objects retained in memory at once
        is reduced.
        """

        if batch_size < 1:
            raise ValueError(
                "batch_size must be at least 1."
            )

        daily_volume = self.get_daily_volume(
            transaction_date
        )

        batch = []

        for _ in range(daily_volume):

            payment = (
                self.payment_simulator
                .generate_one(
                    transaction_date=transaction_date
                )
            )

            batch.append(payment)

            if len(batch) >= batch_size:

                yield batch

                # Release the current batch before generating
                # the next one.
                batch = []

        # Yield the final partial batch.
        if batch:
            yield batch

    # ------------------------------------------------------------------
    # Generate date range - full days
    # ------------------------------------------------------------------

    def generate_range(
        self,
        start_date: date,
        end_date: date,
    ) -> Iterator[tuple[date, list[dict]]]:
        """
        Generate one complete day's payments at a time.

        Retained for compatibility with the existing run_simulation.py.
        """

        for transaction_date in self._date_range(
            start_date,
            end_date,
        ):

            payments = self.generate_day(
                transaction_date
            )

            yield (
                transaction_date,
                payments,
            )

    # ------------------------------------------------------------------
    # Generate date range - streaming batches
    # ------------------------------------------------------------------

    def generate_range_batches(
        self,
        start_date: date,
        end_date: date,
        batch_size: int = 1000,
    ) -> Iterator[tuple[date, list[dict]]]:
        """
        Generate payment journeys across a date range in batches.

        Each yielded value is:

            (
                transaction_date,
                payments_batch
            )

        This is the preferred method for large historical
        simulations.

        Example:

            2026-08-10
                -> batch 1
                -> batch 2
                -> ...

            2026-08-11
                -> batch 1
                -> batch 2
                -> ...

        The caller can immediately load each batch into the
        database before generating the next batch.
        """

        if batch_size < 1:
            raise ValueError(
                "batch_size must be at least 1."
            )

        for transaction_date in self._date_range(
            start_date,
            end_date,
        ):

            for payments in self.generate_day_batches(
                transaction_date,
                batch_size=batch_size,
            ):

                yield (
                    transaction_date,
                    payments,
                )

    # ------------------------------------------------------------------
    # Volume preview
    # ------------------------------------------------------------------

    def preview_volumes(
        self,
        start_date: date,
        end_date: date,
    ) -> Iterator[tuple[date, int]]:
        """
        Preview expected daily transaction volumes without
        generating payment journeys.
        """

        for transaction_date in self._date_range(
            start_date,
            end_date,
        ):

            volume = self.get_daily_volume(
                transaction_date
            )

            yield (
                transaction_date,
                volume,
            )