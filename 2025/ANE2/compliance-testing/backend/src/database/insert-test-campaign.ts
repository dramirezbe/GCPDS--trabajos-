import { query } from './connection';

async function insertTestCampaign() {
  try {
    console.log('🧪 Insertando campaña de prueba...');

    const sensorMac = 'AA:BB:CC:DD:EE:FF';
    
    // 1. Crear campaña de prueba
    const campaignResult = await query(`
      INSERT INTO campaigns (
        name,
        status,
        start_freq_mhz,
        end_freq_mhz,
        bandwidth_mhz,
        resolution_khz,
        start_date,
        end_date,
        start_time,
        end_time,
        interval_seconds,
        created_at,
        updated_at
      ) VALUES (
        'Campaña Test FM - Ulloa',
        'completed',
        88,
        108,
        20,
        100,
        '2025-12-13',
        '2025-12-13',
        '14:00:00',
        '14:30:00',
        60,
        NOW(),
        NOW()
      )
      RETURNING id
    `);

    const campaignId = campaignResult.rows[0].id;
    console.log(`✅ Campaña creada con ID: ${campaignId}`);

    // 2. Asociar sensor a la campaña
    await query(`
      INSERT INTO campaign_sensors (campaign_id, sensor_mac, created_at)
      VALUES ($1, $2, NOW())
    `, [campaignId, sensorMac]);

    console.log(`✅ Sensor ${sensorMac} asociado a la campaña`);

    // 3. Insertar mediciones de ejemplo (FM band 88-108 MHz)
    console.log('📊 Insertando mediciones...');

    const startFreq = 88e6;  // 88 MHz
    const endFreq = 108e6;   // 108 MHz
    const numPoints = 200;
    const freqStep = (endFreq - startFreq) / numPoints;

    // Crear 20 mediciones a lo largo del tiempo
    for (let i = 0; i < 20; i++) {
      // Generar espectro con algunas emisoras FM simuladas
      const pxx: number[] = [];
      
      for (let j = 0; j < numPoints; j++) {
        const freq = startFreq + j * freqStep;
        let power = -100 + Math.random() * 10; // Ruido base entre -100 y -90 dBm

        // Simular emisoras FM (picos en ciertas frecuencias)
        const fmStations = [
          { freq: 89.9e6, power: -45 },   // Emisora 1
          { freq: 93.3e6, power: -40 },   // Emisora 2
          { freq: 96.7e6, power: -35 },   // Emisora 3 (más fuerte)
          { freq: 100.1e6, power: -42 },  // Emisora 4
          { freq: 104.5e6, power: -48 }   // Emisora 5
        ];

        // Agregar picos de emisoras
        fmStations.forEach(station => {
          const freqDiff = Math.abs(freq - station.freq);
          if (freqDiff < 200000) { // 200 kHz de ancho de banda
            const attenuation = (freqDiff / 200000) * 30; // Atenuación gradual
            power = Math.max(power, station.power - attenuation + Math.random() * 5);
          }
        });

        pxx.push(power);
      }

      // Timestamp incremental (cada minuto)
      const timestamp = Date.now() - (20 - i) * 60000;

      await query(`
        INSERT INTO sensor_data (
          mac,
          campaign_id,
          pxx,
          start_freq_hz,
          end_freq_hz,
          timestamp,
          lat,
          lng,
          created_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
      `, [
        sensorMac,
        campaignId,
        JSON.stringify(pxx),
        startFreq,
        endFreq,
        timestamp,
        4.681876,  // Ulloa, Valle del Cauca
        -75.710178,
        Date.now()
      ]);

      if ((i + 1) % 5 === 0) {
        console.log(`   ✓ ${i + 1}/20 mediciones insertadas`);
      }
    }

    console.log('✅ Todas las mediciones insertadas');

    // 4. Verificar datos insertados
    const countResult = await query(`
      SELECT COUNT(*) as count
      FROM sensor_data
      WHERE campaign_id = $1
    `, [campaignId]);

    console.log(`\n📊 Resumen:`);
    console.log(`   Campaña ID: ${campaignId}`);
    console.log(`   Nombre: Campaña Test FM - Ulloa`);
    console.log(`   Sensor: ${sensorMac}`);
    console.log(`   Mediciones: ${countResult.rows[0].count}`);
    console.log(`   Rango: 88-108 MHz (FM)`);
    console.log(`   Estado: completed`);
    console.log(`\n✨ Ahora puedes ver la campaña en la interfaz y hacer clic en el ícono del ojo 👁️`);

  } catch (error) {
    console.error('❌ Error insertando campaña de prueba:', error);
    throw error;
  }
}

// Ejecutar si se llama directamente
if (require.main === module) {
  insertTestCampaign()
    .then(() => {
      console.log('✅ Script completado');
      process.exit(0);
    })
    .catch((error) => {
      console.error('❌ Error:', error);
      process.exit(1);
    });
}

export { insertTestCampaign };
