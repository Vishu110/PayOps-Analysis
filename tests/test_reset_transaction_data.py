from database.connection import (
    get_connection,
)


def main():

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            tables = [
                "transactions",
                "payment_attempts",
                "payment_events",
                "customers",
                "merchants",
                "products",
                "payment_methods",
                "processors",
            ]

            print(
                "Current database record counts:"
            )

            print()

            for table in tables:

                cursor.execute(
                    f"SELECT COUNT(*) FROM {table};"
                )

                count = cursor.fetchone()[0]

                print(
                    f"{table}: {count:,}"
                )

    finally:
        connection.close()


if __name__ == "__main__":
    main()