from collections import defaultdict


class TransactionDependencyResolver:
    """
    Build and resolve valid master-data relationships
    required for transaction generation.

    Expensive dependency validation is performed once
    during initialization and cached for repeated
    transaction generation.
    """

    def __init__(self, dependencies: dict):

        self.customers = dependencies["customers"]
        self.merchants = dependencies["merchants"]
        self.products = dependencies["products"]
        self.payment_methods = dependencies["payment_methods"]
        self.processors = dependencies["processors"]

        self._build_indexes()

    # ------------------------------------------------------------------
    # Build lookup indexes and caches
    # ------------------------------------------------------------------

    def _build_indexes(self) -> None:

        # --------------------------------------------------------------
        # Customer lookup
        # --------------------------------------------------------------

        self.customer_by_id = {
            customer["id"]: customer
            for customer in self.customers
        }

        # --------------------------------------------------------------
        # Merchant lookup
        # --------------------------------------------------------------

        self.merchant_by_id = {
            merchant["id"]: merchant
            for merchant in self.merchants
        }

        # --------------------------------------------------------------
        # Processor lookup
        # --------------------------------------------------------------

        self.processor_by_id = {
            processor["id"]: processor
            for processor in self.processors
        }

        # --------------------------------------------------------------
        # Products by merchant
        # --------------------------------------------------------------

        self.products_by_merchant = defaultdict(list)

        for product in self.products:
            self.products_by_merchant[
                product["merchant_fk"]
            ].append(product)

        # --------------------------------------------------------------
        # Valid products by merchant
        #
        # These rules do not change during simulation, so calculate
        # them once instead of filtering products for every transaction.
        # --------------------------------------------------------------

        self.valid_products_by_merchant = {}

        for merchant in self.merchants:

            merchant_id = merchant["id"]

            valid_products = [
                product
                for product in self.products_by_merchant.get(
                    merchant_id,
                    [],
                )
                if (
                    product["product_status"] == "ACTIVE"
                    and product["currency"]
                    == merchant["default_currency"]
                )
            ]

            self.valid_products_by_merchant[
                merchant_id
            ] = valid_products

        # --------------------------------------------------------------
        # Payment methods by customer
        # --------------------------------------------------------------

        self.payment_methods_by_customer = defaultdict(list)

        for payment_method in self.payment_methods:
            self.payment_methods_by_customer[
                payment_method["customer_fk"]
            ].append(payment_method)

        # --------------------------------------------------------------
        # Valid payment methods by customer
        #
        # Calculate once because payment-method status is static
        # during transaction generation.
        # --------------------------------------------------------------

        self.valid_payment_methods_by_customer = {}

        for customer in self.customers:

            customer_id = customer["id"]

            valid_payment_methods = [
                payment_method
                for payment_method
                in self.payment_methods_by_customer.get(
                    customer_id,
                    [],
                )
                if (
                    payment_method[
                        "payment_method_status"
                    ]
                    == "ACTIVE"
                )
            ]

            self.valid_payment_methods_by_customer[
                customer_id
            ] = valid_payment_methods

        # --------------------------------------------------------------
        # Active customers with valid payment methods
        #
        # This list is generated once and reused for every transaction.
        # --------------------------------------------------------------

        self.active_customers = [
            customer
            for customer in self.customers
            if (
                customer["customer_status"] == "ACTIVE"
                and self.valid_payment_methods_by_customer.get(
                    customer["id"],
                    [],
                )
            )
        ]

        # --------------------------------------------------------------
        # Active merchants with valid products
        #
        # This list is generated once and reused for every transaction.
        # --------------------------------------------------------------

        self.active_merchants = [
            merchant
            for merchant in self.merchants
            if (
                merchant["merchant_status"] == "ACTIVE"
                and self.valid_products_by_merchant.get(
                    merchant["id"],
                    [],
                )
            )
        ]

        # --------------------------------------------------------------
        # Processors by country
        # --------------------------------------------------------------

        self.processors_by_country = defaultdict(list)

        for processor in self.processors:

            for country_code in processor[
                "supported_regions"
            ]:

                self.processors_by_country[
                    country_code
                ].append(processor)

        # --------------------------------------------------------------
        # Processors by card network
        # --------------------------------------------------------------

        self.processors_by_card_network = defaultdict(list)

        for processor in self.processors:

            for network in processor[
                "supported_card_networks"
            ]:

                self.processors_by_card_network[
                    network
                ].append(processor)

    # ------------------------------------------------------------------
    # Customer
    # ------------------------------------------------------------------

    def get_customer(
        self,
        customer_id: int,
    ) -> dict:

        try:
            return self.customer_by_id[
                customer_id
            ]

        except KeyError:

            raise ValueError(
                f"Customer not found: {customer_id}"
            )

    # ------------------------------------------------------------------
    # Merchant
    # ------------------------------------------------------------------

    def get_merchant(
        self,
        merchant_id: int,
    ) -> dict:

        try:
            return self.merchant_by_id[
                merchant_id
            ]

        except KeyError:

            raise ValueError(
                f"Merchant not found: {merchant_id}"
            )

    # ------------------------------------------------------------------
    # Products
    # ------------------------------------------------------------------

    def get_products_for_merchant(
        self,
        merchant_id: int,
    ) -> list[dict]:

        return self.products_by_merchant.get(
            merchant_id,
            [],
        )

    # ------------------------------------------------------------------
    # Valid products
    # ------------------------------------------------------------------

    def get_valid_products(
        self,
        merchant: dict,
    ) -> list[dict]:

        return self.valid_products_by_merchant.get(
            merchant["id"],
            [],
        )

    # ------------------------------------------------------------------
    # Payment methods
    # ------------------------------------------------------------------

    def get_payment_methods_for_customer(
        self,
        customer_id: int,
    ) -> list[dict]:

        return self.payment_methods_by_customer.get(
            customer_id,
            [],
        )

    # ------------------------------------------------------------------
    # Valid payment methods
    # ------------------------------------------------------------------

    def get_valid_payment_methods(
        self,
        customer: dict,
    ) -> list[dict]:

        return self.valid_payment_methods_by_customer.get(
            customer["id"],
            [],
        )

    # ------------------------------------------------------------------
    # Processor eligibility
    # ------------------------------------------------------------------

    def get_processors_for_country(
        self,
        country_code: str,
    ) -> list[dict]:

        return self.processors_by_country.get(
            country_code,
            [],
        )

    # ------------------------------------------------------------------
    # Processor + card network eligibility
    # ------------------------------------------------------------------

    def get_processors_for_payment_method(
        self,
        country_code: str,
        card_network: str,
    ) -> list[dict]:

        country_processors = (
            self.get_processors_for_country(
                country_code
            )
        )

        return [
            processor
            for processor in country_processors
            if card_network
            in processor["supported_card_networks"]
        ]

    # ------------------------------------------------------------------
    # Merchant product compatibility
    # ------------------------------------------------------------------

    def resolve_customer_merchant_context(
        self,
        customer: dict,
        merchant: dict,
    ) -> dict:

        if (
            customer["customer_status"]
            != "ACTIVE"
        ):
            raise ValueError(
                f"Customer {customer['id']} is not active."
            )

        if (
            merchant["merchant_status"]
            != "ACTIVE"
        ):
            raise ValueError(
                f"Merchant {merchant['id']} is not active."
            )

        products = self.get_valid_products(
            merchant
        )

        if not products:
            raise ValueError(
                f"Merchant {merchant['id']} "
                "has no valid products."
            )

        payment_methods = (
            self.get_valid_payment_methods(
                customer
            )
        )

        if not payment_methods:
            raise ValueError(
                f"Customer {customer['id']} "
                "has no valid payment methods."
            )

        is_cross_border = (
            customer["country_code"]
            != merchant["country_code"]
        )

        return {
            "customer": customer,
            "merchant": merchant,
            "products": products,
            "payment_methods": payment_methods,
            "is_cross_border": is_cross_border,
        }