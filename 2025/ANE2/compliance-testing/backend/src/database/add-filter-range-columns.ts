import { dbExec } from './connection';

export async function runMigration() {
  console.log('🔄 Agregando columnas de rango de filtro a sensor_configurations...');

  try {
    // Agregar columna filter_start_freq_hz
    await dbExec(`
      ALTER TABLE sensor_configurations 
      ADD COLUMN IF NOT EXISTS filter_start_freq_hz BIGINT
    `);
    console.log('✅ Columna filter_start_freq_hz agregada/verificada');

    // Agregar columna filter_end_freq_hz
    await dbExec(`
      ALTER TABLE sensor_configurations 
      ADD COLUMN IF NOT EXISTS filter_end_freq_hz BIGINT
    `);
    console.log('✅ Columna filter_end_freq_hz agregada/verificada');

  } catch (error) {
    console.error('❌ Error en migración:', error);
  }
}

// Ejecutar si se llama directamente
if (require.main === module) {
  runMigration().then(() => process.exit(0));
}
