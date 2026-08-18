-- ============================================================================
-- Transaction type
-- ============================================================================

DO $$
BEGIN

    IF NOT EXISTS (
        SELECT 1
        FROM pg_type
        WHERE typname = 'transaction_type_enum'
    ) THEN

        CREATE TYPE transaction_type_enum AS ENUM (
            'PAYMENT'
        );

    END IF;

END
$$;


-- ============================================================================
-- Transaction status
-- ============================================================================

DO $$
BEGIN

    IF NOT EXISTS (
        SELECT 1
        FROM pg_type
        WHERE typname = 'transaction_status_enum'
    ) THEN

        CREATE TYPE transaction_status_enum AS ENUM (
            'PENDING',
            'REQUIRES_ACTION',
            'PROCESSING',
            'AUTHORIZED',
            'REQUIRES_CAPTURE',
            'CAPTURED',
            'FAILED',
            'CANCELED'
        );

    END IF;

END
$$;


-- ============================================================================
-- Transaction failure reason
-- ============================================================================

DO $$
BEGIN

    IF NOT EXISTS (
        SELECT 1
        FROM pg_type
        WHERE typname = 'transaction_failure_reason_enum'
    ) THEN

        CREATE TYPE transaction_failure_reason_enum AS ENUM (
            'INSUFFICIENT_FUNDS',
            'DO_NOT_HONOR',
            'EXPIRED_CARD',
            'INVALID_CARD',
            'FRAUD_BLOCK',
            'PROCESSOR_ERROR',
            'NETWORK_ERROR'
        );

    END IF;

END
$$;