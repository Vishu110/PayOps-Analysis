from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP


MONEY_QUANTUM = Decimal("0.01")


def _round_money(value: Decimal) -> Decimal:
    """
    Round a monetary value to two decimal places.

    Financial calculations use Decimal throughout and apply
    ROUND_HALF_UP for deterministic currency rounding.
    """

    return value.quantize(
        MONEY_QUANTUM,
        rounding=ROUND_HALF_UP,
    )


def add_business_days(
    transaction_date: date,
    business_days: int,
) -> date:
    """
    Add a number of Monday-Friday business days to a date.

    Settlement assumptions:

        - Monday-Friday are business days.
        - Saturday and Sunday are non-business days.
        - Country-specific holidays are not modeled.
        - T+0 returns the transaction date unchanged.

    Args:
        transaction_date:
            Starting transaction date.

        business_days:
            Number of business days to add.
            Must be zero or greater.

    Returns:
        The resulting settlement date.

    Raises:
        TypeError:
            If transaction_date is not a date or business_days
            is not an integer.

        ValueError:
            If business_days is negative.
    """

    if not isinstance(
        transaction_date,
        date,
    ):
        raise TypeError(
            "transaction_date must be a date."
        )

    if not isinstance(
        business_days,
        int,
    ):
        raise TypeError(
            "business_days must be an integer."
        )

    if business_days < 0:
        raise ValueError(
            "business_days cannot be negative."
        )

    if business_days == 0:
        return transaction_date

    current_date = transaction_date
    days_added = 0

    while days_added < business_days:

        current_date += timedelta(
            days=1
        )

        if current_date.weekday() < 5:
            days_added += 1

    return current_date


def calculate_expected_settlement(
    candidate: dict,
) -> dict:
    """
    Calculate the internal expected settlement for one
    settlement candidate.

    This function performs only deterministic settlement
    calculations. It does not access the database and does
    not generate processor-reported settlement data.

    Required candidate fields:

        transaction_id
        simulation_date
        merchant_id
        settlement_cycle
        processor_id
        amount
        currency
        processor_fee_percentage
        fx_rate

    Returns:
        Dictionary containing the original identifying
        attributes plus calculated expected settlement values.
    """

    required_fields = (
        "transaction_id",
        "simulation_date",
        "merchant_id",
        "settlement_cycle",
        "processor_id",
        "amount",
        "currency",
        "processor_fee_percentage",
        "fx_rate",
    )

    missing_fields = [
        field
        for field in required_fields
        if field not in candidate
    ]

    if missing_fields:
        raise ValueError(
            "Settlement candidate is missing "
            f"required fields: {missing_fields}"
        )

    transaction_date = candidate[
        "simulation_date"
    ]

    settlement_cycle = candidate[
        "settlement_cycle"
    ]

    amount = Decimal(
        str(candidate["amount"])
    )

    fx_rate = Decimal(
        str(candidate["fx_rate"])
    )

    fee_percentage = Decimal(
        str(
            candidate[
                "processor_fee_percentage"
            ]
        )
    )

    if amount <= 0:
        raise ValueError(
            "Transaction amount must be greater than zero."
        )

    if fx_rate <= 0:
        raise ValueError(
            "FX rate must be greater than zero."
        )

    if fee_percentage < 0:
        raise ValueError(
            "Processor fee percentage cannot be negative."
        )

    if fee_percentage > 100:
        raise ValueError(
            "Processor fee percentage cannot exceed 100."
        )

    expected_settlement_date = (
        add_business_days(
            transaction_date,
            settlement_cycle,
        )
    )

    gross_amount_usd = _round_money(
        amount * fx_rate
    )

    fee_amount_usd = _round_money(
        gross_amount_usd
        * fee_percentage
        / Decimal("100")
    )

    net_amount_usd = _round_money(
        gross_amount_usd
        - fee_amount_usd
    )

    return {
        "transaction_id":
            candidate["transaction_id"],

        "merchant_id":
            candidate["merchant_id"],

        "processor_id":
            candidate["processor_id"],

        "transaction_date":
            transaction_date,

        "expected_settlement_date":
            expected_settlement_date,

        "gross_amount_usd":
            gross_amount_usd,

        "fee_amount_usd":
            fee_amount_usd,

        "net_amount_usd":
            net_amount_usd,

        "settlement_currency":
            "USD",

        "original_amount":
            amount,

        "original_currency":
            candidate["currency"],

        "fx_rate":
            fx_rate,

        "processor_fee_percentage":
            fee_percentage,

        "settlement_cycle":
            settlement_cycle,
    }


def calculate_expected_settlements(
    candidates: list[dict],
) -> list[dict]:
    """
    Calculate expected settlements for a collection of
    settlement candidates.

    Candidates are processed independently and in their
    supplied order.

    Args:
        candidates:
            Settlement candidate dictionaries.

    Returns:
        List of expected settlement dictionaries.
    """

    return [
        calculate_expected_settlement(
            candidate
        )
        for candidate in candidates
    ]