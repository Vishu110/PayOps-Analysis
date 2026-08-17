from datetime import date
from random import Random

from database.loaders.banks import fetch_banks
from database.loaders.customers import fetch_customers
from simulator.utils.config_loader import load_generator_config
from simulator.utils.id_generator import generate_id


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GENERATOR_CONFIG = load_generator_config()

CUSTOMER_CONFIG = GENERATOR_CONFIG[
    "customers"
]

PAYMENT_METHOD_CONFIG = GENERATOR_CONFIG[
    "payment_methods"
]

SIMULATION_DATE = GENERATOR_CONFIG[
    "simulation"
]["current_date"]


# ---------------------------------------------------------------------------
# Weighted selection
# ---------------------------------------------------------------------------

def weighted_choice(
    rng: Random,
    distribution: dict,
):
    """
    Select one value from a weighted configuration dictionary.
    """

    values = list(
        distribution.keys()
    )

    weights = [
        distribution[value]["weight"]
        for value in values
    ]

    return rng.choices(
        values,
        weights=weights,
        k=1,
    )[0]


# ---------------------------------------------------------------------------
# Issuing-bank selection
# ---------------------------------------------------------------------------

def build_banks_by_country(
    banks: list[dict],
) -> dict[str, list[dict]]:
    """
    Build a lookup of active issuing banks by country.
    """

    banks_by_country = {}

    for bank in banks:

        if bank["bank_status"] != "ACTIVE":
            continue

        country_code = bank[
            "country_code"
        ]

        banks_by_country.setdefault(
            country_code,
            [],
        ).append(bank)

    return banks_by_country


def select_issuing_bank(
    rng: Random,
    customer: dict,
    banks_by_country: dict[str, list[dict]],
) -> dict:
    """
    Select an eligible issuing bank based on
    the customer's country.
    """

    country_code = customer[
        "country_code"
    ]

    eligible_banks = banks_by_country.get(
        country_code,
        [],
    )

    if not eligible_banks:

        raise ValueError(
            f"No active issuing bank found "
            f"for customer country "
            f"'{country_code}'."
        )

    return rng.choice(
        eligible_banks
    )


# ---------------------------------------------------------------------------
# Card-network selection
# ---------------------------------------------------------------------------

VALID_CARD_NETWORKS = {
    "VISA",
    "MASTERCARD",
    "AMEX",
}


def select_card_network(
    rng: Random,
    bank: dict,
) -> str:
    """
    Select a card network supported by both:

    1. The issuing bank
    2. The payment-method card_network enum
    """

    supported_networks = set(
        bank[
            "supported_card_networks"
        ]
    )

    eligible_networks = (
        supported_networks
        & VALID_CARD_NETWORKS
    )

    if not eligible_networks:

        raise ValueError(
            f"Bank '{bank['bank_name']}' "
            f"has no valid card network."
        )

    return rng.choice(
        sorted(eligible_networks)
    )


# ---------------------------------------------------------------------------
# Card expiry
# ---------------------------------------------------------------------------

def generate_expiry(
    rng: Random,
    status: str,
) -> tuple[int, int]:
    """
    Generate an expiry month and year based on
    the payment-method status.

    ACTIVE:
        Future expiry.

    EXPIRED:
        Expiry must be before the simulation date.

    BLOCKED:
        Future expiry.
    """

    current_year = SIMULATION_DATE.year
    current_month = SIMULATION_DATE.month

    expiry_config = PAYMENT_METHOD_CONFIG[
        "expiry"
    ]

    # --------------------------------------------------
    # Active / blocked cards
    # --------------------------------------------------

    if status in {
        "ACTIVE",
        "BLOCKED",
    }:

        min_year = expiry_config[
            "active"
        ]["min_year"]

        max_year = expiry_config[
            "active"
        ]["max_year"]

        expiry_year = rng.randint(
            min_year,
            max_year,
        )

        expiry_month = rng.randint(
            1,
            12,
        )

        return (
            expiry_month,
            expiry_year,
        )

    # --------------------------------------------------
    # Expired cards
    # --------------------------------------------------

    if status == "EXPIRED":

        min_year = expiry_config[
            "expired"
        ]["min_year"]

        max_year = min(
            expiry_config[
                "expired"
            ]["max_year"],
            current_year,
        )

        expiry_year = rng.randint(
            min_year,
            max_year,
        )

        if expiry_year == current_year:

            if current_month <= 1:

                raise ValueError(
                    "Cannot generate an expired "
                    "card for the current month."
                )

            expiry_month = rng.randint(
                1,
                current_month - 1,
            )

        else:

            expiry_month = rng.randint(
                1,
                12,
            )

        return (
            expiry_month,
            expiry_year,
        )

    raise ValueError(
        f"Unsupported payment-method "
        f"status '{status}'."
    )


# ---------------------------------------------------------------------------
# Card last four
# ---------------------------------------------------------------------------

def generate_card_last_four(
    rng: Random,
    existing_last_four: set[str],
) -> str:
    """
    Generate a unique four-digit card suffix
    for a customer.
    """

    for _ in range(100):

        last_four = f"{rng.randint(0, 9999):04d}"

        if last_four not in existing_last_four:

            existing_last_four.add(
                last_four
            )

            return last_four

    raise RuntimeError(
        "Unable to generate a unique "
        "card_last_four value."
    )


# ---------------------------------------------------------------------------
# Payment-method generation
# ---------------------------------------------------------------------------

def generate_payment_methods(
    seed: int = 20260810,
) -> list[dict]:
    """
    Generate payment methods for all existing customers.

    Payment-method count is determined by the configured
    weighted distribution.

    Each customer receives exactly one default
    payment method.
    """

    rng = Random(seed)

    customers = fetch_customers()
    banks = fetch_banks()

    banks_by_country = build_banks_by_country(
        banks
    )

    payment_method_distribution = (
        CUSTOMER_CONFIG[
            "payment_methods_per_customer"
        ]
    )

    card_type_distribution = (
        PAYMENT_METHOD_CONFIG[
            "card_type_distribution"
        ]
    )

    status_distribution = (
        PAYMENT_METHOD_CONFIG[
            "status_distribution"
        ]
    )

    payment_method_type = (
        PAYMENT_METHOD_CONFIG[
            "payment_method_type"
        ]
    )

    payment_methods = []

    for customer in customers:

        # --------------------------------------------------
        # Determine number of payment methods
        # --------------------------------------------------

        payment_method_count = int(
            weighted_choice(
                rng,
                payment_method_distribution,
            )
        )

        # --------------------------------------------------
        # Select exactly one default
        # --------------------------------------------------

        default_index = rng.randrange(
            payment_method_count
        )

        existing_last_four: set[str] = set()

        # --------------------------------------------------
        # Generate customer's payment methods
        # --------------------------------------------------

        for index in range(
            payment_method_count
        ):

            bank = select_issuing_bank(
                rng,
                customer,
                banks_by_country,
            )

            card_network = select_card_network(
                rng,
                bank,
            )

            card_type = weighted_choice(
                rng,
                card_type_distribution,
            )

            payment_method_status = (
                weighted_choice(
                    rng,
                    status_distribution,
                )
            )

            expiry_month, expiry_year = (
                generate_expiry(
                    rng,
                    payment_method_status,
                )
            )

            card_last_four = (
                generate_card_last_four(
                    rng,
                    existing_last_four,
                )
            )

            payment_method = {
                "payment_method_id": generate_id(
                    "pm"
                ),

                "customer_fk": customer[
                    "id"
                ],

                "issuing_bank_fk": bank[
                    "id"
                ],

                "payment_method_type": (
                    payment_method_type
                ),

                "card_network": (
                    card_network
                ),

                "card_type": card_type,

                "card_last_four": (
                    card_last_four
                ),

                "expiry_month": (
                    expiry_month
                ),

                "expiry_year": (
                    expiry_year
                ),

                "is_default": (
                    index == default_index
                ),

                "payment_method_status": (
                    payment_method_status
                ),
            }

            payment_methods.append(
                payment_method
            )

    return payment_methods


# ---------------------------------------------------------------------------
# Direct execution
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    payment_methods = (
        generate_payment_methods()
    )

    print(
        f"Generated payment methods: "
        f"{len(payment_methods):,}"
    )

    print(
        "\nFirst 5 payment methods:"
    )

    for payment_method in (
        payment_methods[:5]
    ):

        print(payment_method)