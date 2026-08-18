from database.loaders.transaction_dependencies import (
    fetch_transaction_dependencies,
)

from simulator.transactions.dependencies import (
    TransactionDependencyResolver,
)


def main():

    # --------------------------------------------------------------
    # Load master data
    # --------------------------------------------------------------

    dependencies = (
        fetch_transaction_dependencies()
    )

    resolver = (
        TransactionDependencyResolver(
            dependencies
        )
    )

    print(
        "Transaction dependency resolver initialized."
    )

    # --------------------------------------------------------------
    # Basic index validation
    # --------------------------------------------------------------

    if not resolver.customer_by_id:
        raise AssertionError(
            "Customer index is empty."
        )

    if not resolver.merchant_by_id:
        raise AssertionError(
            "Merchant index is empty."
        )

    if not resolver.products_by_merchant:
        raise AssertionError(
            "Product-by-merchant index is empty."
        )

    if not resolver.payment_methods_by_customer:
        raise AssertionError(
            "Payment-method-by-customer index is empty."
        )

    if not resolver.processors_by_country:
        raise AssertionError(
            "Processor-by-country index is empty."
        )

    # --------------------------------------------------------------
    # Select sample customer
    # --------------------------------------------------------------

    customer = resolver.customers[0]

    customer_payment_methods = (
        resolver.get_valid_payment_methods(
            customer
        )
    )

    if not customer_payment_methods:
        raise AssertionError(
            f"Customer {customer['id']} "
            "has no valid payment methods."
        )

    print()
    print(
        f"Customer: {customer['customer_id']}"
    )

    print(
        f"Country: {customer['country_code']}"
    )

    print(
        f"Timezone: {customer['timezone']}"
    )

    print(
        "Valid payment methods:",
        len(customer_payment_methods),
    )

    # --------------------------------------------------------------
    # Select sample merchant
    # --------------------------------------------------------------

    merchant = resolver.merchants[0]

    merchant_products = (
        resolver.get_valid_products(
            merchant
        )
    )

    if not merchant_products:
        raise AssertionError(
            f"Merchant {merchant['id']} "
            "has no valid products."
        )

    print()
    print(
        f"Merchant: {merchant['merchant_name']}"
    )

    print(
        f"Country: {merchant['country_code']}"
    )

    print(
        f"Currency: {merchant['default_currency']}"
    )

    print(
        "Valid products:",
        len(merchant_products),
    )

    # --------------------------------------------------------------
    # Processor eligibility
    # --------------------------------------------------------------

    eligible_processors = (
        resolver.get_processors_for_country(
            merchant["country_code"]
        )
    )

    if not eligible_processors:
        raise AssertionError(
            f"No processors available for "
            f"merchant country "
            f"{merchant['country_code']}"
        )

    print()
    print(
        f"Eligible processors for "
        f"{merchant['country_code']}:"
    )

    for processor in eligible_processors:

        print(
            f"  {processor['processor_name']}"
        )

    # --------------------------------------------------------------
    # Card-network processor compatibility
    # --------------------------------------------------------------

    payment_method = (
        customer_payment_methods[0]
    )

    compatible_processors = (
        resolver.get_processors_for_payment_method(
            merchant["country_code"],
            payment_method["card_network"],
        )
    )

    if not compatible_processors:
        raise AssertionError(
            "No processor supports both "
            "merchant country and payment "
            "method card network."
        )

    print()
    print(
        "Sample payment method:"
    )

    print(
        f"  Network: "
        f"{payment_method['card_network']}"
    )

    print(
        f"  Type: "
        f"{payment_method['card_type']}"
    )

    print(
        "Compatible processors:"
    )

    for processor in compatible_processors:

        print(
            f"  {processor['processor_name']}"
        )

    # --------------------------------------------------------------
    # Full customer → merchant resolution
    # --------------------------------------------------------------

    context = (
        resolver.resolve_customer_merchant_context(
            customer,
            merchant,
        )
    )

    print()
    print(
        "Customer → Merchant context resolved."
    )

    print(
        f"Cross-border: "
        f"{context['is_cross_border']}"
    )

    # --------------------------------------------------------------
    # Final validation
    # --------------------------------------------------------------

    print()
    print(
        "All transaction dependency resolver "
        "tests passed."
    )


if __name__ == "__main__":
    main()