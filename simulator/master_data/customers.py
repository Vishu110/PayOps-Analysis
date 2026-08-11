import re
import unicodedata
from datetime import date
from random import Random

from faker import Faker

from simulator.utils.config_loader import (
    load_countries,
    load_generator_config,
)
from simulator.utils.id_generator import generate_id


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

COUNTRIES_CONFIG = load_countries()
GENERATOR_CONFIG = load_generator_config()["customers"]

COUNTRIES = COUNTRIES_CONFIG["countries"]


# ---------------------------------------------------------------------------
# Weighted selection
# ---------------------------------------------------------------------------

def weighted_choice(rng: Random, distribution: dict):
    """
    Select one value from a weighted configuration dictionary.
    """

    values = list(distribution.keys())

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
# Geographic generation
# ---------------------------------------------------------------------------

def generate_location(
    rng: Random,
    country: dict,
) -> tuple[str, str]:
    """
    Generate a valid state and city combination for a country.

    The city is always selected from the selected state's city list.
    """

    states = country["states"]

    state_code = rng.choice(list(states.keys()))

    state = states[state_code]

    city = rng.choice(state["cities"])

    return state["name"], city


# ---------------------------------------------------------------------------
# Signup date
# ---------------------------------------------------------------------------

def generate_signup_date(
    rng: Random,
    year_distribution: dict,
) -> date:
    """
    Generate a signup date according to the configured
    signup-year distribution.
    """

    year = int(
        weighted_choice(
            rng,
            year_distribution,
        )
    )

    start_date = date(year, 1, 1)

    # The simulator's current date is used as the upper
    # boundary for the current year.
    if year == 2026:
        end_date = date(2026, 8, 10)
    else:
        end_date = date(year, 12, 31)

    days_between = (
        end_date - start_date
    ).days

    random_day = rng.randint(
        0,
        days_between,
    )

    return date.fromordinal(
        start_date.toordinal() + random_day
    )


# ---------------------------------------------------------------------------
# Identity generation
# ---------------------------------------------------------------------------

def create_fake_instance(
    locales: str | list[str],
    seed: int,
    ) -> Faker:
    """
    Create a Faker instance using one or more locales.

    A single locale is used for most countries.
    Multiple locales allow us to model countries with
    diverse populations, such as Singapore.
    """

    fake = Faker(locales)

    fake.seed_instance(seed)

    return fake


def normalize_name(value: str) -> str:
    """
    Convert a human name into a safe email component.

    Example:
        Müller → muller
        José   → jose
    """

    normalized = unicodedata.normalize(
        "NFKD",
        value,
    )

    normalized = normalized.encode(
        "ascii",
        "ignore",
    ).decode(
        "ascii"
    )

    normalized = normalized.lower()

    return re.sub(
        r"[^a-z0-9]",
        "",
        normalized,
    )


def generate_email(
    first_name: str,
    last_name: str,
    rng: Random,
    existing_emails: set[str],
) -> str:
    """
    Generate an email address based on the customer's
    first and last name.

    Ensures uniqueness within the generated population.
    """

    first = normalize_name(first_name)
    last = normalize_name(last_name)

    # Handle names that become empty after normalization.
    if not first:
        first = "customer"

    if not last:
        last = "user"

    domains = [
        "gmail.com",
        "outlook.com",
        "yahoo.com",
        "hotmail.com",
        # "example.com",
    ]

    patterns = [
        f"{first}.{last}",
        f"{first}{last}",
        f"{first[0]}{last}",
        f"{first}{last[0]}",
        f"{first}.{last[0]}",
    ]

    for _ in range(20):

        local_part = rng.choice(patterns)
        domain = rng.choice(domains)

        email = f"{local_part}@{domain}"

        if email not in existing_emails:
            existing_emails.add(email)

            return email

    # Fallback for extremely unlikely collisions.
    counter = 1

    while True:

        email = (
            f"{first}.{last}{counter}"
            f"@example.com"
        )

        if email not in existing_emails:
            existing_emails.add(email)

            return email

        counter += 1


# ---------------------------------------------------------------------------
# Customer generation
# ---------------------------------------------------------------------------

def generate_customer(
    rng: Random,
    fake: Faker,
    country_code: str,
    existing_emails: set[str],
) -> dict:
    """
    Generate one internally consistent customer.
    """

    country = COUNTRIES[country_code]

    # --------------------------------------------------
    # Identity
    # --------------------------------------------------

    first_name = fake.first_name()
    last_name = fake.last_name()

    email = generate_email(
        first_name,
        last_name,
        rng,
        existing_emails,
    )

    # --------------------------------------------------
    # Geography
    # --------------------------------------------------

    state, city = generate_location(
        rng,
        country,
    )

    # --------------------------------------------------
    # Customer attributes
    # --------------------------------------------------

    risk_segment = weighted_choice(
        rng,
        GENERATOR_CONFIG["risk_distribution"],
    )

    customer_status = weighted_choice(
        rng,
        GENERATOR_CONFIG["status_distribution"],
    )

    signup_date = generate_signup_date(
        rng,
        GENERATOR_CONFIG[
            "signup_year_distribution"
        ],
    )

    # --------------------------------------------------
    # Record
    # --------------------------------------------------

    return {
        "customer_id": generate_id("cus"),
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "phone": fake.phone_number(),
        "country_code": country_code,
        "country_name": country["name"],
        "state": state,
        "city": city,
        "timezone": country["timezone"],
        "preferred_currency": country["currency"],
        "risk_segment": risk_segment,
        "customer_status": customer_status,
        "signup_date": signup_date,
    }


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def generate_customers(
    total_customers: int | None = None,
    seed: int = 20260810,
) -> list[dict]:
    """
    Generate the configured number of customers.

    The same seed produces the same customer attributes,
    making development runs reproducible.
    """

    if total_customers is None:
        total_customers = GENERATOR_CONFIG[
            "total_customers"
        ]

    rng = Random(seed)

    existing_emails: set[str] = set()

    customers: list[dict] = []

    # Create one Faker instance per country locale.
    fakers = {}

    for country_code, country in COUNTRIES.items():

        if "faker_locales" in country:
            locales = country["faker_locales"]
        else:
            locales = country["faker_locale"]

        locale_seed = (
            seed
            + sum(
                ord(character)
                for character in country_code
            )
        )

        fakers[country_code] = create_fake_instance(
            locales,
            locale_seed,
        )

    # Generate customers.
    for _ in range(total_customers):

        country_code = weighted_choice(
            rng,
            GENERATOR_CONFIG[
                "country_distribution"
            ],
        )

        fake = fakers[country_code]

        customer = generate_customer(
            rng,
            fake,
            country_code,
            existing_emails,
        )

        customers.append(customer)

    return customers


# ---------------------------------------------------------------------------
# Direct execution
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    customers = generate_customers()

    print(
        f"Generated customers: "
        f"{len(customers)}"
    )

    print("\nFirst 5 customers:")

    for customer in customers[:5]:
        print(customer)