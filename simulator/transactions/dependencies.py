from collections import defaultdict


class TransactionDependencyResolver:
    """
    Build and resolve valid master-data relationships
    required for transaction generation.
    """

    def __init__(self, dependencies: dict):

        self.customers = dependencies["customers"]
        self.merchants = dependencies["merchants"]
        self.products = dependencies["products"]
        self.payment_methods = dependencies["payment_methods"]
        self.processors = dependencies["processors"]

        self._build_indexes()

    # ------------------------------------------------------------------
    # Build lookup indexes
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
        # Payment methods by customer
        # --------------------------------------------------------------

        self.payment_methods_by_customer = defaultdict(list)

        for payment_method in self.payment_methods:

            self.payment_methods_by_customer[
                payment_method["customer_fk"]
            ].append(payment_method)

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

    def get_valid_products(
        self,
        merchant: dict,
    ) -> list[dict]:

        products = (
            self.get_products_for_merchant(
                merchant["id"]
            )
        )

        return [
            product
            for product in products
            if (
                product["product_status"]
                == "ACTIVE"
            )
            and (
                product["currency"]
                == merchant["default_currency"]
            )
        ]

    # ------------------------------------------------------------------
    # Customer payment-method compatibility
    # ------------------------------------------------------------------

    def get_valid_payment_methods(
        self,
        customer: dict,
    ) -> list[dict]:

        payment_methods = (
            self.get_payment_methods_for_customer(
                customer["id"]
            )
        )

        return [
            payment_method
            for payment_method in payment_methods
            if (
                payment_method[
                    "payment_method_status"
                ]
                == "ACTIVE"
            )
        ]

    # ------------------------------------------------------------------
    # Full dependency context
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