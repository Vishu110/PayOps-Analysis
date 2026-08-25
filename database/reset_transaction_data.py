from database.connection import (
    get_connection,
)

def reset_transaction_data():
    """
    Delete all generated transactional data while preserving
    reference/dependency tables.

    Delete order:

        payment_events
            ↓
        payment_attempts
            ↓
        transactions
    """

    connection = get_connection()

    try:
        connection.autocommit = False

        with connection.cursor() as cursor:

            print(
                "Starting transaction data reset..."
            )

            # --------------------------------------------------
            # 1. Delete payment events
            # --------------------------------------------------

            cursor.execute(
                "DELETE FROM payment_events;"
            )

            deleted_events = cursor.rowcount

            print(
                f"Deleted payment events: "
                f"{deleted_events:,}"
            )

            # --------------------------------------------------
            # 2. Delete payment attempts
            # --------------------------------------------------

            cursor.execute(
                "DELETE FROM payment_attempts;"
            )

            deleted_attempts = cursor.rowcount

            print(
                f"Deleted payment attempts: "
                f"{deleted_attempts:,}"
            )

            # --------------------------------------------------
            # 3. Delete transactions
            # --------------------------------------------------

            cursor.execute(
                "DELETE FROM transactions;"
            )

            deleted_transactions = cursor.rowcount

            print(
                f"Deleted transactions: "
                f"{deleted_transactions:,}"
            )

            # --------------------------------------------------
            # Commit
            # --------------------------------------------------

            connection.commit()

            print()
            print(
                "Transaction data reset completed "
                "successfully."
            )

    except Exception:

        connection.rollback()

        print()
        print(
            "Transaction data reset failed."
        )

        raise

    finally:
        connection.close()


if __name__ == "__main__":
    reset_transaction_data()