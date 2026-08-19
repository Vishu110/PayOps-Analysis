import secrets


class TransactionDatabaseRowBuilder:
    """
    Convert a complete simulated payment journey into
    database-ready rows.

    No database operations are performed here.
    """

    @staticmethod
    def _generate_id(prefix: str) -> str:
        return (
            f"{prefix}_"
            f"{secrets.token_urlsafe(18)}"
        )

    def build_transaction_row(
        self,
        payment: dict,
    ) -> dict:

        transaction = payment[
            "transaction"
        ]

        return {
            "transaction_id":
                transaction[
                    "transaction_id"
                ],

            "customer_fk":
                transaction[
                    "customer_fk"
                ],

            "merchant_fk":
                transaction[
                    "merchant_fk"
                ],

            "product_fk":
                transaction[
                    "product_fk"
                ],

            "payment_method_fk":
                transaction[
                    "payment_method_fk"
                ],

            "transaction_type":
                transaction[
                    "transaction_type"
                ],

            "amount":
                transaction[
                    "amount"
                ],

            "currency":
                transaction[
                    "currency"
                ],

            "quantity":
                transaction[
                    "quantity"
                ],

            "current_status":
                payment[
                    "final_status"
                ],

            "initiated_at":
                transaction[
                    "initiated_at"
                ],

            "completed_at":
                payment[
                    "completed_at"
                ],
        }

    def build_attempt_rows(
        self,
        payment: dict,
        transaction_db_id: int,
    ) -> list[dict]:

        rows = []

        for attempt in payment[
            "attempts"
        ]:

            processor = attempt[
                "processor"
            ]

            rows.append(
                {
                    "attempt_id":
                        self._generate_id(
                            "att"
                        ),

                    "transaction_fk":
                        transaction_db_id,

                    "attempt_number":
                        attempt[
                            "attempt_number"
                        ],

                    "processor_fk":
                        processor["id"],

                    "attempt_status":
                        attempt[
                            "attempt_status"
                        ],

                    "failure_reason":
                        attempt[
                            "failure_reason"
                        ],

                    "initiated_at":
                        attempt[
                            "initiated_at"
                        ],

                    "completed_at":
                        attempt[
                            "completed_at"
                        ],
                }
            )

        return rows

    def build_event_rows(
        self,
        payment: dict,
        attempt_db_ids: list[int],
    ) -> list[dict]:

        if len(attempt_db_ids) != len(
            payment["attempts"]
        ):
            raise ValueError(
                "Number of database attempt IDs "
                "does not match number of attempts."
            )

        rows = []

        for attempt, attempt_db_id in zip(
            payment["attempts"],
            attempt_db_ids,
        ):

            for event in attempt[
                "events"
            ]:

                rows.append(
                    {
                        "event_id":
                            self._generate_id(
                                "evt"
                            ),

                        "payment_attempt_fk":
                            attempt_db_id,

                        "event_status":
                            event[
                                "event_status"
                            ],

                        "event_at":
                            event[
                                "event_at"
                            ],

                        "sequence_number":
                            event[
                                "sequence_number"
                            ],
                    }
                )

        return rows

    def build_payment_rows(
        self,
        payment: dict,
        transaction_db_id: int,
        attempt_db_ids: list[int],
    ) -> dict:

        return {
            "transaction":
                self.build_transaction_row(
                    payment
                ),

            "attempts":
                self.build_attempt_rows(
                    payment,
                    transaction_db_id,
                ),

            "events":
                self.build_event_rows(
                    payment,
                    attempt_db_ids,
                ),
        }