from database.loaders.transaction_dependencies import (
    fetch_transaction_dependencies,
)


def main():

    dependencies = fetch_transaction_dependencies()

    customers = dependencies["customers"]
    merchants = dependencies["merchants"]
    products = dependencies["products"]
    payment_methods = dependencies["payment_methods"]
    processors = dependencies["processors"]

    print(
        f"Loaded customers: {len(customers):,}"
    )

    print(
        f"Loaded merchants: {len(merchants):,}"
    )

    print(
        f"Loaded products: {len(products):,}"
    )

    print(
        f"Loaded payment methods: "
        f"{len(payment_methods):,}"
    )

    print(
        f"Loaded processors: {len(processors):,}"
    )

    # --------------------------------------------------------------
    # Basic existence validation
    # --------------------------------------------------------------

    if not customers:
        raise AssertionError(
            "No customers loaded."
        )

    if not merchants:
        raise AssertionError(
            "No merchants loaded."
        )

    if not products:
        raise AssertionError(
            "No products loaded."
        )

    if not payment_methods:
        raise AssertionError(
            "No payment methods loaded."
        )

    if not processors:
        raise AssertionError(
            "No processors loaded."
        )

    # --------------------------------------------------------------
    # Customer timezone validation
    # --------------------------------------------------------------

    missing_customer_timezones = [
        customer["id"]
        for customer in customers
        if not customer["timezone"]
    ]

    if missing_customer_timezones:
        raise AssertionError(
            "Customers missing timezone: "
            f"{missing_customer_timezones[:10]}"
        )

    # --------------------------------------------------------------
    # Product → Merchant validation
    # --------------------------------------------------------------

    merchant_ids = {
        merchant["id"]
        for merchant in merchants
    }

    invalid_products = [
        product["id"]
        for product in products
        if product["merchant_fk"] not in merchant_ids
    ]

    if invalid_products:
        raise AssertionError(
            "Products reference invalid merchants: "
            f"{invalid_products[:10]}"
        )

    # --------------------------------------------------------------
    # Payment method → Customer validation
    # --------------------------------------------------------------

    customer_ids = {
        customer["id"]
        for customer in customers
    }

    invalid_payment_methods = [
        payment_method["id"]
        for payment_method in payment_methods
        if payment_method["customer_fk"]
        not in customer_ids
    ]

    if invalid_payment_methods:
        raise AssertionError(
            "Payment methods reference invalid customers: "
            f"{invalid_payment_methods[:10]}"
        )

    # --------------------------------------------------------------
    # Processor validation
    # --------------------------------------------------------------

    processor_ids = {
        processor["id"]
        for processor in processors
    }

    invalid_processor_preferences = [
        merchant["id"]
        for merchant in merchants
        if merchant["preferred_processor_fk"]
        not in processor_ids
    ]

    if invalid_processor_preferences:
        raise AssertionError(
            "Merchants reference invalid preferred processors: "
            f"{invalid_processor_preferences[:10]}"
        )

    # --------------------------------------------------------------
    # Processor-region validation
    # --------------------------------------------------------------

    processor_by_id = {
        processor["id"]: processor
        for processor in processors
    }

    invalid_processor_regions = []

    for merchant in merchants:

        processor = processor_by_id[
            merchant["preferred_processor_fk"]
        ]

        supported_regions = (
            processor["supported_regions"]
        )

        if merchant["country_code"] not in supported_regions:
            invalid_processor_regions.append(
                (
                    merchant["id"],
                    merchant["country_code"],
                    processor["processor_name"],
                )
            )

    if invalid_processor_regions:
        raise AssertionError(
            "Merchants have processors that do not "
            "support their country: "
            f"{invalid_processor_regions[:10]}"
        )

    # --------------------------------------------------------------
    # Final output
    # --------------------------------------------------------------

    print()
    print(
        "Customer timezone validation passed."
    )

    print(
        "Product → merchant dependency validation passed."
    )

    print(
        "Payment method → customer dependency "
        "validation passed."
    )

    print(
        "Merchant → processor dependency validation passed."
    )

    print()
    print(
        "All transaction dependency validation "
        "tests passed."
    )


if __name__ == "__main__":
    main()