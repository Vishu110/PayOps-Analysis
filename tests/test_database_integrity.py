from datetime import date

from database.connection import get_connection
from database.loaders.transactions import TransactionLoader


def run_query(cursor, query):
    cursor.execute(query)
    return cursor.fetchall()


# ==============================================================
# Transaction-level integrity
# ==============================================================

def validate_transactions(cursor):
    print("Validating transactions...")

    # ----------------------------------------------------------
    # Duplicate transaction IDs
    # ----------------------------------------------------------

    rows = run_query(
        cursor,
        """
        SELECT transaction_id, COUNT(*)
        FROM transactions
        GROUP BY transaction_id
        HAVING COUNT(*) > 1;
        """,
    )

    if rows:
        raise AssertionError(
            f"Duplicate transaction IDs found: {rows[:5]}"
        )

    # ----------------------------------------------------------
    # NULL simulation dates
    # ----------------------------------------------------------

    rows = run_query(
        cursor,
        """
        SELECT COUNT(*)
        FROM transactions
        WHERE simulation_date IS NULL;
        """,
    )

    null_count = rows[0][0]

    if null_count != 0:
        raise AssertionError(
            f"Transactions with NULL simulation_date: {null_count}"
        )

    # ----------------------------------------------------------
    # Invalid simulation dates
    # ----------------------------------------------------------

    rows = run_query(
        cursor,
        """
        SELECT COUNT(*)
        FROM transactions
        WHERE simulation_date < DATE '2023-01-01'
           OR simulation_date > DATE '2023-03-17';
        """,
    )

    invalid_date_count = rows[0][0]

    if invalid_date_count != 0:
        raise AssertionError(
            f"Transactions outside simulation period: "
            f"{invalid_date_count}"
        )

    # ----------------------------------------------------------
    # Initiated timestamp must belong to simulation date
    # in the customer's local timezone
    # ----------------------------------------------------------

    rows = run_query(
        cursor,
        """
        SELECT COUNT(*)
        FROM transactions t
        JOIN customers c
            ON t.customer_fk = c.id
        WHERE (
            t.initiated_at AT TIME ZONE c.timezone
        )::date <> t.simulation_date;
        """,
    )

    mismatch_count = rows[0][0]

    if mismatch_count != 0:
        raise AssertionError(
            "Transactions where initiated_at local date does not "
            f"match simulation_date: {mismatch_count}"
        )

    # ----------------------------------------------------------
    # Completion cannot occur before initiation
    # ----------------------------------------------------------

    rows = run_query(
        cursor,
        """
        SELECT COUNT(*)
        FROM transactions
        WHERE completed_at IS NOT NULL
          AND completed_at < initiated_at;
        """,
    )

    invalid_timestamp_count = rows[0][0]

    if invalid_timestamp_count != 0:
        raise AssertionError(
            "Transactions with completed_at before "
            f"initiated_at: {invalid_timestamp_count}"
        )

    # ----------------------------------------------------------
    # Invalid amount
    # ----------------------------------------------------------

    rows = run_query(
        cursor,
        """
        SELECT COUNT(*)
        FROM transactions
        WHERE amount <= 0;
        """,
    )

    invalid_amount_count = rows[0][0]

    if invalid_amount_count != 0:
        raise AssertionError(
            f"Transactions with non-positive amount: "
            f"{invalid_amount_count}"
        )

    # ----------------------------------------------------------
    # Invalid quantity
    # ----------------------------------------------------------

    rows = run_query(
        cursor,
        """
        SELECT COUNT(*)
        FROM transactions
        WHERE quantity < 1;
        """,
    )

    invalid_quantity_count = rows[0][0]

    if invalid_quantity_count != 0:
        raise AssertionError(
            f"Transactions with invalid quantity: "
            f"{invalid_quantity_count}"
        )

    print("  Transaction-level checks passed.")


# ==============================================================
# Referential integrity
# ==============================================================

def validate_referential_integrity(cursor):
    print("Validating referential integrity...")

    # ----------------------------------------------------------
    # Transaction → customer
    # ----------------------------------------------------------

    rows = run_query(
        cursor,
        """
        SELECT COUNT(*)
        FROM transactions t
        LEFT JOIN customers c
            ON c.id = t.customer_fk
        WHERE c.id IS NULL;
        """,
    )

    count = rows[0][0]

    if count != 0:
        raise AssertionError(
            f"Transactions with invalid customer_fk: {count}"
        )

    # ----------------------------------------------------------
    # Transaction → merchant
    # ----------------------------------------------------------

    rows = run_query(
        cursor,
        """
        SELECT COUNT(*)
        FROM transactions t
        LEFT JOIN merchants m
            ON m.id = t.merchant_fk
        WHERE m.id IS NULL;
        """,
    )

    count = rows[0][0]

    if count != 0:
        raise AssertionError(
            f"Transactions with invalid merchant_fk: {count}"
        )

    # ----------------------------------------------------------
    # Transaction → product
    # ----------------------------------------------------------

    rows = run_query(
        cursor,
        """
        SELECT COUNT(*)
        FROM transactions t
        LEFT JOIN products p
            ON p.id = t.product_fk
        WHERE p.id IS NULL;
        """,
    )

    count = rows[0][0]

    if count != 0:
        raise AssertionError(
            f"Transactions with invalid product_fk: {count}"
        )

    # ----------------------------------------------------------
    # Transaction → payment method
    # ----------------------------------------------------------

    rows = run_query(
        cursor,
        """
        SELECT COUNT(*)
        FROM transactions t
        LEFT JOIN payment_methods pm
            ON pm.id = t.payment_method_fk
        WHERE pm.id IS NULL;
        """,
    )

    count = rows[0][0]

    if count != 0:
        raise AssertionError(
            f"Transactions with invalid payment_method_fk: {count}"
        )

    # ----------------------------------------------------------
    # Payment attempt → transaction
    # ----------------------------------------------------------

    rows = run_query(
        cursor,
        """
        SELECT COUNT(*)
        FROM payment_attempts pa
        LEFT JOIN transactions t
            ON t.id = pa.transaction_fk
        WHERE t.id IS NULL;
        """,
    )

    count = rows[0][0]

    if count != 0:
        raise AssertionError(
            f"Payment attempts with invalid transaction_fk: {count}"
        )

    # ----------------------------------------------------------
    # Payment event → payment attempt
    # ----------------------------------------------------------

    rows = run_query(
        cursor,
        """
        SELECT COUNT(*)
        FROM payment_events pe
        LEFT JOIN payment_attempts pa
            ON pa.id = pe.payment_attempt_fk
        WHERE pa.id IS NULL;
        """,
    )

    count = rows[0][0]

    if count != 0:
        raise AssertionError(
            "Payment events with invalid payment_attempt_fk: "
            f"{count}"
        )

    print("  Referential integrity checks passed.")


# ==============================================================
# Payment attempt integrity
# ==============================================================

def validate_attempts(cursor):
    print("Validating payment attempts...")

    # ----------------------------------------------------------
    # Attempt numbers must be positive
    # ----------------------------------------------------------

    rows = run_query(
        cursor,
        """
        SELECT COUNT(*)
        FROM payment_attempts
        WHERE attempt_number < 1;
        """,
    )

    count = rows[0][0]

    if count != 0:
        raise AssertionError(
            f"Payment attempts with invalid attempt_number: {count}"
        )

    # ----------------------------------------------------------
    # Attempt timestamps
    # ----------------------------------------------------------

    rows = run_query(
        cursor,
        """
        SELECT COUNT(*)
        FROM payment_attempts
        WHERE completed_at IS NOT NULL
          AND completed_at < initiated_at;
        """,
    )

    count = rows[0][0]

    if count != 0:
        raise AssertionError(
            "Payment attempts with completed_at before "
            f"initiated_at: {count}"
        )

    # ----------------------------------------------------------
    # Attempt starts before transaction
    # ----------------------------------------------------------

    rows = run_query(
        cursor,
        """
        SELECT COUNT(*)
        FROM payment_attempts pa
        JOIN transactions t
            ON t.id = pa.transaction_fk
        WHERE pa.initiated_at < t.initiated_at;
        """,
    )

    count = rows[0][0]

    if count != 0:
        raise AssertionError(
            "Payment attempts starting before their "
            f"transaction: {count}"
        )

    # ----------------------------------------------------------
    # Failed attempts must have failure reason
    # ----------------------------------------------------------

    rows = run_query(
        cursor,
        """
        SELECT COUNT(*)
        FROM payment_attempts
        WHERE attempt_status = 'FAILED'
          AND failure_reason IS NULL;
        """,
    )

    count = rows[0][0]

    if count != 0:
        raise AssertionError(
            f"Failed attempts without failure_reason: {count}"
        )

    # ----------------------------------------------------------
    # Non-failed attempts must not have failure reason
    # ----------------------------------------------------------

    rows = run_query(
        cursor,
        """
        SELECT COUNT(*)
        FROM payment_attempts
        WHERE attempt_status <> 'FAILED'
          AND failure_reason IS NOT NULL;
        """,
    )

    count = rows[0][0]

    if count != 0:
        raise AssertionError(
            "Non-failed attempts with failure_reason: "
            f"{count}"
        )

    print("  Payment attempt checks passed.")


# ==============================================================
# Payment event integrity
# ==============================================================

def validate_events(cursor):
    print("Validating payment events...")

    # ----------------------------------------------------------
    # Sequence numbers must be positive
    # ----------------------------------------------------------

    rows = run_query(
        cursor,
        """
        SELECT COUNT(*)
        FROM payment_events
        WHERE sequence_number < 1;
        """,
    )

    count = rows[0][0]

    if count != 0:
        raise AssertionError(
            f"Events with invalid sequence_number: {count}"
        )

    # ----------------------------------------------------------
    # Events cannot occur before attempt initiation
    # ----------------------------------------------------------

    rows = run_query(
        cursor,
        """
        SELECT COUNT(*)
        FROM payment_events pe
        JOIN payment_attempts pa
            ON pa.id = pe.payment_attempt_fk
        WHERE pe.event_at < pa.initiated_at;
        """,
    )

    count = rows[0][0]

    if count != 0:
        raise AssertionError(
            "Events occurring before attempt initiation: "
            f"{count}"
        )

    # ----------------------------------------------------------
    # Events cannot occur after attempt completion
    # ----------------------------------------------------------

    rows = run_query(
        cursor,
        """
        SELECT COUNT(*)
        FROM payment_events pe
        JOIN payment_attempts pa
            ON pa.id = pe.payment_attempt_fk
        WHERE pe.event_at > pa.completed_at;
        """,
    )

    count = rows[0][0]

    if count != 0:
        raise AssertionError(
            "Events occurring after attempt completion: "
            f"{count}"
        )

    # ----------------------------------------------------------
    # Every attempt must have at least one event
    # ----------------------------------------------------------

    rows = run_query(
        cursor,
        """
        SELECT COUNT(*)
        FROM payment_attempts pa
        LEFT JOIN payment_events pe
            ON pe.payment_attempt_fk = pa.id
        WHERE pe.id IS NULL;
        """,
    )

    count = rows[0][0]

    if count != 0:
        raise AssertionError(
            f"Payment attempts without events: {count}"
        )

    # ----------------------------------------------------------
    # Final event must equal attempt completion
    # ----------------------------------------------------------

    rows = run_query(
        cursor,
        """
        SELECT COUNT(*)
        FROM payment_attempts pa
        JOIN (
            SELECT
                payment_attempt_fk,
                MAX(sequence_number) AS max_sequence
            FROM payment_events
            GROUP BY payment_attempt_fk
        ) last_event
            ON last_event.payment_attempt_fk = pa.id
        JOIN payment_events pe
            ON pe.payment_attempt_fk = pa.id
           AND pe.sequence_number = last_event.max_sequence
        WHERE pe.event_at <> pa.completed_at;
        """,
    )

    count = rows[0][0]

    if count != 0:
        raise AssertionError(
            "Final payment event does not match attempt "
            f"completion: {count}"
        )

    print("  Payment event checks passed.")


# ==============================================================
# Summary checks
# ==============================================================

def validate_summary(cursor):
    print("Validating database summary...")

    rows = run_query(
        cursor,
        """
        SELECT
            MIN(simulation_date),
            MAX(simulation_date),
            COUNT(*)
        FROM transactions;
        """,
    )

    first_date, latest_date, transaction_count = rows[0]

    if transaction_count == 0:
        raise AssertionError(
            "No transactions found in database."
        )

    print(
        f"  Transactions: {transaction_count:,}"
    )

    print(
        f"  Simulation period: "
        f"{first_date} → {latest_date}"
    )

    print("  Database summary checks passed.")


# ==============================================================
# Main
# ==============================================================

def main():

    print(
        "Starting database integrity validation..."
    )

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            validate_summary(cursor)

            validate_transactions(cursor)

            validate_referential_integrity(cursor)

            validate_attempts(cursor)

            validate_events(cursor)

    finally:

        connection.close()

    print()
    print(
        "All database integrity validation tests passed."
    )


if __name__ == "__main__":
    main()