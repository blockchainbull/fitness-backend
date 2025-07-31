-- Add period cycle fields to users table
-- scripts/add_period_cycle_fields.sql

BEGIN;

-- Add new period cycle columns to users table
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS has_periods BOOLEAN DEFAULT NULL,
ADD COLUMN IF NOT EXISTS last_period_date TIMESTAMP DEFAULT NULL,
ADD COLUMN IF NOT EXISTS cycle_length INTEGER DEFAULT NULL,
ADD COLUMN IF NOT EXISTS cycle_length_regular BOOLEAN DEFAULT NULL,
ADD COLUMN IF NOT EXISTS pregnancy_status VARCHAR(50) DEFAULT NULL,
ADD COLUMN IF NOT EXISTS period_tracking_preference VARCHAR(50) DEFAULT NULL;

-- Add indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_users_has_periods ON users(has_periods);
CREATE INDEX IF NOT EXISTS idx_users_pregnancy_status ON users(pregnancy_status);
CREATE INDEX IF NOT EXISTS idx_users_period_tracking ON users(period_tracking_preference);

-- Add comments to document the new fields
COMMENT ON COLUMN users.has_periods IS 'Whether the user currently has menstrual periods';
COMMENT ON COLUMN users.last_period_date IS 'Date of the users last menstrual period';
COMMENT ON COLUMN users.cycle_length IS 'Average menstrual cycle length in days';
COMMENT ON COLUMN users.cycle_length_regular IS 'Whether the users cycles are regular';
COMMENT ON COLUMN users.pregnancy_status IS 'Current pregnancy/reproductive status';
COMMENT ON COLUMN users.period_tracking_preference IS 'Users preference for period tracking features';

COMMIT;

-- Verify the changes
SELECT column_name, data_type, is_nullable, column_default 
FROM information_schema.columns 
WHERE table_name = 'users' 
AND column_name IN ('has_periods', 'last_period_date', 'cycle_length', 'cycle_length_regular', 'pregnancy_status', 'period_tracking_preference')
ORDER BY column_name;