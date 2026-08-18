import random

from simulator.utils.config_loader import (
    load_generator_config,
)

from simulator.transactions.lifecycle import (
    TransactionLifecycle,
)


def main():

    config = load_generator_config()

    lifecycle_config = (
        config["transactions"][
            "lifecycle"
        ]
    )

    lifecycle = TransactionLifecycle(
        lifecycle_config=lifecycle_config,
        rng=random.Random(20260818),
    )

    # --------------------------------------------------------------
    # Test multiple lifecycles
    # --------------------------------------------------------------

    sample_size = 1000

    # Use a fixed timezone-aware timestamp.
    # The lifecycle engine should preserve this
    # timezone and derive every later timestamp from it.

    from datetime import datetime
    from zoneinfo import ZoneInfo

    initiated_at = datetime(
        2026,
        8,
        18,
        19,
        4,
        33,
        217000,
        tzinfo=ZoneInfo(
            "Asia/Kolkata"
        ),
    )

    results = []

    for _ in range(sample_size):

        result = lifecycle.generate(
            initiated_at
        )

        results.append(result)

    # --------------------------------------------------------------
    # Validate lifecycle results
    # --------------------------------------------------------------

    scenario_counts = {}

    for result in results:

        scenario = result[
            "scenario"
        ]

        scenario_counts[
            scenario
        ] = (
            scenario_counts.get(
                scenario,
                0,
            )
            + 1
        )

        events = result[
            "events"
        ]

        # Must contain at least PENDING
        if not events:
            raise AssertionError(
                "Lifecycle generated no events."
            )

        # First event must be PENDING
        if events[0][
            "event_status"
        ] != "PENDING":
            raise AssertionError(
                "Lifecycle must begin with PENDING."
            )

        # First event must equal transaction
        # initiation timestamp
        if events[0][
            "event_at"
        ] != initiated_at:
            raise AssertionError(
                "PENDING event timestamp does not "
                "match transaction initiation."
            )

        # ----------------------------------------------------------
        # Sequence validation
        # ----------------------------------------------------------

        expected_sequence = 1

        for event in events:

            if event[
                "sequence_number"
            ] != expected_sequence:

                raise AssertionError(
                    "Lifecycle sequence numbers "
                    "are not continuous."
                )

            expected_sequence += 1

        # ----------------------------------------------------------
        # Chronological validation
        # ----------------------------------------------------------

        previous_timestamp = (
            events[0]["event_at"]
        )

        for event in events[1:]:

            current_timestamp = (
                event["event_at"]
            )

            if current_timestamp <= previous_timestamp:

                raise AssertionError(
                    "Lifecycle timestamps are not "
                    "strictly chronological."
                )

            if (
                current_timestamp.tzinfo
                is None
            ):

                raise AssertionError(
                    "Lifecycle timestamp is "
                    "timezone-naive."
                )

            previous_timestamp = (
                current_timestamp
            )

        # ----------------------------------------------------------
        # Terminal status validation
        # ----------------------------------------------------------

        final_status = result[
            "final_status"
        ]

        if final_status not in {
            "CAPTURED",
            "FAILED",
            "CANCELED",
        }:

            raise AssertionError(
                "Lifecycle does not terminate "
                "in a valid terminal status."
            )

        if (
            result["completed_at"]
            != events[-1]["event_at"]
        ):

            raise AssertionError(
                "completed_at must equal the "
                "final lifecycle event timestamp."
            )

        # ----------------------------------------------------------
        # Scenario/path validation
        # ----------------------------------------------------------

        configured_path = (
            lifecycle_config[
                "paths"
            ][scenario]
        )

        actual_path = [
            event["event_status"]
            for event in events
        ]

        if actual_path != configured_path:

            raise AssertionError(
                f"Generated path does not match "
                f"configured path for {scenario}."
            )

    # --------------------------------------------------------------
    # Print distribution
    # --------------------------------------------------------------

    print(
        f"Generated lifecycles: "
        f"{sample_size:,}"
    )

    print()
    print(
        "Lifecycle scenario distribution:"
    )

    for scenario, count in sorted(
        scenario_counts.items()
    ):

        percentage = (
            count
            / sample_size
            * 100
        )

        print(
            f"{scenario}: "
            f"{count:,} "
            f"({percentage:.2f}%)"
        )

    print()
    print(
        "All transaction lifecycle "
        "validation tests passed."
    )


if __name__ == "__main__":
    main()