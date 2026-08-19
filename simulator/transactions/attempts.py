from datetime import timedelta
import random


class PaymentAttemptEngine:
    """
    Generate payment attempts for a transaction.

    A transaction may have one or more attempts.
    Each attempt receives a processor and its own
    chronological lifecycle.
    """

    RETRYABLE_SCENARIOS = {
        "AUTHORIZATION_FAILURE",
        "PROCESSING_FAILURE",
        "CAPTURE_FAILURE",
    }

    FAILURE_REASONS = {
        "AUTHORIZATION_FAILURE": [
            "INSUFFICIENT_FUNDS",
            "DO_NOT_HONOR",
            "EXPIRED_CARD",
            "INVALID_CARD",
            "FRAUD_BLOCK",
        ],
        "PROCESSING_FAILURE": [
            "PROCESSOR_ERROR",
            "NETWORK_ERROR",
        ],
        "CAPTURE_FAILURE": [
            "PROCESSOR_ERROR",
            "NETWORK_ERROR",
        ],
    }

    def __init__(
        self,
        resolver,
        lifecycle_engine,
        attempts_config,
        rng=None,
    ):
        self.resolver = resolver
        self.lifecycle_engine = lifecycle_engine
        self.config = attempts_config
        self.rng = rng or random.Random()

        self.max_attempts = int(
            attempts_config["max_attempts"]
        )

        self.retry_policy = (
            attempts_config["retry_policy"]
        )

        self.retry_delay = (
            attempts_config[
                "retry_delay_seconds"
            ]
        )

    # ------------------------------------------------------------------
    # Processor selection
    # ------------------------------------------------------------------

    def _select_processor(
        self,
        merchant,
        payment_method,
        previously_used_processor_ids,
    ):
        eligible_processors = (
            self.resolver
            .get_processors_for_payment_method(
                merchant["country_code"],
                payment_method["card_network"],
            )
        )

        if not eligible_processors:
            raise ValueError(
                "No eligible processor available for "
                f"merchant country "
                f"{merchant['country_code']} and "
                f"card network "
                f"{payment_method['card_network']}."
            )

        # Prefer an unused processor during retries.
        unused = [
            processor
            for processor in eligible_processors
            if processor["id"]
            not in previously_used_processor_ids
        ]

        candidates = unused or eligible_processors

        # If merchant has a preferred processor and it is
        # eligible, give it a higher chance on attempt 1.
        preferred_id = merchant.get(
            "preferred_processor_fk"
        )

        preferred = [
            processor
            for processor in candidates
            if processor["id"] == preferred_id
        ]

        if preferred:
            if self.rng.random() < 0.70:
                return preferred[0]

        return self.rng.choice(candidates)

    # ------------------------------------------------------------------
    # Failure reason
    # ------------------------------------------------------------------

    def _select_failure_reason(
        self,
        scenario,
    ):
        reasons = self.FAILURE_REASONS.get(
            scenario
        )

        if not reasons:
            return None

        return self.rng.choice(
            reasons
        )

    # ------------------------------------------------------------------
    # Retry decision
    # ------------------------------------------------------------------

    def _should_retry(
        self,
        scenario,
    ):
        if scenario not in self.retry_policy:
            return False

        policy = self.retry_policy[
            scenario
        ]

        if not policy["retryable"]:
            return False

        probability = float(
            policy["retry_probability"]
        )

        return (
            self.rng.random() * 100
            < probability
        )

    # ------------------------------------------------------------------
    # Retry delay
    # ------------------------------------------------------------------

    def _sample_retry_delay(self):
        minimum = float(
            self.retry_delay["min"]
        )

        maximum = float(
            self.retry_delay["max"]
        )

        return self.rng.uniform(
            minimum,
            maximum,
        )

    # ------------------------------------------------------------------
    # Generate attempts
    # ------------------------------------------------------------------

    def generate(
        self,
        transaction,
        context,
    ):
        customer = context[
            "customer"
        ]

        merchant = context[
            "merchant"
        ]

        payment_method = context[
            "payment_method"
        ]

        attempts = []

        previous_processor_ids = set()

        attempt_start = transaction[
            "initiated_at"
        ]

        for attempt_number in range(
            1,
            self.max_attempts + 1,
        ):

            processor = self._select_processor(
                merchant,
                payment_method,
                previous_processor_ids,
            )

            previous_processor_ids.add(
                processor["id"]
            )

            lifecycle = (
                self.lifecycle_engine.generate(
                    attempt_start
                )
            )

            final_status = lifecycle[
                "final_status"
            ]

            failure_reason = None

            if final_status == "FAILED":

                failure_reason = (
                    self._select_failure_reason(
                        lifecycle["scenario"]
                    )
                )

            attempt = {
                "attempt_number":
                    attempt_number,

                "processor":
                    processor,

                "attempt_status":
                    final_status,

                "failure_reason":
                    failure_reason,

                "initiated_at":
                    attempt_start,

                "completed_at":
                    lifecycle[
                        "completed_at"
                    ],

                "scenario":
                    lifecycle[
                        "scenario"
                    ],

                "events":
                    lifecycle[
                        "events"
                    ],
            }

            attempts.append(
                attempt
            )

            # ----------------------------------------------------------
            # Terminal success
            # ----------------------------------------------------------

            if final_status == "CAPTURED":
                break

            # ----------------------------------------------------------
            # Cancellation is terminal
            # ----------------------------------------------------------

            if final_status == "CANCELED":
                break

            # ----------------------------------------------------------
            # Failure / retry decision
            # ----------------------------------------------------------

            if final_status != "FAILED":
                break

            scenario = lifecycle[
                "scenario"
            ]

            if (
                attempt_number
                >= self.max_attempts
            ):
                break

            if not self._should_retry(
                scenario
            ):
                break

            retry_delay = (
                self._sample_retry_delay()
            )

            attempt_start = (
                lifecycle[
                    "completed_at"
                ]
                + timedelta(
                    seconds=retry_delay
                )
            )

        return {
            "attempts": attempts,
            "final_status": attempts[-1][
                "attempt_status"
            ],
            "completed_at": attempts[-1][
                "completed_at"
            ],
        }