import random
from datetime import date, timedelta

from simulator.transactions.volume import (
    TransactionVolumeGenerator,
)

from simulator.utils.config_loader import (
    load_generator_config,
)


def main():

    config = load_generator_config()

    simulation_config = (
        config["simulation"]
    )

    volume_config = dict(
        simulation_config["volume"]
    )

    volume_config[
        "_historical_start_date"
    ] = simulation_config[
        "historical_start_date"
    ]

    generator = (
        TransactionVolumeGenerator(
            volume_config=volume_config,
            rng=random.Random(
                volume_config[
                    "random_seed"
                ]
            ),
        )
    )

    # --------------------------------------------------------------
    # Generate one month
    # --------------------------------------------------------------

    start_date = date(
        2026,
        1,
        1,
    )

    volumes = {}

    for day_offset in range(31):

        transaction_date = (
            start_date
            + timedelta(
                days=day_offset
            )
        )

        volumes[
            transaction_date
        ] = generator.generate_daily_volume(
            transaction_date
        )

    # --------------------------------------------------------------
    # Basic validation
    # --------------------------------------------------------------

    if len(volumes) != 31:
        raise AssertionError(
            "Incorrect number of daily volumes."
        )

    if any(
        volume <= 0
        for volume in volumes.values()
    ):
        raise AssertionError(
            "Daily transaction volume must "
            "always be positive."
        )

    # --------------------------------------------------------------
    # Validate variation
    # --------------------------------------------------------------

    unique_volumes = set(
        volumes.values()
    )

    if len(unique_volumes) < 20:
        raise AssertionError(
            "Daily volumes do not contain "
            "enough natural variation."
        )

    # --------------------------------------------------------------
    # Display results
    # --------------------------------------------------------------

    print(
        "Generated daily volumes:"
    )

    for (
        transaction_date,
        volume,
    ) in volumes.items():

        print(
            f"{transaction_date}: "
            f"{volume:,}"
        )

    print()

    print(
        f"Minimum volume: "
        f"{min(volumes.values()):,}"
    )

    print(
        f"Maximum volume: "
        f"{max(volumes.values()):,}"
    )

    print(
        f"Average volume: "
        f"{sum(volumes.values()) / len(volumes):,.1f}"
    )

    print()
    print(
        "Transaction volume "
        "validation passed."
    )


if __name__ == "__main__":
    main()