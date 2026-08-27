from __future__ import annotations

from datetime import date
import calendar
import random


class TransactionVolumeGenerator:
    """
    Generate realistic daily transaction volumes using:

    - long-term annual growth
    - weekday effects
    - monthly seasonality
    - payment/business cycles
    - controlled random variation

    The generator is deterministic when supplied with a fixed seed.
    """

    def __init__(
        self,
        volume_config: dict,
        rng: random.Random | None = None,
    ):
        self.config = volume_config
        self.rng = rng or random.Random()

    # ------------------------------------------------------------------
    # Annual growth
    # ------------------------------------------------------------------

    def _annual_growth_multiplier(
        self,
        transaction_date: date,
    ) -> float:

        start_date = date.fromisoformat(
            str(
                self.config.get(
                    "_historical_start_date",
                    transaction_date,
                )
            )
        )

        annual_growth_rates = {
            int(year): float(rate)
            for year, rate
            in self.config[
                "annual_growth_rates"
            ].items()
        }

        multiplier = 1.0

        for year in range(
            start_date.year + 1,
            transaction_date.year + 1,
        ):

            growth_rate = annual_growth_rates.get(
                year,
                0.0,
            )

            multiplier *= (
                1 + growth_rate
            )

        return multiplier

    # ------------------------------------------------------------------
    # Weekday
    # ------------------------------------------------------------------

    def _weekday_multiplier(
        self,
        transaction_date: date,
    ) -> float:

        weekday_name = (
            transaction_date.strftime("%A")
        )

        return float(
            self.config[
                "weekday_multipliers"
            ][weekday_name]
        )

    # ------------------------------------------------------------------
    # Month
    # ------------------------------------------------------------------

    def _monthly_multiplier(
        self,
        transaction_date: date,
    ) -> float:

        month_key = (
            f"{transaction_date.month:02d}"
        )

        return float(
            self.config[
                "monthly_multipliers"
            ][month_key]
        )

    # ------------------------------------------------------------------
    # Payment / business cycle
    # ------------------------------------------------------------------

    def _payment_cycle_multiplier(
        self,
        transaction_date: date,
    ) -> float:

        cycle_config = self.config[
            "payment_cycle"
        ]

        if not cycle_config.get(
            "enabled",
            False,
        ):
            return 1.0

        multiplier = 1.0

        early_month_days = int(
            cycle_config[
                "early_month_days"
            ]
        )

        month_end_days = int(
            cycle_config[
                "month_end_days"
            ]
        )

        if (
            transaction_date.day
            <= early_month_days
        ):
            multiplier *= float(
                cycle_config[
                    "early_month_multiplier"
                ]
            )

        last_day = calendar.monthrange(
            transaction_date.year,
            transaction_date.month,
        )[1]

        if (
            transaction_date.day
            > last_day - month_end_days
        ):
            multiplier *= float(
                cycle_config[
                    "month_end_multiplier"
                ]
            )

        return multiplier

    # ------------------------------------------------------------------
    # Random variation
    # ------------------------------------------------------------------

    def _random_variation(self) -> float:

        random_config = self.config[
            "random_variation"
        ]

        minimum = float(
            random_config[
                "min_multiplier"
            ]
        )

        maximum = float(
            random_config[
                "max_multiplier"
            ]
        )

        return self.rng.uniform(
            minimum,
            maximum,
        )

    # ------------------------------------------------------------------
    # Daily volume
    # ------------------------------------------------------------------

    def generate_daily_volume(
        self,
        transaction_date: date,
    ) -> int:

        baseline = float(
            self.config[
                "baseline_daily_volume"
            ]
        )

        growth = (
            self._annual_growth_multiplier(
                transaction_date
            )
        )

        weekday = (
            self._weekday_multiplier(
                transaction_date
            )
        )

        monthly = (
            self._monthly_multiplier(
                transaction_date
            )
        )

        payment_cycle = (
            self._payment_cycle_multiplier(
                transaction_date
            )
        )

        random_variation = (
            self._random_variation()
        )

        volume = (
            baseline
            * growth
            * weekday
            * monthly
            * payment_cycle
            * random_variation
        )

        return max(
            1,
            int(round(volume)),
        )