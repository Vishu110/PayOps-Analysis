from database.connection import get_connection

connection = get_connection()

try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_database();")
        database_name = cursor.fetchone()[0]

        print(
            f"Successfully connected to PostgreSQL"
            f"database: {database_name}"
        )

finally:
    connection.close()