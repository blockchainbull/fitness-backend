// scripts/run_period_length_migration.js
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
    console.log('🔄 Running period length field migration...');
    
    // Read the SQL migration file
    const migrationSQL = fs.readFileSync(
      path.join(__dirname, 'add_period_length_field.sql'), 
      'utf8'
    );
    
    // Execute the migration
    await client.query(migrationSQL);
    
    console.log('✅ Migration completed successfully!');
    
    // Verify the new column exists
    const verification = await client.query(`
      SELECT column_name, data_type, column_default 
      FROM information_schema.columns 
      WHERE table_name = 'users' 
      AND column_name = 'period_length';
    `);
    
    if (verification.rows.length > 0) {
      console.log('\n📋 New column added:');
      const col = verification.rows[0];
      console.log(`  - ${col.column_name}: ${col.data_type} (default: ${col.column_default})`);
    }
    
    // Check how many female users were updated
    const femaleUsers = await client.query(`
      SELECT COUNT(*) as count 
      FROM users 
      WHERE LOWER(gender) = 'female';
    `);
    
    console.log(`\n👩 Updated ${femaleUsers.rows[0].count} female users with default period_length = 5`);
    
    // Show sample of updated users
    const sampleUsers = await client.query(`
      SELECT id, name, email, gender, period_length, cycle_length, has_periods
      FROM users 
      WHERE LOWER(gender) = 'female'
      LIMIT 5;
    `);
    
    if (sampleUsers.rows.length > 0) {
      console.log('\n📊 Sample of updated female users:');
      sampleUsers.rows.forEach(user => {
        console.log(`  - ${user.name} (${user.email}): period_length=${user.period_length}, cycle_length=${user.cycle_length}`);
      });
    }
    
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
    console.log('\n🎉 Period length migration completed!');
    process.exit(0);
  })
  .catch((error) => {
    console.error('💥 Migration script failed:', error);
    process.exit(1);
  });