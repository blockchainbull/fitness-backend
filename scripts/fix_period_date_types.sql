-- scripts/fix_period_date_types.sql
BEGIN;

-- Ensure last_period_date is properly typed as TIMESTAMP
ALTER TABLE users 
ALTER COLUMN last_period_date TYPE TIMESTAMP USING last_period_date::TIMESTAMP;

-- Ensure period_tracking dates are properly typed
ALTER TABLE period_tracking
ALTER COLUMN start_date TYPE TIMESTAMP USING start_date::TIMESTAMP,
ALTER COLUMN end_date TYPE TIMESTAMP USING end_date::TIMESTAMP;

COMMIT;