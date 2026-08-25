from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta


BATCH_MONTHS = 6


def add_months(value: date, months: int) -> date:
    """
    Add a number of calendar months while preserving the day
    where possible.
    """

    if months < 0:
        raise ValueError("months must be non-negative.")

    total_months = (
        value.year * 12
        + (value.month - 1)
        + months
    )

    year = total_months // 12
    month = (total_months % 12) + 1

    day = min(
        value.day,
        monthrange(year, month)[1],
    )

    return date(
        year,
        month,
        day,
    )


def get_batch_end_date(
    start_date: date,
    target_end_date: date,
    batch_months: int = BATCH_MONTHS,
) -> date:
    """
    Calculate the final date for the next batch.

    The configured target_end_date is always the hard boundary.
    """

    if batch_months < 1:
        raise ValueError(
            "batch_months must be at least 1."
        )

    if target_end_date < start_date:
        raise ValueError(
            "target_end_date cannot be before start_date."
        )

    month_start = date(
        start_date.year,
        start_date.month,
        1,
    )

    next_month_after_batch = add_months(
        month_start,
        batch_months,
    )

    batch_end = (
        next_month_after_batch
        - timedelta(days=1)
    )

    return min(
        batch_end,
        target_end_date,
    )


def get_next_batch(
    next_start_date: date,
    target_end_date: date,
    batch_months: int = BATCH_MONTHS,
) -> tuple[date, date] | None:
    """
    Return the next simulation batch.

    Returns None when the target period has already
    been completely generated.
    """

    if next_start_date > target_end_date:
        return None

    return (
        next_start_date,
        get_batch_end_date(
            start_date=next_start_date,
            target_end_date=target_end_date,
            batch_months=batch_months,
        ),
    )