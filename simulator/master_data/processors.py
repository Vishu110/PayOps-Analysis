from simulator.utils.config_loader import (
    load_countries,
    load_generator_config,
    load_processors,
)
from simulator.utils.id_generator import generate_id


COUNTRIES_CONFIG = load_countries()
GENERATOR_CONFIG = load_generator_config()
PROCESSORS_CONFIG = load_processors()

COUNTRIES = COUNTRIES_CONFIG["countries"]
PROCESSORS = PROCESSORS_CONFIG["processors"]


def generate_processors() -> list[dict]:
    """
    Generate processor master data from reference configuration.

    Processor capabilities and commercial attributes are treated
    as master data. Operational states such as DEGRADED and DOWN
    will be simulated later through processor events.
    """

    processors = []

    default_status = GENERATOR_CONFIG[
        "processors"
    ]["default_status"]

    for processor_key, processor in PROCESSORS.items():

        headquarters_country_code = (
            processor["headquarters_country_code"]
        )

        headquarters_country = COUNTRIES.get(
            headquarters_country_code
        )

        if headquarters_country is None:
            raise ValueError(
                f"Unknown headquarters country "
                f"'{headquarters_country_code}' "
                f"for processor '{processor_key}'."
            )

        processors.append(
            {
                "processor_id": generate_id("proc"),

                "processor_name": processor["name"],

                "headquarters_country_code": (
                    headquarters_country_code
                ),

                "headquarters_country_name": (
                    headquarters_country["name"]
                ),

                "supported_regions": (
                    processor["supported_regions"]
                ),

                "supported_card_networks": (
                    processor["supported_card_networks"]
                ),

                "default_processing_fee_percentage": (
                    processor[
                        "default_processing_fee_percentage"
                    ]
                ),

                "processor_status": default_status,
            }
        )

    return processors