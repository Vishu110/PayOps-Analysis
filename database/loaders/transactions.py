import psycopg2

from database.connection import get_connection


class TransactionLoader:
    """
    Persist complete simulated payment journeys.

    Insert order:
        transactions
            -> payment_attempts
                -> payment_events

    Each payment journey is committed atomically.
    """

    def load_payment(
        self,
        payment: dict,
    ) -> dict:

        transaction = payment[
            "transaction"
        ]

        attempts = payment[
            "attempts"
        ]

        connection = get_connection()

        try:
            with connection.cursor() as cursor:

                # --------------------------------------------------
                # 1. Transaction
                # --------------------------------------------------

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

                # --------------------------------------------------
                # 2. Payment attempts
                # --------------------------------------------------

                attempt_db_ids = []

                for attempt in attempts:

                    processor = attempt[
                        "processor"
                    ]

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
                            self._generate_attempt_id(),

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

                    attempt_db_ids.append(
                        attempt_db_id
                    )

                    # ----------------------------------------------
                    # 3. Payment events
                    # ----------------------------------------------

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
                            RETURNING id
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

            connection.commit()

            return {
                "transaction_id":
                    transaction[
                        "transaction_id"
                    ],

                "transaction_db_id":
                    transaction_db_id,

                "attempt_count":
                    len(attempts),

                "event_count":
                    sum(
                        len(
                            attempt["events"]
                        )
                        for attempt in attempts
                    ),
            }

        except Exception:
            connection.rollback()
            raise

        finally:
            connection.close()

    @staticmethod
    def _generate_attempt_id():

        import secrets

        return (
            "att_"
            + secrets.token_urlsafe(18)
        )

    @staticmethod
    def _generate_event_id():

        import secrets

        return (
            "evt_"
            + secrets.token_urlsafe(18)
        )


    def load_batch(
        self,
        payments: list[dict],
    ) -> dict:
        """
        Persist multiple complete payment journeys
        in a single database transaction.

        If any payment fails, the entire batch is rolled back.
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

                for payment in payments:

                    transaction = payment[
                        "transaction"
                    ]

                    attempts = payment[
                        "attempts"
                    ]

                    # --------------------------------------------------
                    # Transaction
                    # --------------------------------------------------

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

                    transaction_count += 1

                    # --------------------------------------------------
                    # Outcome counters
                    # --------------------------------------------------

                    final_status = payment[
                        "final_status"
                    ]

                    if final_status == "CAPTURED":
                        captured_count += 1

                    elif final_status == "FAILED":
                        failed_count += 1

                    elif final_status == "CANCELED":
                        canceled_count += 1

                    if len(attempts) > 1:
                        retried_count += 1

                    # --------------------------------------------------
                    # Cross-border
                    # --------------------------------------------------

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

                    # --------------------------------------------------
                    # Attempts + Events
                    # --------------------------------------------------

                    for attempt in attempts:

                        processor = attempt[
                            "processor"
                        ]

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
                                self._generate_attempt_id(),

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
                            ),
                        )

                        attempt_db_id = (
                            cursor.fetchone()[0]
                        )

                        attempt_count += 1

                        # ----------------------------------------------
                        # Events
                        # ----------------------------------------------

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
                "transactions": transaction_count,
                "attempts": attempt_count,
                "events": event_count,
                "captured": captured_count,
                "failed": failed_count,
                "canceled": canceled_count,
                "retried": retried_count,
                "cross_border": cross_border_count,
            }

        except Exception:
            connection.rollback()
            raise

        finally:
            connection.close()