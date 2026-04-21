import { query } from './src/database/connection';

async function checkDatabase() {
  try {
    console.log('\n=== ESTRUCTURA DE sensor_status ===\n');
    const structure = await query(`
      SELECT column_name, data_type, is_nullable 
      FROM information_schema.columns 
      WHERE table_name = 'sensor_status' 
      ORDER BY ordinal_position
    `);
    console.table(structure.rows);
    
    console.log('\n=== FOREIGN KEYS DE sensor_status ===\n');
    const fkeys = await query(`
      SELECT
        tc.constraint_name,
        tc.table_name,
        kcu.column_name,
        ccu.table_name AS foreign_table_name,
        ccu.column_name AS foreign_column_name
      FROM information_schema.table_constraints AS tc
      JOIN information_schema.key_column_usage AS kcu
        ON tc.constraint_name = kcu.constraint_name
      JOIN information_schema.constraint_column_usage AS ccu
        ON ccu.constraint_name = tc.constraint_name
      WHERE tc.constraint_type = 'FOREIGN KEY'
        AND tc.table_name = 'sensor_status'
    `);
    console.table(fkeys.rows);
    
    console.log('\n=== SENSORES EN LA TABLA sensors ===\n');
    const sensors = await query(`
      SELECT id, name, mac, status, 
             to_timestamp(created_at/1000) as created_at,
             to_timestamp(updated_at/1000) as updated_at
      FROM sensors 
      ORDER BY id
    `);
    console.table(sensors.rows);
    
    console.log('\n=== TOTAL DE REGISTROS ===\n');
    const counts = await query(`
      SELECT 
        (SELECT COUNT(*) FROM sensors) as sensors_count,
        (SELECT COUNT(*) FROM sensor_status) as sensor_status_count
    `);
    console.log(`Sensores: ${counts.rows[0].sensors_count}`);
    console.log(`Status registros: ${counts.rows[0].sensor_status_count}`);
    
    process.exit(0);
  } catch (error) {
    console.error('Error:', error);
    process.exit(1);
  }
}

checkDatabase();
