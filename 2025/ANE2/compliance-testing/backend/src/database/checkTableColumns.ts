import { pool } from './connection';

async function checkColumns() {
  try {
    const queryStr = `
      SELECT table_name, column_name, data_type
      FROM information_schema.columns
      WHERE table_schema = 'public'
        AND table_name IN ('sensors', 'antennas', 'sensor_antennas', 'campaigns', 'users')
      ORDER BY table_name, ordinal_position
    `;
    
    const result = await pool.query(queryStr);
    
    console.log('\n=== Database Table Columns ===\n');
    let currentTable = '';
    result.rows.forEach((row: any) => {
      if (row.table_name !== currentTable) {
        currentTable = row.table_name;
        console.log(`\n📋 Table: ${currentTable}`);
        console.log('─'.repeat(50));
      }
      console.log(`  - ${row.column_name} (${row.data_type})`);
    });
    
    console.log('\n\n=== Audit Columns Summary ===\n');
    const tables = ['sensors', 'antennas', 'sensor_antennas', 'campaigns', 'users'];
    
    for (const table of tables) {
      const columns = result.rows
        .filter((r: any) => r.table_name === table)
        .map((r: any) => r.column_name);
      
      const hasCreatedBy = columns.includes('created_by');
      const hasUpdatedBy = columns.includes('updated_by');
      const hasCreatedAt = columns.includes('created_at');
      const hasUpdatedAt = columns.includes('updated_at');
      
      console.log(`${table}:`);
      console.log(`  created_by: ${hasCreatedBy ? '✅' : '❌'}`);
      console.log(`  updated_by: ${hasUpdatedBy ? '✅' : '❌'}`);
      console.log(`  created_at: ${hasCreatedAt ? '✅' : '❌'}`);
      console.log(`  updated_at: ${hasUpdatedAt ? '✅' : '❌'}`);
      console.log('');
    }
    
  } catch (error) {
    console.error('Error checking columns:', error);
  } finally {
    await pool.end();
  }
}

checkColumns();
