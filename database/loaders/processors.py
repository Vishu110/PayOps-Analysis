from psycopg2.extras import Json

from database.connection import get_connection


PROCESSOR_INSERT_SQL = """
INSERT INTO processors (
    processor_id,
    processor_name,
    headquarters_country_code,
    headquarters_country_name,
    supported_regions,
    supported_card_networks,
    default_processing_fee_percentage,
    processor_status
)
VALUES (
    %(processor_id)s,
    %(processor_name)s,
    %(headquarters_country_code)s,
    %(headquarters_country_name)s,
    %(supported_regions)s,
    %(supported_card_networks)s,
    %(default_processing_fee_percentage)s,
    %(processor_status)s
);
"""


def load_processors(processors: list[dict]) -> int:
    """
    Insert generated processor records into PostgreSQL.
    """

    if not processors:
        return 0

    records = []

    for processor in processors:
        record = processor.copy()

        record["supported_regions"] = Json(
            processor["supported_regions"]
        )

        record["supported_card_networks"] = Json(
            processor["supported_card_networks"]
        )
        records.append(record)

    connection = get_connection()
    try:
        with connection.cursor() as cursor:

            cursor.executemany(
                PROCESSOR_INSERT_SQL,
                records,
            )
        connection.commit()
        return len(records)

    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def fetch_processors() -> list[dict]:
    """
    Fetch existing processors from PostgreSQL.

    These records are used as dependencies by
    downstream master-data generators.
    """

    query = """
        SELECT
            id,
            processor_id,
            processor_name,
            headquarters_country_code,
            supported_regions,
            supported_card_networks,
            default_processing_fee_percentage,
            processor_status
        FROM processors
        ORDER BY id;
    """

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            cursor.execute(query)

            rows = cursor.fetchall()

            columns = [
                "id",
                "processor_id",
                "processor_name",
                "headquarters_country_code",
                "supported_regions",
                "supported_card_networks",
                "default_processing_fee_percentage",
                "processor_status",
            ]

            return [
                dict(zip(columns, row))
                for row in rows
            ]

    finally:

        connection.close()