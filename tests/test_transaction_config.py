from datetime import date

from simulator.utils.config_loader import load_generator_config


GENERATOR_CONFIG = load_generator_config()


def validate_weights(
    distribution: dict,
    name: str,
    expected_total: float = 100.0,
) -> None:
    """
    Validate that a configuration distribution contains
    positive weights whose total matches the expected value.
    """

    if not distribution:
        raise AssertionError(
            f"{name} distribution is empty."
        )

    weights = []

    for value, configuration in distribution.items():

        if "weight" not in configuration:
            raise AssertionError(
                f"{name}: '{value}' is missing a weight."
            )

        weight = float(configuration["weight"])

        if weight <= 0:
            raise AssertionError(
                f"{name}: '{value}' has invalid weight: {weight}"
            )

        weights.append(weight)

    total = sum(weights)

    if abs(total - expected_total) > 0.01:
        raise AssertionError(
            f"{name} weights must total "
            f"{expected_total}, got {total:.2f}"
        )


def main():

    transactions = GENERATOR_CONFIG.get(
        "transactions"
    )

    if transactions is None:
        raise AssertionError(
            "Missing 'transactions' configuration."
        )

    # --------------------------------------------------------------
    # Historical simulation date
    # --------------------------------------------------------------

    historical_start_date = date.fromisoformat(
        str(
            transactions[
                "historical_start_date"
            ]
        )
    )

    simulation_date = date.fromisoformat(
        str(
            GENERATOR_CONFIG[
                "simulation"
            ]["current_date"]
        )
    )

    if historical_start_date > simulation_date:
        raise AssertionError(
            "Historical start date cannot be after "
            "simulation current date."
        )

    # --------------------------------------------------------------
    # Transaction type distribution
    # --------------------------------------------------------------

    transaction_types = transactions[
        "transaction_type_distribution"
    ]

    validate_weights(
        transaction_types,
        "Transaction type",
    )

    if "PAYMENT" not in transaction_types:
        raise AssertionError(
            "PAYMENT must exist in transaction type distribution."
        )

    # --------------------------------------------------------------
    # Daily volume
    # --------------------------------------------------------------

    daily_volume = transactions[
        "daily_volume"
    ]

    average_volume = float(
        daily_volume["average"]
    )

    if average_volume <= 0:
        raise AssertionError(
            "Daily average transaction volume "
            "must be greater than zero."
        )

    variation = daily_volume[
        "variation"
    ]

    min_multiplier = float(
        variation["min_multiplier"]
    )

    max_multiplier = float(
        variation["max_multiplier"]
    )

    if min_multiplier <= 0:
        raise AssertionError(
            "Minimum volume multiplier must "
            "be greater than zero."
        )

    if max_multiplier <= min_multiplier:
        raise AssertionError(
            "Maximum volume multiplier must be "
            "greater than minimum multiplier."
        )

    # --------------------------------------------------------------
    # Quantity distribution
    # --------------------------------------------------------------

    quantity_distribution = transactions[
        "quantity_distribution"
    ]

    validate_weights(
        quantity_distribution,
        "Quantity",
    )

    for quantity in quantity_distribution:

        quantity_value = int(quantity)

        if quantity_value < 1:
            raise AssertionError(
                f"Invalid transaction quantity: "
                f"{quantity_value}"
            )

    # --------------------------------------------------------------
    # Geography distribution
    # --------------------------------------------------------------

    geography = transactions[
        "geography"
    ]

    validate_weights(
        geography,
        "Geography",
    )

    required_geographies = {
        "domestic",
        "cross_border",
    }

    if set(geography.keys()) != required_geographies:
        raise AssertionError(
            "Geography distribution must contain "
            "'domestic' and 'cross_border'."
        )

    # --------------------------------------------------------------
    # Initiation hour distribution
    # --------------------------------------------------------------

    initiation = transactions[
        "initiation"
    ]

    hour_distribution = initiation[
        "hour_distribution"
    ]

    if len(hour_distribution) != 24:
        raise AssertionError(
            "Initiation hour distribution must "
            "contain exactly 24 hours."
        )

    expected_hours = set(range(24))

    actual_hours = set(
        int(hour)
        for hour in hour_distribution.keys()
    )

    if actual_hours != expected_hours:
        missing = expected_hours - actual_hours
        extra = actual_hours - expected_hours

        raise AssertionError(
            "Invalid initiation hours. "
            f"Missing: {sorted(missing)}, "
            f"Extra: {sorted(extra)}"
        )

    for hour, configuration in (
        hour_distribution.items()
    ):

        weight = configuration.get(
            "weight"
        )

        if weight is None:
            raise AssertionError(
                f"Hour '{hour}' is missing a weight."
            )

        if float(weight) <= 0:
            raise AssertionError(
                f"Hour '{hour}' has invalid "
                f"weight: {weight}"
            )

    # --------------------------------------------------------------
    # Lifecycle configuration
    # --------------------------------------------------------------

    lifecycle = transactions.get(
        "lifecycle"
    )

    if lifecycle is None:
        raise AssertionError(
            "Missing transaction lifecycle configuration."
        )

    scenario_distribution = lifecycle.get(
        "scenario_distribution"
    )

    if not scenario_distribution:
        raise AssertionError(
            "Lifecycle scenario distribution is empty."
        )

    validate_weights(
        scenario_distribution,
        "Lifecycle scenario",
    )

    paths = lifecycle.get(
        "paths"
    )

    if not paths:
        raise AssertionError(
            "Lifecycle paths are missing."
        )

    if set(paths.keys()) != set(
        scenario_distribution.keys()
    ):
        raise AssertionError(
            "Lifecycle scenario distribution and "
            "lifecycle paths must contain the "
            "same scenarios."
        )

    required_statuses = {
        "PENDING",
        "PROCESSING",
        "AUTHORIZED",
        "REQUIRES_CAPTURE",
        "CAPTURED",
        "REQUIRES_ACTION",
        "FAILED",
        "CANCELED",
    }

    for scenario, path in paths.items():

        if not path:
            raise AssertionError(
                f"Lifecycle path '{scenario}' is empty."
            )

        if path[0] != "PENDING":
            raise AssertionError(
                f"Lifecycle path '{scenario}' "
                "must begin with PENDING."
            )

        for status in path:

            if status not in required_statuses:
                raise AssertionError(
                    f"Lifecycle path '{scenario}' "
                    f"contains invalid status: {status}"
                )

        if path[-1] not in {
            "CAPTURED",
            "FAILED",
            "CANCELED",
        }:
            raise AssertionError(
                f"Lifecycle path '{scenario}' "
                "must terminate in CAPTURED, "
                "FAILED, or CANCELED."
            )

    # --------------------------------------------------------------
    # Event delay configuration
    # --------------------------------------------------------------

    event_delays = lifecycle.get(
        "event_delays_seconds"
    )

    if not event_delays:
        raise AssertionError(
            "Lifecycle event delay configuration "
            "is missing."
        )

    for transition, delay in event_delays.items():

        minimum = float(
            delay["min"]
        )

        maximum = float(
            delay["max"]
        )

        if minimum < 0:
            raise AssertionError(
                f"{transition}: minimum delay "
                "cannot be negative."
            )

        if maximum <= minimum:
            raise AssertionError(
                f"{transition}: maximum delay "
                "must be greater than minimum."
            )

    print(
        "Lifecycle scenario configuration validated."
    )

    print(
        "Lifecycle path configuration validated."
    )

    print(
        "Lifecycle event delay configuration validated."
    )


    # --------------------------------------------------------------
    # Payment attempt / retry configuration
    # --------------------------------------------------------------

    attempts = transactions.get(
        "attempts"
    )

    if attempts is None:
        raise AssertionError(
            "Missing transaction attempts configuration."
        )

    max_attempts = int(
        attempts["max_attempts"]
    )

    if max_attempts < 1:
        raise AssertionError(
            "max_attempts must be at least 1."
        )

    retry_policy = attempts.get(
        "retry_policy"
    )

    if not retry_policy:
        raise AssertionError(
            "Retry policy is missing."
        )

    expected_retry_scenarios = {
        "AUTHORIZATION_FAILURE",
        "PROCESSING_FAILURE",
        "CAPTURE_FAILURE",
        "CANCELED",
    }

    if set(retry_policy.keys()) != (
        expected_retry_scenarios
    ):
        raise AssertionError(
            "Retry policy scenarios do not match "
            "the expected failure scenarios."
        )

    for scenario, policy in (
        retry_policy.items()
    ):

        if "retryable" not in policy:
            raise AssertionError(
                f"{scenario} is missing retryable flag."
            )

        if "retry_probability" not in policy:
            raise AssertionError(
                f"{scenario} is missing retry probability."
            )

        probability = float(
            policy["retry_probability"]
        )

        if probability < 0 or probability > 100:
            raise AssertionError(
                f"{scenario} has invalid retry "
                f"probability: {probability}"
            )

        if (
            policy["retryable"] is False
            and probability != 0
        ):
            raise AssertionError(
                f"{scenario} is not retryable but "
                f"has probability {probability}."
            )

    retry_delay = attempts.get(
        "retry_delay_seconds"
    )

    if not retry_delay:
        raise AssertionError(
            "Retry delay configuration is missing."
        )

    retry_min = float(
        retry_delay["min"]
    )

    retry_max = float(
        retry_delay["max"]
    )

    if retry_min < 0:
        raise AssertionError(
            "Retry minimum delay cannot be negative."
        )

    if retry_max <= retry_min:
        raise AssertionError(
            "Retry maximum delay must be greater "
            "than retry minimum delay."
        )

    print(
        "Payment attempt/retry configuration validated."
    )

    # --------------------------------------------------------------
    # Final output
    # --------------------------------------------------------------

    print(
        "Historical start date:",
        historical_start_date,
    )

    print(
        "Simulation current date:",
        simulation_date,
    )

    print(
        "Expected average daily volume:",
        average_volume,
    )

    print(
        "Quantity distribution validated."
    )

    print(
        "Geography distribution validated."
    )

    print(
        "24-hour initiation distribution validated."
    )

    print(
        "All transaction configuration "
        "validation tests passed."
    )


if __name__ == "__main__":
    main()