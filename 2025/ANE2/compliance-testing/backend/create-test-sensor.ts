import { query } from './src/database/connection';

async function createTestSensor() {
  try {
    console.log('\n=== CREANDO SENSOR DE PRUEBA ===\n');
    
    const mac = '00:11:22:33:44:55';
    
    // Verificar si ya existe
    const existing = await query('SELECT * FROM sensors WHERE mac = $1', [mac]);
    
    if (existing.rows.length > 0) {
      console.log('✅ El sensor ya existe:');
      console.table(existing.rows);
    } else {
      // Crear el sensor
      const result = await query(`
        INSERT INTO sensors (mac, name, description, lat, lng, alt, status)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING *
      `, [
        mac,
        'Sensor Simulado',
        'Sensor creado para pruebas con el simulador',
        4.6097,  // Bogotá
        -74.0817,
        2640,
        'inactive'
      ]);
      
      console.log('✅ Sensor creado exitosamente:');
      console.table(result.rows);
    }
    
    console.log('\n=== SENSORES ACTUALES ===\n');
    const sensors = await query('SELECT id, name, mac, status FROM sensors ORDER BY id');
    console.table(sensors.rows);
    
    process.exit(0);
  } catch (error) {
    console.error('❌ Error:', error);
    process.exit(1);
  }
}

createTestSensor();
