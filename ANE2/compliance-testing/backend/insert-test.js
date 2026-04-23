// Script para insertar datos de prueba con emisiones para reporte de cumplimiento
const { Pool } = require('pg');

const pool = new Pool({
  host: 'localhost',
  port: 5432,
  database: 'ane_db',
  user: 'postgres',
  password: 'postgres'
});

async function insertTestData() {
  console.log('\n🔧 Insertando datos de prueba con emisiones...\n');

  try {
    // Limpiar datos anteriores de prueba
    console.log('🧹 Limpiando datos anteriores...');
    await pool.query(
      "DELETE FROM sensor_data WHERE mac = 'd0:65:78:9c:dd:d0' AND timestamp >= 1734861600000"
    );

    const now = Date.now();

    // Medición 1: Emisiones SIN LICENCIA (98.5 MHz, 100.2 MHz)
    console.log('📊 Insertando medición 1 (SIN LICENCIA)...');
    const data1 = Array(200).fill(-80).concat(
      [-45, -42, -45, -48, -45, -42, -45],
      Array(50).fill(-80),
      [-52, -48, -50, -52, -48, -52],
      Array(143).fill(-80)
    );
    await pool.query(
      'INSERT INTO sensor_data (mac, timestamp, pxx, start_freq_hz, end_freq_hz, created_at) VALUES ($1, $2, $3, $4, $5, $6)',
      ['d0:65:78:9c:dd:d0', 1734861600000, JSON.stringify(data1), 88000000, 108000000, now]
    );
    console.log('  ✅ Medición 1 insertada');

    // Medición 2: Emisiones FUERA DE PARÁMETROS
    console.log('📊 Insertando medición 2 (FUERA PARÁMETROS)...');
    const data2 = Array(30).fill(-80).concat(
      [-38, -35, -33, -38, -35, -38],
      Array(54).fill(-80),
      [-42, -40, -38, -42, -40, -42],
      Array(110).fill(-80)
    );
    await pool.query(
      'INSERT INTO sensor_data (mac, timestamp, pxx, start_freq_hz, end_freq_hz, created_at) VALUES ($1, $2, $3, $4, $5, $6)',
      ['d0:65:78:9c:dd:d0', 1734862200000, JSON.stringify(data2), 88000000, 108000000, now]
    );
    console.log('  ✅ Medición 2 insertada');

    // Medición 3: MIX (Conforme + Sin Licencia + Fuera Parámetros)
    console.log('📊 Insertando medición 3 (MIX)...');
    const data3 = Array(20).fill(-80).concat(
      [-40, -38, -36, -40, -38, -40],
      Array(24).fill(-80),
      [-48, -45, -43, -48, -45, -48],
      Array(30).fill(-80),
      [-36, -33, -31, -36, -33, -36],
      Array(120).fill(-80)
    );
    await pool.query(
      'INSERT INTO sensor_data (mac, timestamp, pxx, start_freq_hz, end_freq_hz, created_at) VALUES ($1, $2, $3, $4, $5, $6)',
      ['d0:65:78:9c:dd:d0', 1734862800000, JSON.stringify(data3), 88000000, 108000000, now]
    );
    console.log('  ✅ Medición 3 insertada');

    // Medición 4: Más problemas para agrupación
    console.log('📊 Insertando medición 4 (MÁS PROBLEMAS)...');
    const data4 = Array(50).fill(-80).concat(
      [-50, -47, -45, -50, -47, -50],
      Array(24).fill(-80),
      [-38, -35, -33, -38, -35, -38],
      Array(120).fill(-80)
    );
    await pool.query(
      'INSERT INTO sensor_data (mac, timestamp, pxx, start_freq_hz, end_freq_hz, created_at) VALUES ($1, $2, $3, $4, $5, $6)',
      ['d0:65:78:9c:dd:d0', 1734863400000, JSON.stringify(data4), 88000000, 108000000, now]
    );
    console.log('  ✅ Medición 4 insertada');

    // Medición 5: Mayormente CONFORMES
    console.log('📊 Insertando medición 5 (CONFORMES)...');
    const data5 = Array(20).fill(-80).concat(
      [-42, -40, -38, -42, -40, -42],
      Array(34).fill(-80),
      [-38, -36, -34, -38, -36, -38],
      Array(50).fill(-80),
      [-44, -42, -40, -44, -42, -44],
      Array(90).fill(-80)
    );
    await pool.query(
      'INSERT INTO sensor_data (mac, timestamp, pxx, start_freq_hz, end_freq_hz, created_at) VALUES ($1, $2, $3, $4, $5, $6)',
      ['d0:65:78:9c:dd:d0', 1734864000000, JSON.stringify(data5), 88000000, 108000000, now]
    );
    console.log('  ✅ Medición 5 insertada');

    console.log('\n✅ Datos de prueba insertados exitosamente!\n');
    console.log('📊 Total: 5 mediciones con emisiones variadas\n');
    console.log('Emisiones esperadas:');
    console.log('  🔴 Sin Licencia: ~4 emisiones en frecuencias 98.5 MHz y 100.2 MHz');
    console.log('  🟠 Fuera Parámetros: ~4 emisiones en licencias 94.0 MHz y 101.5 MHz (FC desviada)');
    console.log('  🟢 Conformes: ~6 emisiones\n');
    console.log('🎯 Ahora genera el reporte para Campaña ID 1 en el frontend!\n');

  } catch (error) {
    console.error('❌ Error:', error.message);
    throw error;
  } finally {
    await pool.end();
  }
}

insertTestData().catch(console.error);
