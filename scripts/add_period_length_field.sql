-- Migration to add period_length field to users table
-- scripts/add_period_length_field.sql

BEGIN;

-- Add period_length column to users table
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS period_length INTEGER DEFAULT 5;

-- Update existing female users with default period length of 5
UPDATE users 
SET period_length = 5 
WHERE LOWER(gender) = 'female' 
AND period_length IS NULL;

-- Add comment to document the field
COMMENT ON COLUMN users.period_length IS 'Average menstrual period duration in days (default: 5)';

-- Create index for better query performance on female users with periods
CREATE INDEX IF NOT EXISTS idx_users_gender_periods 
ON users(gender, has_periods) 
WHERE LOWER(gender) = 'female';

COMMIT;

-- Verify the changes
SELECT 
    u.id,
    u.name,
    u.email,
    u.gender,
    u.has_periods,
    u.period_length,
    u.cycle_length,
    u.last_period_date
FROM users u
WHERE LOWER(u.gender) = 'female'
LIMIT 10;