import { query } from './connection';

async function dropTable() {
  await query('DROP TABLE IF EXISTS frecuencias_consolidadas');
  console.log('✅ Tabla eliminada');
  process.exit(0);
}

dropTable().catch(console.error);
