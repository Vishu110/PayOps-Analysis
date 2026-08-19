import random


class PaymentSimulator:
    """
    Orchestrates the complete generation of one
    payment journey.

    Transaction
        ↓
    Payment attempts
        ↓
    Payment events
    """

    def __init__(
        self,
        transaction_generator,
        attempt_engine,
    ):
        self.transaction_generator = (
            transaction_generator
        )

        self.attempt_engine = (
            attempt_engine
        )

    def generate_one(self):

        generated_payment = (
            self.transaction_generator
            .generate_one()
        )

        transaction = (
            generated_payment[
                "transaction"
            ]
        )

        context = (
            generated_payment[
                "context"
            ]
        )

        attempt_result = (
            self.attempt_engine.generate(
                transaction,
                context,
            )
        )

        attempts = (
            attempt_result[
                "attempts"
            ]
        )

        final_status = (
            attempt_result[
                "final_status"
            ]
        )

        completed_at = (
            attempt_result[
                "completed_at"
            ]
        )

        # ----------------------------------------------------------
        # Update transaction-level state
        # ----------------------------------------------------------

        transaction[
            "current_status"
        ] = final_status

        transaction[
            "completed_at"
        ] = completed_at

        return {
            "transaction": transaction,
            "context": context,
            "attempts": attempts,
            "final_status": final_status,
            "completed_at": completed_at,
        }

    def generate_many(
        self,
        count: int,
    ):

        if count < 1:
            raise ValueError(
                "count must be at least 1."
            )

        return [
            self.generate_one()
            for _ in range(count)
        ]