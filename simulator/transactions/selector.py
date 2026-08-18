import random


class TransactionSelector:
    """
    Select a valid customer, merchant, product,
    payment method, and eligible processors for a
    transaction.
    """

    def __init__(
        self,
        resolver,
        geography_config: dict,
        rng: random.Random | None = None,
    ):
        self.resolver = resolver
        self.rng = rng or random.Random()

        self.domestic_weight = float(
            geography_config["domestic"]["weight"]
        )

        self.cross_border_weight = float(
            geography_config["cross_border"]["weight"]
        )

        total_weight = (
            self.domestic_weight
            + self.cross_border_weight
        )

        if abs(total_weight - 100.0) > 0.01:
            raise ValueError(
                "Geography weights must total 100. "
                f"Got {total_weight:.2f}"
            )

    # ------------------------------------------------------------------
    # Customer selection
    # ------------------------------------------------------------------

    def _select_customer(self) -> dict:

        active_customers = [
            customer
            for customer in self.resolver.customers
            if customer["customer_status"] == "ACTIVE"
            and self.resolver.get_valid_payment_methods(
                customer
            )
        ]

        if not active_customers:
            raise ValueError(
                "No active customers with valid "
                "payment methods available."
            )

        return self.rng.choice(
            active_customers
        )

    # ------------------------------------------------------------------
    # Merchant selection
    # ------------------------------------------------------------------

    def _select_merchant(
        self,
        customer: dict,
        is_cross_border: bool,
    ) -> dict:

        active_merchants = [
            merchant
            for merchant in self.resolver.merchants
            if merchant["merchant_status"] == "ACTIVE"
            and self.resolver.get_valid_products(
                merchant
            )
        ]

        if not active_merchants:
            raise ValueError(
                "No active merchants with valid "
                "products available."
            )

        if is_cross_border:

            eligible = [
                merchant
                for merchant in active_merchants
                if (
                    merchant["country_code"]
                    != customer["country_code"]
                )
            ]

        else:

            eligible = [
                merchant
                for merchant in active_merchants
                if (
                    merchant["country_code"]
                    == customer["country_code"]
                )
            ]

        if not eligible:

            raise ValueError(
                "No eligible merchant found for "
                f"customer country "
                f"{customer['country_code']} "
                f"and cross-border="
                f"{is_cross_border}."
            )

        return self.rng.choice(
            eligible
        )

    # ------------------------------------------------------------------
    # Payment method selection
    # ------------------------------------------------------------------

    def _select_payment_method(
        self,
        customer: dict,
    ) -> dict:

        payment_methods = (
            self.resolver.get_valid_payment_methods(
                customer
            )
        )

        if not payment_methods:
            raise ValueError(
                f"Customer {customer['id']} "
                "has no valid payment methods."
            )

        # Prefer the customer's default payment
        # method, while still allowing non-default
        # methods to be selected.
        default_methods = [
            payment_method
            for payment_method in payment_methods
            if payment_method["is_default"]
        ]

        if default_methods:

            # The default method receives a higher
            # probability, rather than being selected
            # 100% of the time.
            if self.rng.random() < 0.82:
                return self.rng.choice(
                    default_methods
                )

        return self.rng.choice(
            payment_methods
        )

    # ------------------------------------------------------------------
    # Product selection
    # ------------------------------------------------------------------

    def _select_product(
        self,
        merchant: dict,
    ) -> dict:

        products = (
            self.resolver.get_valid_products(
                merchant
            )
        )

        if not products:
            raise ValueError(
                f"Merchant {merchant['id']} "
                "has no valid products."
            )

        return self.rng.choice(
            products
        )

    # ------------------------------------------------------------------
    # Processor eligibility
    # ------------------------------------------------------------------

    def _get_eligible_processors(
        self,
        merchant: dict,
        payment_method: dict,
    ) -> list[dict]:

        return (
            self.resolver
            .get_processors_for_payment_method(
                merchant["country_code"],
                payment_method["card_network"],
            )
        )

    # ------------------------------------------------------------------
    # Full transaction context
    # ------------------------------------------------------------------

    def select(self) -> dict:

        # --------------------------------------------------------------
        # Geography
        # --------------------------------------------------------------

        is_cross_border = (
            self.rng.random() * 100
            < self.cross_border_weight
        )

        # --------------------------------------------------------------
        # Customer
        # --------------------------------------------------------------

        customer = self._select_customer()

        # --------------------------------------------------------------
        # Merchant
        # --------------------------------------------------------------

        merchant = self._select_merchant(
            customer,
            is_cross_border,
        )

        # --------------------------------------------------------------
        # Payment method
        # --------------------------------------------------------------

        payment_method = (
            self._select_payment_method(
                customer
            )
        )

        # --------------------------------------------------------------
        # Product
        # --------------------------------------------------------------

        product = self._select_product(
            merchant
        )

        # --------------------------------------------------------------
        # Currency validation
        # --------------------------------------------------------------

        if (
            product["currency"]
            != merchant["default_currency"]
        ):
            raise ValueError(
                "Product currency does not match "
                "merchant currency."
            )

        # --------------------------------------------------------------
        # Processor eligibility
        # --------------------------------------------------------------

        eligible_processors = (
            self._get_eligible_processors(
                merchant,
                payment_method,
            )
        )

        if not eligible_processors:
            raise ValueError(
                "No eligible processor found for "
                f"merchant={merchant['merchant_name']}, "
                f"country={merchant['country_code']}, "
                f"network="
                f"{payment_method['card_network']}."
            )

        # --------------------------------------------------------------
        # Final context
        # --------------------------------------------------------------

        return {
            "customer": customer,
            "merchant": merchant,
            "product": product,
            "payment_method": payment_method,
            "eligible_processors": eligible_processors,
            "is_cross_border": is_cross_border,
        }