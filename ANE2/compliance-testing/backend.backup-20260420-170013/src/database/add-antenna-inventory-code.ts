import { query } from './connection';

export async function migrate() {
  console.log('🔄 Agregando columna inventory_code a la tabla antennas...');
  try {
    await query(`
      ALTER TABLE antennas 
      ADD COLUMN IF NOT EXISTS inventory_code VARCHAR(255)
    `);
    console.log('✅ Columna inventory_code agregada exitosamente');
  } catch (error) {
    console.error('❌ Error al agregar columna inventory_code:', error);
  }
}

if (require.main === module) {
  migrate()
    .then(() => process.exit(0))
    .catch(() => process.exit(1));
}
