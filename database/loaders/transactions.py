import secrets

from psycopg2.extras import execute_values

from database.connection import get_connection


class TransactionLoader:
    """
    Persist complete simulated payment journeys.

    Insert order:

        transactions
            ↓
        payment_attempts
            ↓
        payment_events

    The simulation/business logic is NOT performed here.

    This class is responsible only for efficient persistence.

    Batch loading uses PostgreSQL execute_values() to reduce the
    number of database round trips while preserving the required
    foreign-key relationships.
    """

    # ------------------------------------------------------------------
    # Single payment loader
    # ------------------------------------------------------------------

    def load_payment(
        self,
        payment: dict,
    ) -> dict:
        """
        Persist one complete payment journey.

        This method is retained for compatibility with existing tests
        or callers. Large simulations should use load_batch().
        """

        transaction = payment[
            "transaction"
        ]

        attempts = payment[
            "attempts"
        ]

        connection = get_connection()

        try:
            with connection.cursor() as cursor:

                # ------------------------------------------------------
                # 1. Transaction
                # ------------------------------------------------------

                cursor.execute(
                    """
                    INSERT INTO transactions (
                        transaction_id,
                        customer_fk,
                        merchant_fk,
                        product_fk,
                        payment_method_fk,
                        transaction_type,
                        amount,
                        currency,
                        quantity,
                        current_status,
                        initiated_at,
                        completed_at
                    )
                    VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s
                    )
                    RETURNING id
                    """,
                    (
                        transaction[
                            "transaction_id"
                        ],
                        transaction[
                            "customer_fk"
                        ],
                        transaction[
                            "merchant_fk"
                        ],
                        transaction[
                            "product_fk"
                        ],
                        transaction[
                            "payment_method_fk"
                        ],
                        transaction[
                            "transaction_type"
                        ],
                        transaction[
                            "amount"
                        ],
                        transaction[
                            "currency"
                        ],
                        transaction[
                            "quantity"
                        ],
                        transaction[
                            "current_status"
                        ],
                        transaction[
                            "initiated_at"
                        ],
                        transaction[
                            "completed_at"
                        ],
                    ),
                )

                transaction_db_id = (
                    cursor.fetchone()[0]
                )

                # ------------------------------------------------------
                # 2. Attempts
                # ------------------------------------------------------

                attempt_count = 0
                event_count = 0

                for attempt in attempts:

                    processor = attempt[
                        "processor"
                    ]

                    attempt_id = (
                        self._generate_attempt_id()
                    )

                    cursor.execute(
                        """
                        INSERT INTO payment_attempts (
                            attempt_id,
                            transaction_fk,
                            attempt_number,
                            processor_fk,
                            attempt_status,
                            failure_reason,
                            initiated_at,
                            completed_at
                        )
                        VALUES (
                            %s, %s, %s, %s,
                            %s, %s, %s, %s
                        )
                        RETURNING id
                        """,
                        (
                            attempt_id,
                            transaction_db_id,
                            attempt[
                                "attempt_number"
                            ],
                            processor["id"],
                            attempt[
                                "attempt_status"
                            ],
                            attempt[
                                "failure_reason"
                            ],
                            attempt[
                                "initiated_at"
                            ],
                            attempt[
                                "completed_at"
                            ],
                        ),
                    )

                    attempt_db_id = (
                        cursor.fetchone()[0]
                    )

                    attempt_count += 1

                    # --------------------------------------------------
                    # 3. Events
                    # --------------------------------------------------

                    for event in attempt[
                        "events"
                    ]:

                        cursor.execute(
                            """
                            INSERT INTO payment_events (
                                event_id,
                                payment_attempt_fk,
                                event_status,
                                event_at,
                                sequence_number
                            )
                            VALUES (
                                %s, %s, %s, %s, %s
                            )
                            """,
                            (
                                self._generate_event_id(),
                                attempt_db_id,
                                event[
                                    "event_status"
                                ],
                                event[
                                    "event_at"
                                ],
                                event[
                                    "sequence_number"
                                ],
                            ),
                        )

                        event_count += 1

            connection.commit()

            return {
                "transaction_id":
                    transaction[
                        "transaction_id"
                    ],

                "transaction_db_id":
                    transaction_db_id,

                "attempt_count":
                    attempt_count,

                "event_count":
                    event_count,
            }

        except Exception:
            connection.rollback()
            raise

        finally:
            connection.close()

    # ------------------------------------------------------------------
    # ID generation
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_attempt_id():

        return (
            "att_"
            + secrets.token_urlsafe(18)
        )

    @staticmethod
    def _generate_event_id():

        return (
            "evt_"
            + secrets.token_urlsafe(18)
        )

    # ------------------------------------------------------------------
    # Batch loader
    # ------------------------------------------------------------------

    def load_batch(
        self,
        payments: list[dict],
    ) -> dict:
        """
        Persist multiple complete payment journeys.

        Optimized for large simulations.

        Strategy:

            1. Bulk insert transactions
            2. Retrieve generated database IDs
            3. Bulk insert payment attempts
            4. Retrieve generated attempt database IDs
            5. Bulk insert payment events
            6. Commit once

        The entire batch is atomic.

        If anything fails, the entire batch is rolled back.
        """

        if not payments:
            raise ValueError(
                "payments cannot be empty."
            )

        connection = get_connection()

        transaction_count = 0
        attempt_count = 0
        event_count = 0

        captured_count = 0
        failed_count = 0
        canceled_count = 0
        retried_count = 0
        cross_border_count = 0

        try:

            with connection.cursor() as cursor:

                # ======================================================
                # 1. Prepare transactions
                # ======================================================

                transaction_rows = []

                for payment in payments:

                    transaction = payment[
                        "transaction"
                    ]

                    simulation_date = transaction[
                        "simulation_date"
                    ]

                    initiated_at = transaction[
                        "initiated_at"
                    ]

                    completed_at = transaction[
                        "completed_at"
                    ]

                    # --------------------------------------------------
                    # Historical timestamp validation
                    # --------------------------------------------------
                    #
                    # A completed transaction cannot finish before
                    # it was initiated.
                    #
                    # We intentionally FAIL the batch instead of
                    # silently modifying the generated data.
                    # This protects the business rules and makes
                    # simulation errors visible.
                    # --------------------------------------------------

                    if (
                        completed_at is not None
                        and completed_at < initiated_at
                    ):
                        raise ValueError(
                            "Invalid transaction timestamps: "
                            f"transaction_id="
                            f"{transaction['transaction_id']}, "
                            f"initiated_at={initiated_at}, "
                            f"completed_at={completed_at}"
                        )

                    # --------------------------------------------------
                    # updated_at
                    # --------------------------------------------------
                    #
                    # For historical simulation data we don't want
                    # PostgreSQL's CURRENT_TIMESTAMP as updated_at.
                    #
                    # Use the transaction's own historical completion
                    # timestamp when available. For transactions
                    # without a completion timestamp, use initiated_at.
                    # --------------------------------------------------

                    updated_at = (
                        completed_at
                        if completed_at is not None
                        else initiated_at
                    )

                    transaction_rows.append(
                        (
                            transaction[
                                "transaction_id"
                            ],
                            transaction[
                                "customer_fk"
                            ],
                            transaction[
                                "merchant_fk"
                            ],
                            transaction[
                                "product_fk"
                            ],
                            transaction[
                                "payment_method_fk"
                            ],
                            transaction[
                                "transaction_type"
                            ],
                            transaction[
                                "amount"
                            ],
                            transaction[
                                "currency"
                            ],
                            transaction[
                                "quantity"
                            ],
                            transaction[
                                "current_status"
                            ],
                            simulation_date,
                            initiated_at,
                            completed_at,
                            updated_at,
                        )
                    )

                # ======================================================
                # 2. Bulk insert transactions
                # ======================================================

                execute_values(
                    cursor,
                    """
                    INSERT INTO transactions (
                        transaction_id,
                        customer_fk,
                        merchant_fk,
                        product_fk,
                        payment_method_fk,
                        transaction_type,
                        amount,
                        currency,
                        quantity,
                        current_status,
                        simulation_date,
                        initiated_at,
                        completed_at,
                        updated_at
                    )
                    VALUES %s
                    RETURNING id, transaction_id
                    """,
                    transaction_rows,
                    page_size=5000,
                )

                returned_transactions = (
                    cursor.fetchall()
                )

                # ------------------------------------------------------
                # Build transaction_id → database ID mapping
                # ------------------------------------------------------

                transaction_id_map = {
                    transaction_id:
                        database_id
                    for (
                        database_id,
                        transaction_id,
                    ) in returned_transactions
                }

                if len(
                    transaction_id_map
                ) != len(payments):

                    raise RuntimeError(
                        "Transaction ID mapping count "
                        "does not match generated "
                        "payment count."
                    )

                transaction_count = (
                    len(payments)
                )

                # ======================================================
                # 3. Calculate transaction-level statistics
                # ======================================================

                for payment in payments:

                    final_status = payment[
                        "final_status"
                    ]

                    if final_status == "CAPTURED":
                        captured_count += 1

                    elif final_status == "FAILED":
                        failed_count += 1

                    elif final_status == "CANCELED":
                        canceled_count += 1

                    attempts = payment[
                        "attempts"
                    ]

                    if len(attempts) > 1:
                        retried_count += 1

                    context = payment.get(
                        "context"
                    )

                    if context:

                        customer_country = (
                            context[
                                "customer"
                            ].get(
                                "country_code"
                            )
                        )

                        merchant_country = (
                            context[
                                "merchant"
                            ].get(
                                "country_code"
                            )
                        )

                        if (
                            customer_country
                            and merchant_country
                            and customer_country
                            != merchant_country
                        ):
                            cross_border_count += 1

                # ======================================================
                # 4. Prepare payment attempts
                # ======================================================

                attempt_rows = []

                # Keep enough information to map the returned
                # database attempt ID back to its events.

                attempt_metadata = []

                for payment in payments:

                    transaction = payment[
                        "transaction"
                    ]

                    transaction_id = transaction[
                        "transaction_id"
                    ]

                    transaction_db_id = (
                        transaction_id_map[
                            transaction_id
                        ]
                    )

                    for attempt in payment[
                        "attempts"
                    ]:

                        processor = attempt[
                            "processor"
                        ]

                        attempt_id = (
                            self._generate_attempt_id()
                        )

                        attempt_rows.append(
                            (
                                attempt_id,
                                transaction_db_id,
                                attempt[
                                    "attempt_number"
                                ],
                                processor[
                                    "id"
                                ],
                                attempt[
                                    "attempt_status"
                                ],
                                attempt[
                                    "failure_reason"
                                ],
                                attempt[
                                    "initiated_at"
                                ],
                                attempt[
                                    "completed_at"
                                ],
                            )
                        )

                        attempt_metadata.append(
                            (
                                attempt_id,
                                attempt,
                            )
                        )

                # ======================================================
                # 5. Bulk insert attempts
                # ======================================================

                if attempt_rows:

                    execute_values(
                        cursor,
                        """
                        INSERT INTO payment_attempts (
                            attempt_id,
                            transaction_fk,
                            attempt_number,
                            processor_fk,
                            attempt_status,
                            failure_reason,
                            initiated_at,
                            completed_at
                        )
                        VALUES %s
                        RETURNING id, attempt_id
                        """,
                        attempt_rows,
                        page_size=5000,
                    )

                    returned_attempts = (
                        cursor.fetchall()
                    )

                    attempt_id_map = {
                        attempt_id:
                            database_id
                        for (
                            database_id,
                            attempt_id,
                        ) in returned_attempts
                    }

                    if len(
                        attempt_id_map
                    ) != len(attempt_rows):

                        raise RuntimeError(
                            "Payment attempt ID "
                            "mapping count does not "
                            "match generated attempt "
                            "count."
                        )

                    attempt_count = (
                        len(attempt_rows)
                    )

                # ======================================================
                # 6. Prepare payment events
                # ======================================================

                event_rows = []

                for (
                    attempt_id,
                    attempt,
                ) in attempt_metadata:

                    attempt_db_id = (
                        attempt_id_map[
                            attempt_id
                        ]
                    )

                    for event in attempt[
                        "events"
                    ]:

                        event_rows.append(
                            (
                                self._generate_event_id(),
                                attempt_db_id,
                                event[
                                    "event_status"
                                ],
                                event[
                                    "event_at"
                                ],
                                event[
                                    "sequence_number"
                                ],
                            )
                        )

                # ======================================================
                # 7. Bulk insert events
                # ======================================================

                if event_rows:

                    execute_values(
                        cursor,
                        """
                        INSERT INTO payment_events (
                            event_id,
                            payment_attempt_fk,
                            event_status,
                            event_at,
                            sequence_number
                        )
                        VALUES %s
                        """,
                        event_rows,
                        page_size=10000,
                    )

                    event_count = (
                        len(event_rows)
                    )

                # ======================================================
                # 8. Commit
                # ======================================================

                connection.commit()

                return {
                    "transactions":
                        transaction_count,

                    "attempts":
                        attempt_count,

                    "events":
                        event_count,

                    "captured":
                        captured_count,

                    "failed":
                        failed_count,

                    "canceled":
                        canceled_count,

                    "retried":
                        retried_count,

                    "cross_border":
                        cross_border_count,
                }

        except Exception:

            connection.rollback()

            raise

        finally:

            connection.close()


    # ------------------------------------------------------------------
    # Resume support
    # ------------------------------------------------------------------

    def get_latest_transaction_date(self):
        """
        Return the latest transaction date currently stored
        in the database.

        Used by the simulation runner to resume generation
        from the next missing date.
        """

        connection = get_connection()

        try:
            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    SELECT MAX(simulation_date)
                    FROM transactions
                    """
                )

                result = cursor.fetchone()

                return result[0]

        finally:
            connection.close()



    def get_transaction_count_for_date(
        self,
        transaction_date,
    ):
        """
        Return the number of transactions stored
        for a specific simulation date.
        """

        connection = get_connection()

        try:
            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM transactions
                    WHERE initiated_at::date = %s
                    """,
                    (transaction_date,),
                )

                result = cursor.fetchone()

                return result[0]

        finally:
            connection.close()