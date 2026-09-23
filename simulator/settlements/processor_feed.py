from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP


MONEY_QUANTUM = Decimal("0.01")


# Synthetic scenario distribution.
#
# Bucket range: 0-9999
#
# AMOUNT_MISMATCH       13.70%
# MISSING_SETTLEMENT     8.10%
# TIMING_EXCEPTION       4.20%
# STATUS_MISMATCH        1.90%
# MATCHED                72.10%
#
# These are simulation assumptions, not real processor statistics.
SCENARIO_THRESHOLDS = (
    ("AMOUNT_MISMATCH", 1370),
    ("MISSING_SETTLEMENT", 2180),
    ("TIMING_EXCEPTION", 2600),
    ("STATUS_MISMATCH", 2790),
)


# Amount-mismatch subtype distribution.
#
# Bucket range: 0-999
#
# PROCESSOR_FEE_VARIANCE 21.3%
# PARTIAL_SETTLEMENT     31.4%
# FX_DIFFERENCE          19.7%
# ROUNDING_DIFFERENCE    16.8%
# UNEXPLAINED_DIFFERENCE 10.8%
AMOUNT_MISMATCH_SUBTYPES = (
    ("PROCESSOR_FEE_VARIANCE", 213),
    ("PARTIAL_SETTLEMENT", 527),
    ("FX_DIFFERENCE", 724),
    ("ROUNDING_DIFFERENCE", 892),
)


@dataclass(frozen=True)
class ProcessorSettlementEntry:
    """
    Synthetic processor-reported settlement entry.

    This represents the external processor feed, not the internal
    expected-settlement record.

    merchant_reference intentionally remains an external reconciliation
    key rather than a database foreign key.

    scenario and amount_mismatch_reason are simulation metadata. They
    help validate the generated population but should not be persisted
    as raw processor-feed columns.
    """

    settlement_entry_id: str
    merchant_reference: str
    processor_transaction_reference: str

    processor_id: str

    transaction_date: date
    expected_settlement_date: date
    actual_settlement_date: date

    settlement_currency: str

    gross_amount_usd: Decimal
    fee_amount_usd: Decimal
    net_amount_usd: Decimal

    processor_status: str
    journal_type: str

    scenario: str
    amount_mismatch_reason: str | None


def _round_money(value: Decimal) -> Decimal:
    """
    Round a monetary value to two decimal places using
    deterministic financial rounding.
    """

    return value.quantize(
        MONEY_QUANTUM,
        rounding=ROUND_HALF_UP,
    )


def _stable_bucket(
    transaction_id: str,
    seed: int,
    modulus: int,
) -> int:
    """
    Generate a deterministic integer bucket.

    Python's built-in hash() is intentionally avoided because its
    result can differ between processes. SHA-256 gives us stable
    scenario assignment across runs.
    """

    if modulus <= 0:
        raise ValueError(
            "modulus must be greater than zero."
        )

    payload = (
        f"{seed}:{transaction_id}"
    ).encode("utf-8")

    digest = hashlib.sha256(
        payload
    ).digest()

    value = int.from_bytes(
        digest[:8],
        byteorder="big",
        signed=False,
    )

    return value % modulus


def _select_scenario(
    transaction_id: str,
    seed: int,
) -> str:
    """
    Select a deterministic processor settlement scenario.
    """

    bucket = _stable_bucket(
        transaction_id,
        seed,
        10000,
    )

    for scenario, threshold in SCENARIO_THRESHOLDS:
        if bucket < threshold:
            return scenario

    return "MATCHED"


def _select_amount_mismatch_reason(
    transaction_id: str,
    seed: int,
) -> str:
    """
    Select a deterministic amount-mismatch subtype.
    """

    bucket = _stable_bucket(
        transaction_id,
        seed + 1,
        1000,
    )

    for reason, threshold in AMOUNT_MISMATCH_SUBTYPES:
        if bucket < threshold:
            return reason

    return "UNEXPLAINED_DIFFERENCE"


def _calculate_processor_amounts(
    expected: dict,
    reason: str,
) -> tuple[Decimal, Decimal, Decimal]:
    """
    Generate processor-reported financial amounts for an
    AMOUNT_MISMATCH scenario.

    The processor's normal fee percentage is taken from the expected
    settlement. Only PROCESSOR_FEE_VARIANCE deliberately changes the
    fee itself.

    Financial invariants:

        fee <= gross
        net = gross - fee
    """

    expected_gross = Decimal(
        str(
            expected[
                "gross_amount_usd"
            ]
        )
    )

    expected_fee = Decimal(
        str(
            expected[
                "fee_amount_usd"
            ]
        )
    )

    expected_fee_percentage = Decimal(
        str(
            expected[
                "processor_fee_percentage"
            ]
        )
    )

    if reason == "PROCESSOR_FEE_VARIANCE":

        settled_gross = expected_gross

        fee_variance = max(
            Decimal("0.02"),
            _round_money(
                expected_gross
                * Decimal("0.0015")
            ),
        )

        settled_fee = _round_money(
            expected_fee
            + fee_variance
        )

    elif reason == "PARTIAL_SETTLEMENT":

        settled_gross = _round_money(
            expected_gross
            * Decimal("0.75")
        )

        settled_fee = _round_money(
            settled_gross
            * expected_fee_percentage
            / Decimal("100")
        )

    elif reason == "FX_DIFFERENCE":

        gross_difference = max(
            Decimal("0.01"),
            _round_money(
                expected_gross
                * Decimal("0.002")
            ),
        )

        settled_gross = _round_money(
            expected_gross
            + gross_difference
        )

        settled_fee = _round_money(
            settled_gross
            * expected_fee_percentage
            / Decimal("100")
        )

    elif reason == "ROUNDING_DIFFERENCE":

        settled_gross = _round_money(
            expected_gross
            + Decimal("0.02")
        )

        settled_fee = _round_money(
            settled_gross
            * expected_fee_percentage
            / Decimal("100")
        )

    else:
        # UNEXPLAINED_DIFFERENCE
        gross_difference = max(
            Decimal("0.01"),
            _round_money(
                expected_gross
                * Decimal("0.01")
            ),
        )

        settled_gross = _round_money(
            expected_gross
            + gross_difference
        )

        settled_fee = _round_money(
            settled_gross
            * expected_fee_percentage
            / Decimal("100")
        )

    if settled_fee > settled_gross:
        settled_fee = settled_gross

    settled_net = _round_money(
        settled_gross
        - settled_fee
    )

    return (
        settled_gross,
        settled_fee,
        settled_net,
    )


def _add_one_business_day(
    settlement_date: date,
) -> date:
    """
    Add one Monday-Friday business day.

    Country-specific holidays are intentionally not modelled.
    """

    next_date = settlement_date + timedelta(
        days=1
    )

    while next_date.weekday() >= 5:
        next_date += timedelta(
            days=1
        )

    return next_date


def generate_processor_settlement(
    expected: dict,
    seed: int = 20260907,
) -> ProcessorSettlementEntry | None:
    """
    Generate one synthetic processor settlement-feed record.

    The function consumes an internal expected settlement and produces
    an independent processor-reported outcome.

    Missing settlements intentionally return None. No processor row is
    created in that scenario; reconciliation detects the absence.

    STATUS_MISMATCH is different: the processor does report a settlement
    row, but reports its status as REVERSED.

    Args:
        expected:
            Expected settlement dictionary produced by expected.py.

        seed:
            Stable seed controlling deterministic scenario assignment.

    Returns:
        ProcessorSettlementEntry for a reported processor record,
        or None for MISSING_SETTLEMENT.
    """

    required_fields = (
        "transaction_id",
        "processor_id",
        "transaction_date",
        "expected_settlement_date",
        "gross_amount_usd",
        "fee_amount_usd",
        "net_amount_usd",
        "settlement_currency",
        "processor_fee_percentage",
    )

    missing_fields = [
        field
        for field in required_fields
        if field not in expected
    ]

    if missing_fields:
        raise ValueError(
            "Expected settlement is missing required fields: "
            f"{missing_fields}"
        )

    transaction_id = expected[
        "transaction_id"
    ]

    processor_id = expected[
        "processor_id"
    ]

    transaction_date = expected[
        "transaction_date"
    ]

    expected_settlement_date = expected[
        "expected_settlement_date"
    ]

    settlement_currency = expected[
        "settlement_currency"
    ]

    scenario = _select_scenario(
        transaction_id,
        seed,
    )

    # --------------------------------------------------------------
    # Missing settlement
    # --------------------------------------------------------------
    #
    # The processor reports no settlement entry.
    #
    if scenario == "MISSING_SETTLEMENT":
        return None

    # --------------------------------------------------------------
    # Default: processor reports the expected settlement
    # --------------------------------------------------------------

    actual_settlement_date = (
        expected_settlement_date
    )

    gross_amount_usd = Decimal(
        str(
            expected[
                "gross_amount_usd"
            ]
        )
    )

    fee_amount_usd = Decimal(
        str(
            expected[
                "fee_amount_usd"
            ]
        )
    )

    net_amount_usd = Decimal(
        str(
            expected[
                "net_amount_usd"
            ]
        )
    )

    processor_status = "SETTLED"

    amount_mismatch_reason = None

    # --------------------------------------------------------------
    # Amount mismatch
    # --------------------------------------------------------------

    if scenario == "AMOUNT_MISMATCH":

        amount_mismatch_reason = (
            _select_amount_mismatch_reason(
                transaction_id,
                seed,
            )
        )

        (
            gross_amount_usd,
            fee_amount_usd,
            net_amount_usd,
        ) = _calculate_processor_amounts(
            expected,
            amount_mismatch_reason,
        )

    # --------------------------------------------------------------
    # Timing exception
    # --------------------------------------------------------------

    elif scenario == "TIMING_EXCEPTION":

        actual_settlement_date = (
            _add_one_business_day(
                expected_settlement_date
            )
        )

    # --------------------------------------------------------------
    # Status mismatch
    # --------------------------------------------------------------
    #
    # The processor still reports the settlement row and its
    # financial amounts, but its operational status is REVERSED.
    #
    elif scenario == "STATUS_MISMATCH":

        processor_status = "REVERSED"

    # --------------------------------------------------------------
    # External processor references
    # --------------------------------------------------------------

    processor_transaction_reference = (
        f"PSP_{processor_id}_{transaction_id}"
    )

    settlement_entry_id = (
        f"STE_{processor_id}_{transaction_id}"
    )

    return ProcessorSettlementEntry(
        settlement_entry_id=settlement_entry_id,
        merchant_reference=transaction_id,
        processor_transaction_reference=(
            processor_transaction_reference
        ),
        processor_id=processor_id,
        transaction_date=transaction_date,
        expected_settlement_date=(
            expected_settlement_date
        ),
        actual_settlement_date=(
            actual_settlement_date
        ),
        settlement_currency=settlement_currency,
        gross_amount_usd=gross_amount_usd,
        fee_amount_usd=fee_amount_usd,
        net_amount_usd=net_amount_usd,
        processor_status=processor_status,
        journal_type="SETTLED",
        scenario=scenario,
        amount_mismatch_reason=(
            amount_mismatch_reason
        ),
    )


def generate_processor_settlements(
    expected_settlements: list[dict],
    seed: int = 20260907,
) -> list[ProcessorSettlementEntry]:
    """
    Generate processor settlement-feed records for a collection
    of expected settlements.

    Missing settlements are omitted from the returned feed.

    The output preserves the order of the supplied expected
    settlements for deterministic testing.
    """

    processor_entries = []

    for expected in expected_settlements:

        entry = generate_processor_settlement(
            expected,
            seed=seed,
        )

        if entry is not None:
            processor_entries.append(
                entry
            )

    return processor_entries