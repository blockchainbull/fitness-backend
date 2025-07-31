// scripts/run_migration.js
const { Pool } = require('pg');
const fs = require('fs');
const path = require('path');

// Database configuration
const pool = new Pool({
  user: process.env.DB_USERNAME || 'health_ai_user',
  password: process.env.DB_PASSWORD || 'health_ai_password', 
  host: process.env.DB_HOST || 'localhost',
  port: process.env.DB_PORT || 5432,
  database: process.env.DB_NAME || 'health_ai_db',
});

async function runMigration() {
  const client = await pool.connect();
  
  try {
    console.log('Running period cycle fields migration...');
    
    // Read the SQL migration file
    const migrationSQL = fs.readFileSync(
      path.join(__dirname, 'add_period_cycle_fields.sql'), 
      'utf8'
    );
    
    // Execute the migration
    await client.query(migrationSQL);
    
    console.log('✅ Migration completed successfully!');
    
    // Verify the new columns exist
    const verification = await client.query(`
      SELECT column_name, data_type, is_nullable, column_default 
      FROM information_schema.columns 
      WHERE table_name = 'users' 
      AND column_name IN ('has_periods', 'last_period_date', 'cycle_length', 'cycle_length_regular', 'pregnancy_status', 'period_tracking_preference')
      ORDER BY column_name;
    `);
    
    console.log('\n📋 New columns added:');
    verification.rows.forEach(row => {
      console.log(`  - ${row.column_name}: ${row.data_type} ${row.is_nullable === 'YES' ? '(nullable)' : '(not null)'}`);
    });
    
  } catch (error) {
    console.error('❌ Migration failed:', error);
    throw error;
  } finally {
    client.release();
    await pool.end();
  }
}

// Run the migration
runMigration()
  .then(() => {
    console.log('🎉 All done!');
    process.exit(0);
  })
  .catch((error) => {
    console.error('💥 Migration script failed:', error);
    process.exit(1);
  });