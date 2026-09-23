CREATE TABLE fx_rates (
    rate_date DATE NOT NULL,
    source_currency CHAR(3) NOT NULL,
    target_currency CHAR(3) NOT NULL,
    fx_rate NUMERIC(20, 10) NOT NULL,

    CONSTRAINT pk_fx_rates
        PRIMARY KEY (
            rate_date,
            source_currency,
            target_currency
        ),

    CONSTRAINT chk_fx_rates_positive
        CHECK (fx_rate > 0),

    CONSTRAINT chk_fx_rates_currency_format
        CHECK (
            source_currency = UPPER(source_currency)
            AND target_currency = UPPER(target_currency)
        )
);