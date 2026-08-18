from datetime import datetime, timedelta
import random


class TransactionLifecycle:

    TERMINAL_STATUSES = {
        "CAPTURED",
        "FAILED",
        "CANCELED",
    }

    def __init__(
        self,
        lifecycle_config: dict,
        rng: random.Random | None = None,
    ):
        self.config = lifecycle_config
        self.rng = rng or random.Random()

        self.scenario_distribution = (
            lifecycle_config["scenario_distribution"]
        )

        self.paths = lifecycle_config["paths"]

        self.event_delays = (
            lifecycle_config["event_delays_seconds"]
        )

    # ------------------------------------------------------------------
    # Scenario selection
    # ------------------------------------------------------------------

    def _select_scenario(self) -> str:

        scenarios = list(
            self.scenario_distribution.keys()
        )

        weights = [
            float(
                self.scenario_distribution[
                    scenario
                ]["weight"]
            )
            for scenario in scenarios
        ]

        return self.rng.choices(
            scenarios,
            weights=weights,
            k=1,
        )[0]

    # ------------------------------------------------------------------
    # Delay selection
    # ------------------------------------------------------------------

    def _get_transition_key(
        self,
        current_status: str,
        next_status: str,
    ) -> str:

        return (
            f"{current_status}_TO_{next_status}"
        )

    def _sample_delay(
        self,
        current_status: str,
        next_status: str,
    ) -> float:

        transition_key = (
            self._get_transition_key(
                current_status,
                next_status,
            )
        )

        if transition_key not in self.event_delays:
            raise ValueError(
                "Missing lifecycle delay configuration "
                f"for transition: {transition_key}"
            )

        configuration = self.event_delays[
            transition_key
        ]

        minimum = float(
            configuration["min"]
        )

        maximum = float(
            configuration["max"]
        )

        return self.rng.uniform(
            minimum,
            maximum,
        )

    # ------------------------------------------------------------------
    # Generate lifecycle
    # ------------------------------------------------------------------

    def generate(
        self,
        initiated_at: datetime,
    ) -> dict:

        if initiated_at.tzinfo is None:
            raise ValueError(
                "initiated_at must be timezone-aware."
            )

        scenario = self._select_scenario()

        path = self.paths[scenario]

        if not path:
            raise ValueError(
                f"Lifecycle path is empty: {scenario}"
            )

        if path[0] != "PENDING":
            raise ValueError(
                f"Lifecycle path '{scenario}' "
                "must begin with PENDING."
            )

        events = []

        current_time = initiated_at

        # --------------------------------------------------------------
        # First event: PENDING
        # --------------------------------------------------------------

        events.append(
            {
                "event_status": "PENDING",
                "event_at": current_time,
                "sequence_number": 1,
            }
        )

        # --------------------------------------------------------------
        # Subsequent events
        # --------------------------------------------------------------

        for sequence_number in range(
            2,
            len(path) + 1,
        ):

            current_status = path[
                sequence_number - 2
            ]

            next_status = path[
                sequence_number - 1
            ]

            delay_seconds = (
                self._sample_delay(
                    current_status,
                    next_status,
                )
            )

            current_time = (
                current_time
                + timedelta(
                    seconds=delay_seconds
                )
            )

            events.append(
                {
                    "event_status": next_status,
                    "event_at": current_time,
                    "sequence_number":
                        sequence_number,
                }
            )

        final_status = events[-1][
            "event_status"
        ]

        if final_status not in self.TERMINAL_STATUSES:
            raise ValueError(
                f"Lifecycle '{scenario}' "
                f"ended in non-terminal status: "
                f"{final_status}"
            )

        completed_at = None

        if final_status in self.TERMINAL_STATUSES:
            completed_at = events[-1][
                "event_at"
            ]

        return {
            "scenario": scenario,
            "events": events,
            "final_status": final_status,
            "completed_at": completed_at,
        }