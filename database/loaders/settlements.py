from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict
from decimal import Decimal

from psycopg2.extras import execute_values

from database.connection import get_connection


class SettlementLoader:
    """
    Persist processor settlement batches and settlement entries.

    The simulation/business logic is performed upstream.

    This loader is responsible only for:
        1. Resolving processor business IDs to database IDs.
        2. Creating settlement batches when they do not already exist.
        3. Reusing existing settlement batches when appropriate.
        4. Creating settlement entries.
        5. Maintaining parent-child relationships.
        6. Maintaining batch aggregate totals.
        7. Supporting atomic database persistence.

    Transaction ownership:

        By default, load_batch() creates and commits its own
        database transaction.

        When an existing database connection is supplied,
        the caller owns the transaction. This is required by
        the settlement simulation runner so that checkpoint
        updates and settlement inserts can be committed
        atomically.

    Insert/update order:

        settlement_batches
                ↓
        settlement_entries
                ↓
        settlement_batches aggregate update
    """

    def __init__(self, connection=None):
        """
        Initialize the settlement loader.

        Args:
            connection:
                Optional existing PostgreSQL connection.

                If supplied, the caller owns the transaction.

                If omitted, load_batch() creates and commits
                its own connection.
        """

        self.connection = connection

    # ------------------------------------------------------------------
    # Batch loading
    # ------------------------------------------------------------------

    def load_batch(
        self,
        processor_entries: list,
    ) -> dict:
        """
        Persist a collection of processor settlement entries.

        Existing logical settlement batches are reused.

        A logical batch is identified by:

            processor_fk
            settlement_date
            settlement_currency

        This allows multiple simulation/transaction dates to contribute
        entries to the same processor settlement batch.

        Args:
            processor_entries:
                A list of ProcessorSettlementEntry objects generated
                by simulator.settlements.processor_feed.

        Returns:
            Dictionary containing persistence statistics.

        Raises:
            ValueError:
                If processor_entries is empty or contains invalid data.

            RuntimeError:
                If processor resolution or database ID mapping fails.
        """

        if not processor_entries:
            raise ValueError(
                "processor_entries cannot be empty."
            )

        owns_connection = self.connection is None

        connection = (
            get_connection()
            if owns_connection
            else self.connection
        )

        try:
            with connection.cursor() as cursor:

                # ======================================================
                # 1. Resolve processor business IDs
                # ======================================================

                processor_ids = sorted(
                    {
                        entry.processor_id
                        for entry in processor_entries
                    }
                )

                cursor.execute(
                    """
                    SELECT
                        id,
                        processor_id
                    FROM processors
                    WHERE processor_id = ANY(%s)
                    ORDER BY id;
                    """,
                    (processor_ids,),
                )

                processor_rows = cursor.fetchall()

                processor_id_map = {
                    processor_id: database_id
                    for (
                        database_id,
                        processor_id,
                    ) in processor_rows
                }

                missing_processors = [
                    processor_id
                    for processor_id in processor_ids
                    if processor_id not in processor_id_map
                ]

                if missing_processors:
                    raise RuntimeError(
                        "Settlement feed contains processor IDs "
                        "that do not exist in the processors table: "
                        f"{missing_processors}"
                    )

                # ======================================================
                # 2. Normalize and validate processor entries
                # ======================================================

                normalized_entries = []

                for entry in processor_entries:

                    if hasattr(
                        entry,
                        "__dataclass_fields__",
                    ):
                        entry_data = asdict(entry)

                    elif isinstance(
                        entry,
                        dict,
                    ):
                        entry_data = entry.copy()

                    else:
                        raise TypeError(
                            "Each processor settlement entry must be "
                            "a dataclass instance or dictionary."
                        )

                    required_fields = (
                        "settlement_entry_id",
                        "merchant_reference",
                        "processor_transaction_reference",
                        "processor_id",
                        "transaction_date",
                        "expected_settlement_date",
                        "actual_settlement_date",
                        "settlement_currency",
                        "gross_amount_usd",
                        "fee_amount_usd",
                        "net_amount_usd",
                        "processor_status",
                        "journal_type",
                    )

                    missing_fields = [
                        field
                        for field in required_fields
                        if field not in entry_data
                    ]

                    if missing_fields:
                        raise ValueError(
                            "Processor settlement entry is missing "
                            "required fields: "
                            f"{missing_fields}"
                        )

                    processor_id = entry_data[
                        "processor_id"
                    ]

                    if processor_id not in processor_id_map:
                        raise RuntimeError(
                            "Processor ID could not be resolved: "
                            f"{processor_id}"
                        )

                    gross_amount = Decimal(
                        str(
                            entry_data[
                                "gross_amount_usd"
                            ]
                        )
                    )

                    fee_amount = Decimal(
                        str(
                            entry_data[
                                "fee_amount_usd"
                            ]
                        )
                    )

                    net_amount = Decimal(
                        str(
                            entry_data[
                                "net_amount_usd"
                            ]
                        )
                    )

                    # --------------------------------------------------
                    # Financial integrity
                    # --------------------------------------------------

                    if gross_amount < 0:
                        raise ValueError(
                            "Settlement gross amount cannot be negative: "
                            f"{entry_data['settlement_entry_id']}"
                        )

                    if fee_amount < 0:
                        raise ValueError(
                            "Settlement fee amount cannot be negative: "
                            f"{entry_data['settlement_entry_id']}"
                        )

                    if fee_amount > gross_amount:
                        raise ValueError(
                            "Settlement fee cannot exceed gross amount: "
                            f"{entry_data['settlement_entry_id']}"
                        )

                    if net_amount < 0:
                        raise ValueError(
                            "Settlement net amount cannot be negative: "
                            f"{entry_data['settlement_entry_id']}"
                        )

                    if net_amount != (
                        gross_amount - fee_amount
                    ):
                        raise ValueError(
                            "Settlement arithmetic is invalid: "
                            f"{entry_data['settlement_entry_id']}"
                        )

                    # --------------------------------------------------
                    # Date integrity
                    # --------------------------------------------------

                    if (
                        entry_data[
                            "actual_settlement_date"
                        ]
                        < entry_data[
                            "transaction_date"
                        ]
                    ):
                        raise ValueError(
                            "Actual settlement date cannot be before "
                            "transaction date: "
                            f"{entry_data['settlement_entry_id']}"
                        )

                    expected_date = entry_data[
                        "expected_settlement_date"
                    ]

                    if (
                        expected_date is not None
                        and expected_date
                        < entry_data[
                            "transaction_date"
                        ]
                    ):
                        raise ValueError(
                            "Expected settlement date cannot be before "
                            "transaction date: "
                            f"{entry_data['settlement_entry_id']}"
                        )

                    if (
                        entry_data[
                            "settlement_currency"
                        ]
                        != "USD"
                    ):
                        raise ValueError(
                            "Settlement currency must be USD: "
                            f"{entry_data['settlement_entry_id']}"
                        )

                    normalized_entries.append(
                        {
                            **entry_data,
                            "processor_fk":
                                processor_id_map[
                                    processor_id
                                ],
                            "gross_amount_usd":
                                gross_amount,
                            "fee_amount_usd":
                                fee_amount,
                            "net_amount_usd":
                                net_amount,
                        }
                    )

                # ======================================================
                # 3. Detect duplicate settlement identifiers
                # ======================================================

                settlement_entry_ids = [
                    entry[
                        "settlement_entry_id"
                    ]
                    for entry in normalized_entries
                ]

                if len(
                    settlement_entry_ids
                ) != len(
                    set(
                        settlement_entry_ids
                    )
                ):
                    raise ValueError(
                        "Duplicate settlement_entry_id values "
                        "were found in the processor feed."
                    )

                processor_references = [
                    (
                        entry[
                            "processor_fk"
                        ],
                        entry[
                            "processor_transaction_reference"
                        ],
                    )
                    for entry in normalized_entries
                ]

                if len(
                    processor_references
                ) != len(
                    set(
                        processor_references
                    )
                ):
                    raise ValueError(
                        "Duplicate processor transaction references "
                        "were found in the processor feed."
                    )

                # ======================================================
                # 4. Group entries into logical settlement batches
                # ======================================================

                batch_groups = defaultdict(list)

                for entry in normalized_entries:

                    batch_key = (
                        entry[
                            "processor_fk"
                        ],
                        entry[
                            "actual_settlement_date"
                        ],
                        entry[
                            "settlement_currency"
                        ],
                    )

                    batch_groups[
                        batch_key
                    ].append(entry)

                # ======================================================
                # 5. Resolve existing batches
                # ======================================================

                batch_keys = list(batch_groups.keys())

                existing_batch_map = {}

                if batch_keys:
                    processors = sorted(
                        {
                            processor_fk
                            for (
                                processor_fk,
                                _,
                                _,
                            ) in batch_keys
                        }
                    )

                    settlement_dates = sorted(
                        {
                            settlement_date
                            for (
                                _,
                                settlement_date,
                                _,
                            ) in batch_keys
                        }
                    )

                    currencies = sorted(
                        {
                            settlement_currency
                            for (
                                _,
                                _,
                                settlement_currency,
                            ) in batch_keys
                        }
                    )

                    cursor.execute(
                        """
                        SELECT
                            id,
                            processor_fk,
                            settlement_date,
                            settlement_currency,
                            settlement_batch_id
                        FROM settlement_batches
                        WHERE processor_fk = ANY(%s)
                          AND settlement_date = ANY(%s)
                          AND settlement_currency = ANY(%s)
                        ORDER BY id;
                        """,
                        (
                            processors,
                            settlement_dates,
                            currencies,
                        ),
                    )

                    existing_batches = cursor.fetchall()

                    for row in existing_batches:
                        (
                            database_id,
                            processor_fk,
                            settlement_date,
                            settlement_currency,
                            settlement_batch_id,
                        ) = row

                        key = (
                            processor_fk,
                            settlement_date,
                            settlement_currency,
                        )

                        existing_batch_map[key] = {
                            "id": database_id,
                            "settlement_batch_id":
                                settlement_batch_id,
                        }

                # ======================================================
                # 6. Prepare only genuinely new settlement batches
                # ======================================================

                batch_rows = []
                batch_metadata = []

                for (
                    processor_fk,
                    settlement_date,
                    settlement_currency,
                ), entries in sorted(
                    batch_groups.items(),
                    key=lambda item: item[0],
                ):

                    processor_id = entries[0][
                        "processor_id"
                    ]

                    batch_key = (
                        processor_fk,
                        settlement_date,
                        settlement_currency,
                    )

                    existing_batch = existing_batch_map.get(
                        batch_key
                    )

                    if existing_batch is not None:
                        settlement_batch_id = (
                            existing_batch[
                                "settlement_batch_id"
                            ]
                        )
                    else:
                        settlement_batch_id = (
                            f"STB_"
                            f"{processor_id}_"
                            f"{settlement_date:%Y%m%d}_"
                            f"{settlement_currency}"
                        )

                        gross_amount_usd = sum(
                            (
                                entry[
                                    "gross_amount_usd"
                                ]
                                for entry in entries
                            ),
                            Decimal("0.00"),
                        )

                        fee_amount_usd = sum(
                            (
                                entry[
                                    "fee_amount_usd"
                                ]
                                for entry in entries
                            ),
                            Decimal("0.00"),
                        )

                        net_amount_usd = sum(
                            (
                                entry[
                                    "net_amount_usd"
                                ]
                                for entry in entries
                            ),
                            Decimal("0.00"),
                        )

                        batch_rows.append(
                            (
                                settlement_batch_id,
                                processor_fk,
                                settlement_date,
                                settlement_currency,
                                "SETTLED",
                                gross_amount_usd,
                                fee_amount_usd,
                                net_amount_usd,
                                len(entries),
                            )
                        )

                    batch_metadata.append(
                        (
                            batch_key,
                            settlement_batch_id,
                            entries,
                        )
                    )

                # ======================================================
                # 7. Bulk insert new settlement batches
                # ======================================================

                if batch_rows:

                    execute_values(
                        cursor,
                        """
                        INSERT INTO settlement_batches (
                            settlement_batch_id,
                            processor_fk,
                            settlement_date,
                            settlement_currency,
                            batch_status,
                            gross_amount_usd,
                            fee_amount_usd,
                            net_amount_usd,
                            entry_count
                        )
                        VALUES %s
                        RETURNING
                            id,
                            settlement_batch_id;
                        """,
                        batch_rows,
                        page_size=5000,
                    )

                    returned_batches = cursor.fetchall()

                    for (
                        database_id,
                        settlement_batch_id,
                    ) in returned_batches:

                        existing_batch_map_key = next(
                            (
                                key
                                for key, value
                                in (
                                    (
                                        batch_key,
                                        batch_value,
                                    )
                                    for (
                                        batch_key,
                                        batch_value,
                                    ) in existing_batch_map.items()
                                )
                                if value[
                                    "settlement_batch_id"
                                ] == settlement_batch_id
                            ),
                            None,
                        )

                        if existing_batch_map_key is None:
                            for (
                                batch_key,
                                generated_batch_id,
                                _,
                            ) in batch_metadata:

                                if (
                                    generated_batch_id
                                    == settlement_batch_id
                                ):
                                    existing_batch_map[
                                        batch_key
                                    ] = {
                                        "id": database_id,
                                        "settlement_batch_id":
                                            settlement_batch_id,
                                    }
                                    break

                # ======================================================
                # 8. Validate that every logical batch has a DB ID
                # ======================================================

                batch_id_map = {}

                for (
                    batch_key,
                    settlement_batch_id,
                    _,
                ) in batch_metadata:

                    batch_record = existing_batch_map.get(
                        batch_key
                    )

                    if batch_record is None:
                        raise RuntimeError(
                            "Settlement batch could not be resolved: "
                            f"{settlement_batch_id}"
                        )

                    batch_id_map[
                        settlement_batch_id
                    ] = batch_record["id"]

                # ======================================================
                # 9. Prepare settlement entries
                # ======================================================

                entry_rows = []

                for (
                    batch_key,
                    settlement_batch_id,
                    entries,
                ) in batch_metadata:

                    settlement_batch_fk = (
                        batch_id_map[
                            settlement_batch_id
                        ]
                    )

                    processor_fk = batch_key[0]

                    for entry in entries:

                        if (
                            entry[
                                "processor_fk"
                            ]
                            != processor_fk
                        ):
                            raise RuntimeError(
                                "Settlement entry processor does not "
                                "match settlement batch processor: "
                                f"{entry['settlement_entry_id']}"
                            )

                        entry_rows.append(
                            (
                                entry[
                                    "settlement_entry_id"
                                ],
                                settlement_batch_fk,
                                entry[
                                    "processor_fk"
                                ],
                                entry[
                                    "merchant_reference"
                                ],
                                entry[
                                    "processor_transaction_reference"
                                ],
                                entry[
                                    "journal_type"
                                ],
                                entry[
                                    "transaction_date"
                                ],
                                entry[
                                    "expected_settlement_date"
                                ],
                                entry[
                                    "actual_settlement_date"
                                ],
                                entry[
                                    "settlement_currency"
                                ],
                                entry[
                                    "gross_amount_usd"
                                ],
                                entry[
                                    "fee_amount_usd"
                                ],
                                entry[
                                    "net_amount_usd"
                                ],
                                entry[
                                    "processor_status"
                                ],
                            )
                        )

                # ======================================================
                # 10. Bulk insert settlement entries
                # ======================================================

                execute_values(
                    cursor,
                    """
                    INSERT INTO settlement_entries (
                        settlement_entry_id,
                        settlement_batch_fk,
                        processor_fk,
                        merchant_reference,
                        processor_transaction_reference,
                        journal_type,
                        transaction_date,
                        expected_settlement_date,
                        actual_settlement_date,
                        settlement_currency,
                        gross_amount_usd,
                        fee_amount_usd,
                        net_amount_usd,
                        processor_status
                    )
                    VALUES %s;
                    """,
                    entry_rows,
                    page_size=5000,
                )

                # ======================================================
                # 11. Update affected batch aggregates
                # ======================================================

                affected_batch_ids = sorted(
                    {
                        batch_id_map[
                            settlement_batch_id
                        ]
                        for (
                            _,
                            settlement_batch_id,
                            _,
                        ) in batch_metadata
                    }
                )

                if affected_batch_ids:

                    cursor.execute(
                        """
                        UPDATE settlement_batches AS sb
                        SET
                            gross_amount_usd = totals.gross_amount_usd,
                            fee_amount_usd = totals.fee_amount_usd,
                            net_amount_usd = totals.net_amount_usd,
                            entry_count = totals.entry_count
                        FROM (
                            SELECT
                                settlement_batch_fk,
                                SUM(gross_amount_usd) AS gross_amount_usd,
                                SUM(fee_amount_usd) AS fee_amount_usd,
                                SUM(net_amount_usd) AS net_amount_usd,
                                COUNT(*) AS entry_count
                            FROM settlement_entries
                            WHERE settlement_batch_fk = ANY(%s)
                            GROUP BY settlement_batch_fk
                        ) AS totals
                        WHERE sb.id = totals.settlement_batch_fk;
                        """,
                        (affected_batch_ids,),
                    )

                    if cursor.rowcount != len(
                        affected_batch_ids
                    ):
                        raise RuntimeError(
                            "Settlement batch aggregate update count "
                            "does not match affected batch count. "
                            f"Expected={len(affected_batch_ids)}, "
                            f"Updated={cursor.rowcount}."
                        )

                # ======================================================
                # 12. Commit only when this loader owns the connection
                # ======================================================

                if owns_connection:
                    connection.commit()

                return {
                    "batches":
                        len(batch_metadata),
                    "entries":
                        len(entry_rows),
                    "processors":
                        len(processor_id_map),
                }

        except Exception:

            if owns_connection:
                connection.rollback()

            raise

        finally:

            if owns_connection:
                connection.close()