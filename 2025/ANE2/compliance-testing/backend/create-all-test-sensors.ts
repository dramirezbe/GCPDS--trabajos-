import { query } from './src/database/connection';

async function createAllTestSensors() {
  try {
    console.log('\n=== CREANDO SENSORES PARA PRUEBAS ===\n');
    
    const testSensors = [
      {
        mac: '00:11:22:33:44:55',
        name: 'Sensor Simulado',
        description: 'Sensor por defecto para el simulador (MAC estándar)',
        lat: 4.6097,
        lng: -74.0817,
        alt: 2640
      },
      {
        mac: 'AA:BB:CC:DD:EE:FF',
        name: 'Sensor Test',
        description: 'Sensor de prueba alternativo',
        lat: 4.6105,
        lng: -74.0823,
        alt: 2645
      },
      {
        mac: '11:22:33:44:55:66',
        name: 'Sensor Cali Sur',
        description: 'Sensor de prueba Cali',
        lat: 4.6115,
        lng: -74.0810,
        alt: 2638
      }
    ];
    
    for (const sensor of testSensors) {
      // Verificar si ya existe
      const existing = await query('SELECT id, name, mac, status FROM sensors WHERE mac = $1', [sensor.mac]);
      
      if (existing.rows.length > 0) {
        console.log(`✅ Ya existe: ${sensor.name} (${sensor.mac})`);
      } else {
        // Crear el sensor
        await query(`
          INSERT INTO sensors (mac, name, description, lat, lng, alt, status)
          VALUES ($1, $2, $3, $4, $5, $6, $7)
        `, [
          sensor.mac,
          sensor.name,
          sensor.description,
          sensor.lat,
          sensor.lng,
          sensor.alt,
          'inactive'
        ]);
        
        console.log(`✅ Creado: ${sensor.name} (${sensor.mac})`);
      }
    }
    
    console.log('\n=== TODOS LOS SENSORES ===\n');
    const sensors = await query(`
      SELECT id, name, mac, status,
             lat, lng, alt,
             to_timestamp(created_at/1000) as created_at
      FROM sensors 
      ORDER BY id
    `);
    console.table(sensors.rows);
    
    console.log('\n✅ Listo para usar el simulador con cualquiera de estas MACs\n');
    
    process.exit(0);
  } catch (error) {
    console.error('❌ Error:', error);
    process.exit(1);
  }
}

createAllTestSensors();
