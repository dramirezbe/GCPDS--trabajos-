import { query } from './connection';

async function insertTestData() {
  console.log('\n📝 Insertando datos de prueba para reportes\n');
  
  const sensorMac = 'AA:BB:CC:DD:EE:FF';
  
  // 1. Insertar datos GPS (Bogotá, Colombia)
  console.log('📍 Insertando datos GPS...');
  await query(`
    INSERT INTO sensor_gps (mac, lat, lng, alt, created_at)
    VALUES ($1, $2, $3, $4, $5)
    ON CONFLICT DO NOTHING
  `, [sensorMac, 4.681876, -75.710178, 100, Date.now()]);
  console.log('   ✅ Datos GPS insertados: Ulloa, Valle del Cauca (4.681876, -75.710178)');
  
  // 2. Insertar algunos datos de medición de ejemplo
  console.log('\n📊 Insertando mediciones de prueba...');
  
  // Generar un PXX de ejemplo (88-108 MHz, banda FM)
  const startFreqHz = 88e6; // 88 MHz
  const endFreqHz = 108e6;  // 108 MHz
  const numPoints = 200;
  const freqStep = (endFreqHz - startFreqHz) / numPoints;
  
  // Generar valores de potencia simulados con algunos picos en frecuencias FM típicas
  const pxxData = [];
  for (let i = 0; i < numPoints; i++) {
    const freq = startFreqHz + (i * freqStep);
    const freqMhz = freq / 1e6;
    
    // Agregar picos en frecuencias FM comunes
    let power = -100 + Math.random() * 10; // Ruido de fondo
    
    if (Math.abs(freqMhz - 95.5) < 0.5) power = -45; // Pico en 95.5 MHz
    if (Math.abs(freqMhz - 98.6) < 0.5) power = -50; // Pico en 98.6 MHz
    if (Math.abs(freqMhz - 100.6) < 0.5) power = -48; // Pico en 100.6 MHz
    if (Math.abs(freqMhz - 104.2) < 0.5) power = -42; // Pico en 104.2 MHz
    
    pxxData.push(power);
  }
  
  const now = Date.now();
  const oneDayAgo = now - 24 * 60 * 60 * 1000;
  
  // Insertar 3 mediciones de ejemplo
  for (let i = 0; i < 3; i++) {
    const timestamp = oneDayAgo + (i * 12 * 60 * 60 * 1000); // Cada 12 horas
    
    await query(`
      INSERT INTO sensor_data (
        mac, campaign_id, pxx, start_freq_hz, end_freq_hz, 
        "timestamp", lat, lng, created_at
      )
      VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
    `, [
      sensorMac,
      1, // campaign_id
      JSON.stringify(pxxData),
      startFreqHz,
      endFreqHz,
      timestamp,
      4.681876,
      -75.710178,
      timestamp
    ]);
  }
  
  console.log('   ✅ 3 mediciones insertadas (banda FM 88-108 MHz)');
  
  // 3. Verificar
  console.log('\n✅ Verificando datos insertados:');
  const gps = await query('SELECT mac, lat, lng FROM sensor_gps WHERE mac = $1', [sensorMac]);
  console.log(`   GPS: ${gps.rows[0].lat}, ${gps.rows[0].lng}`);
  
  const measurements = await query('SELECT COUNT(*) as count FROM sensor_data WHERE mac = $1', [sensorMac]);
  console.log(`   Mediciones: ${measurements.rows[0].count}`);
  
  console.log('\n🎉 Datos de prueba insertados exitosamente!');
  console.log('   Ahora puedes generar reportes para la Campaña ID 1');
  
  process.exit(0);
}

insertTestData().catch(console.error);
