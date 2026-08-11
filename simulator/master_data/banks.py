from simulator.utils.config_loader import (
    load_banks,
    load_countries,
    load_generator_config,
)
from simulator.utils.id_generator import generate_id


COUNTRIES_CONFIG = load_countries()
GENERATOR_CONFIG = load_generator_config()
BANKS_CONFIG = load_banks()

COUNTRIES = COUNTRIES_CONFIG["countries"]
BANKS = BANKS_CONFIG["banks"]


def generate_banks() -> list[dict]:
    """
    Generate issuing-bank master data from reference configuration.
    """

    banks = []

    default_status = GENERATOR_CONFIG[
        "banks"
    ]["default_status"]

    for bank_key, bank in BANKS.items():

        country_code = bank["country_code"]

        country = COUNTRIES.get(country_code)

        if country is None:
            raise ValueError(
                f"Unknown country '{country_code}' "
                f"for bank '{bank_key}'."
            )

        banks.append(
            {
                "bank_id": generate_id("bank"),

                "bank_name": bank["name"],

                "bank_code": bank["bank_code"],

                "country_code": country_code,

                "country_name": country["name"],

                "supported_card_networks": (
                    bank["supported_card_networks"]
                ),

                "bank_status": default_status,
            }
        )

    return banks