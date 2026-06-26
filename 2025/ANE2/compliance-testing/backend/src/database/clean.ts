import { query } from './connection';

async function cleanDatabase() {
  console.log('🗑️  Limpiando base de datos...');
  
  try {
    // Eliminar todas las tablas en orden inverso para respetar foreign keys
    await query('DROP TABLE IF EXISTS campaign_sensors CASCADE');
    await query('DROP TABLE IF EXISTS campaigns CASCADE');
    await query('DROP TABLE IF EXISTS sensor_configurations CASCADE');
    await query('DROP TABLE IF EXISTS sensor_data CASCADE');
    await query('DROP TABLE IF EXISTS sensor_gps CASCADE');
    await query('DROP TABLE IF EXISTS sensor_status CASCADE');
    await query('DROP TABLE IF EXISTS sensor_antennas CASCADE');
    await query('DROP TABLE IF EXISTS antennas CASCADE');
    await query('DROP TABLE IF EXISTS sensors CASCADE');
    
    console.log('✅ Base de datos limpiada exitosamente');
  } catch (error: any) {
    console.error('❌ Error limpiando base de datos:', error.message);
    throw error;
  }
}

// Ejecutar si se llama directamente
if (require.main === module) {
  cleanDatabase()
    .then(() => {
      console.log('✅ Clean completed');
      process.exit(0);
    })
    .catch((error) => {
      console.error('❌ Clean failed:', error);
      process.exit(1);
    });
}

export { cleanDatabase };
