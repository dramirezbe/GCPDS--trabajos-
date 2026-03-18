import { pool } from './connection';

async function addAuditColumns() {
  try {
    console.log('🔄 Adding audit columns to database tables...\n');

    // 1. Add created_by and updated_by to sensors table
    console.log('📋 Table: sensors');
    await pool.query(`
      ALTER TABLE sensors 
      ADD COLUMN IF NOT EXISTS created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
      ADD COLUMN IF NOT EXISTS updated_by INTEGER REFERENCES users(id) ON DELETE SET NULL
    `);
    await pool.query(`CREATE INDEX IF NOT EXISTS idx_sensors_created_by ON sensors(created_by)`);
    await pool.query(`CREATE INDEX IF NOT EXISTS idx_sensors_updated_by ON sensors(updated_by)`);
    console.log('  ✅ Added created_by and updated_by columns with foreign keys\n');

    // 2. Add created_by and updated_by to antennas table
    console.log('📋 Table: antennas');
    await pool.query(`
      ALTER TABLE antennas 
      ADD COLUMN IF NOT EXISTS created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
      ADD COLUMN IF NOT EXISTS updated_by INTEGER REFERENCES users(id) ON DELETE SET NULL
    `);
    await pool.query(`CREATE INDEX IF NOT EXISTS idx_antennas_created_by ON antennas(created_by)`);
    await pool.query(`CREATE INDEX IF NOT EXISTS idx_antennas_updated_by ON antennas(updated_by)`);
    console.log('  ✅ Added created_by and updated_by columns with foreign keys\n');

    // 3. Add updated_by to campaigns table (created_by already exists)
    console.log('📋 Table: campaigns');
    await pool.query(`
      ALTER TABLE campaigns 
      ADD COLUMN IF NOT EXISTS updated_by INTEGER REFERENCES users(id) ON DELETE SET NULL
    `);
    await pool.query(`CREATE INDEX IF NOT EXISTS idx_campaigns_updated_by ON campaigns(updated_by)`);
    console.log('  ✅ Added updated_by column with foreign key\n');

    // 4. Add created_by and updated_at/updated_by to sensor_antennas table
    console.log('📋 Table: sensor_antennas');
    await pool.query(`
      ALTER TABLE sensor_antennas 
      ADD COLUMN IF NOT EXISTS created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
      ADD COLUMN IF NOT EXISTS updated_at BIGINT DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT,
      ADD COLUMN IF NOT EXISTS updated_by INTEGER REFERENCES users(id) ON DELETE SET NULL
    `);
    await pool.query(`CREATE INDEX IF NOT EXISTS idx_sensor_antennas_created_by ON sensor_antennas(created_by)`);
    await pool.query(`CREATE INDEX IF NOT EXISTS idx_sensor_antennas_updated_by ON sensor_antennas(updated_by)`);
    console.log('  ✅ Added created_by, updated_at, and updated_by columns with foreign keys\n');

    // Verify the changes
    console.log('\n=== Verification ===\n');
    const query = `
      SELECT table_name, column_name, data_type
      FROM information_schema.columns
      WHERE table_schema = 'public'
        AND table_name IN ('sensors', 'antennas', 'sensor_antennas', 'campaigns')
        AND column_name IN ('created_by', 'updated_by')
      ORDER BY table_name, column_name
    `;
    
    const result = await pool.query(query);
    let currentTable = '';
    result.rows.forEach((row: any) => {
      if (row.table_name !== currentTable) {
        currentTable = row.table_name;
        console.log(`\n${currentTable}:`);
      }
      console.log(`  ✅ ${row.column_name} (${row.data_type})`);
    });

    console.log('\n\n✅ All audit columns added successfully!');
    
  } catch (error) {
    console.error('❌ Error adding audit columns:', error);
    throw error;
  } finally {
    await pool.end();
  }
}

addAuditColumns();
