// scripts/run_date_type_migration.js
const { Pool } = require('pg');
const fs = require('fs');
const path = require('path');

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
    console.log('🔄 Running date type fix migration...');
    
    // First, check current column types
    const checkTypes = await client.query(`
      SELECT column_name, data_type 
      FROM information_schema.columns 
      WHERE table_name = 'users' 
      AND column_name IN ('last_period_date', 'starting_weight_date', 'created_at', 'updated_at');
    `);
    
    console.log('\n📋 Current column types:');
    checkTypes.rows.forEach(row => {
      console.log(`  - ${row.column_name}: ${row.data_type}`);
    });
    
    // Run the migration
    const migrationSQL = fs.readFileSync(
      path.join(__dirname, 'fix_period_date_types.sql'), 
      'utf8'
    );
    
    await client.query(migrationSQL);
    
    console.log('\n✅ Migration completed successfully!');
    
    // Verify the changes
    const verifyTypes = await client.query(`
      SELECT column_name, data_type 
      FROM information_schema.columns 
      WHERE table_name = 'users' 
      AND column_name IN ('last_period_date', 'period_length');
    `);
    
    console.log('\n📋 Updated column types:');
    verifyTypes.rows.forEach(row => {
      console.log(`  - ${row.column_name}: ${row.data_type}`);
    });
    
  } catch (error) {
    console.error('❌ Migration failed:', error);
    throw error;
  } finally {
    client.release();
    await pool.end();
  }
}

runMigration()
  .then(() => {
    console.log('\n🎉 Date type migration completed!');
    process.exit(0);
  })
  .catch((error) => {
    console.error('💥 Migration script failed:', error);
    process.exit(1);
  });