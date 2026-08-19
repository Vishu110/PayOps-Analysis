from datetime import datetime, date, time
from decimal import Decimal
from zoneinfo import ZoneInfo
import random
import secrets

from simulator.transactions.selector import (
    TransactionSelector,
)


class TransactionGenerator:
    """
    Generate transaction records from valid transaction
    dependency contexts.

    This class is responsible for transaction-level
    attributes only. Payment attempts and payment events
    are generated later from the transaction timeline.
    """

    def __init__(
        self,
        selector: TransactionSelector,
        transaction_config: dict,
        rng: random.Random | None = None,
    ):
        self.selector = selector
        self.config = transaction_config
        self.rng = rng or random.Random()

        self.quantity_distribution = (
            self.config[
                "quantity_distribution"
            ]
        )

        self.hour_distribution = (
            self.config[
                "initiation"
            ]["hour_distribution"]
        )

        self.transaction_type_distribution = (
            self.config[
                "transaction_type_distribution"
            ]
        )

    # ------------------------------------------------------------------
    # Weighted selection
    # ------------------------------------------------------------------

    def _select_weighted_value(
        self,
        distribution: dict,
    ):
        values = list(distribution.keys())

        weights = [
            float(
                configuration["weight"]
            )
            for configuration in distribution.values()
        ]

        return self.rng.choices(
            values,
            weights=weights,
            k=1,
        )[0]

    # ------------------------------------------------------------------
    # Quantity
    # ------------------------------------------------------------------

    def _select_quantity(self) -> int:

        quantity = self._select_weighted_value(
            self.quantity_distribution
        )

        return int(quantity)

    # ------------------------------------------------------------------
    # Transaction type
    # ------------------------------------------------------------------

    def _select_transaction_type(self) -> str:

        return self._select_weighted_value(
            self.transaction_type_distribution
        )

    # ------------------------------------------------------------------
    # Initiation hour
    # ------------------------------------------------------------------

    def _select_initiation_hour(self) -> int:

        hour = self._select_weighted_value(
            self.hour_distribution
        )

        return int(hour)

    # ------------------------------------------------------------------
    # Initiation timestamp
    # ------------------------------------------------------------------

    def _generate_initiated_at(
        self,
        customer: dict,
    ) -> datetime:

        start_date = date.fromisoformat(
            str(
                self.config[
                    "historical_start_date"
                ]
            )
        )

        current_date = date.fromisoformat(
            str(
                self.config[
                    "_simulation_current_date"
                ]
            )
        )

        if start_date > current_date:
            raise ValueError(
                "Historical start date cannot be "
                "after simulation current date."
            )

        # Select a calendar date uniformly for now.
        # Daily volume variation will be applied by
        # the outer simulation engine later.
        day_range = (
            current_date - start_date
        ).days

        selected_day = (
            start_date
            + __import__(
                "datetime"
            ).timedelta(
                days=self.rng.randint(
                    0,
                    day_range,
                )
            )
        )

        hour = self._select_initiation_hour()

        minute = self.rng.randint(
            0,
            59,
        )

        second = self.rng.randint(
            0,
            59,
        )

        microsecond = self.rng.randint(
            0,
            999999,
        )

        local_datetime = datetime.combine(
            selected_day,
            time(
                hour=hour,
                minute=minute,
                second=second,
                microsecond=microsecond,
            ),
        )

        timezone = ZoneInfo(
            customer["timezone"]
        )

        return local_datetime.replace(
            tzinfo=timezone
        )

    # ------------------------------------------------------------------
    # Transaction amount
    # ------------------------------------------------------------------

    def _calculate_amount(
        self,
        product: dict,
        quantity: int,
    ) -> Decimal:

        base_price = Decimal(
            str(product["base_price"])
        )

        amount = (
            base_price
            * Decimal(quantity)
        )

        return amount.quantize(
            Decimal("0.01")
        )

    # ------------------------------------------------------------------
    # Transaction ID
    # ------------------------------------------------------------------

    def _generate_transaction_id(
        self,
    ) -> str:

        suffix = secrets.token_urlsafe(
            18
        )

        return f"txn_{suffix}"

    # ------------------------------------------------------------------
    # Generate one transaction
    # ------------------------------------------------------------------

    def generate_one(self) -> dict:

        context = self.selector.select()

        customer = context[
            "customer"
        ]

        merchant = context[
            "merchant"
        ]

        product = context[
            "product"
        ]

        payment_method = context[
            "payment_method"
        ]

        quantity = (
            self._select_quantity()
        )

        transaction_type = (
            self._select_transaction_type()
        )

        amount = self._calculate_amount(
            product,
            quantity,
        )

        initiated_at = (
            self._generate_initiated_at(
                customer
            )
        )

        return {
            "transaction": {
                "transaction_id":
                    self._generate_transaction_id(),

                "customer_fk":
                    customer["id"],

                "merchant_fk":
                    merchant["id"],

                "product_fk":
                    product["id"],

                "payment_method_fk":
                    payment_method["id"],

                "transaction_type":
                    transaction_type,

                "amount":
                    amount,

                "currency":
                    product["currency"],

                "quantity":
                    quantity,

                "current_status":
                    "PENDING",

                "initiated_at":
                    initiated_at,
            },

            "context": {
                "customer": customer,
                "merchant": merchant,
                "product": product,
                "payment_method": payment_method,
            },
        }