import { Pool } from 'pg';
import dotenv from 'dotenv';

dotenv.config();

// Configuración de conexión para Producción
// Se usan variables de entorno, o valores por defecto para el servidor de producción
const config = {
  user: process.env.DB_USER || 'ane_user',
  host: process.env.DB_HOST || 'localhost',
  database: process.env.DB_NAME || 'ane_db',
  password: process.env.DB_PASSWORD || 'ane_password',
  port: parseInt(process.env.DB_PORT || '5432'),
};

const pool = new Pool(config);

async function runMigration() {
  console.log('🔌 Conectando a la base de datos:', config.host, config.database);
  
  let client;
  try {
    client = await pool.connect();
    console.log('✅ Conexión exitosa.');

    // 1. Tabla de Configuraciones del Sistema (Para reportes de cumplimiento)
    console.log('🔄 Verificando tabla system_configurations...');
    await client.query(`
      CREATE TABLE IF NOT EXISTS system_configurations (
        key VARCHAR(100) PRIMARY KEY,
        value TEXT,
        description TEXT,
        updated_at TIMESTAMP DEFAULT NOW()
      )
    `);
    console.log('✅ Tabla system_configurations verificada.');

    // 2. Insertar valores por defecto para tolerancias
    console.log('🔄 Insertando configuraciones por defecto...');
    const configs = [
      { key: 'center_freq_tolerance_khz', value: '100', description: 'Tolerancia de frecuencia central (kHz)' },
      { key: 'bandwidth_tolerance_khz', value: '10', description: 'Tolerancia de ancho de banda (kHz)' },
      { key: 'max_monitoring_time_min', value: '10', description: 'Tiempo máximo de monitoreo (minutos)' }
    ];

    for (const conf of configs) {
      await client.query(`
        INSERT INTO system_configurations (key, value, description)
        VALUES ($1, $2, $3)
        ON CONFLICT (key) DO NOTHING
      `, [conf.key, conf.value, conf.description]);
    }
    console.log('✅ Configuraciones insertadas.');

    // 3. Actualizar tabla sensor_configurations (Filtros)
    console.log('🔄 Actualizando tabla sensor_configurations...');
    
    const alterQueries = [
      `ALTER TABLE sensor_configurations ADD COLUMN IF NOT EXISTS filter_type VARCHAR(50)`,
      `ALTER TABLE sensor_configurations ADD COLUMN IF NOT EXISTS filter_bw_hz INTEGER`,
      `ALTER TABLE sensor_configurations ADD COLUMN IF NOT EXISTS filter_order INTEGER`,
      `ALTER TABLE sensor_configurations ADD COLUMN IF NOT EXISTS filter_start_freq_hz BIGINT`,
      `ALTER TABLE sensor_configurations ADD COLUMN IF NOT EXISTS filter_end_freq_hz BIGINT`
    ];

    for (const q of alterQueries) {
      try {
        await client.query(q);
      } catch (e: any) {
        console.log(`⚠️  Nota: ${e.message}`);
      }
    }
    console.log('✅ Tabla sensor_configurations actualizada.');

    // 4. Verificar resultados
    const res = await client.query('SELECT * FROM system_configurations');
    console.log('\n📊 Configuraciones actuales:');
    console.table(res.rows);

  } catch (err) {
    console.error('❌ Error ejecutando la migración:', err);
  } finally {
    if (client) client.release();
    await pool.end();
    console.log('👋 Conexión cerrada.');
  }
}

// Ejecutar si se llama directamente
if (require.main === module) {
  runMigration();
}

export { runMigration };
