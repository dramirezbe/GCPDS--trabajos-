import { query } from './connection';

async function fixCampaignData() {
  try {
    console.log('🔍 Buscando campaña "test-ane2-violacion"...');
    
    // 1. Buscar la campaña
    const campaignResult = await query(`
      SELECT * FROM campaigns 
      WHERE name = 'test-ane2-violacion'
      LIMIT 1
    `);

    if (campaignResult.rows.length === 0) {
      console.error('❌ Campaña "test-ane2-violacion" no encontrada.');
      process.exit(1);
    }

    const campaign = campaignResult.rows[0];
    console.log(`✅ Campaña encontrada: ID ${campaign.id}`);
    console.log(`   Rango: ${campaign.start_freq_mhz} - ${campaign.end_freq_mhz} MHz`);
    console.log(`   Sensor asociado (via campaign_sensors):`);
    
    // 2. Obtener sensor asociado
    const sensorResult = await query(`
      SELECT sensor_mac FROM campaign_sensors WHERE campaign_id = $1
    `, [campaign.id]);
    
    if (sensorResult.rows.length === 0) {
      console.error('❌ No hay sensores asociados a esta campaña.');
      process.exit(1);
    }
    
    const sensorMac = sensorResult.rows[0].sensor_mac;
    console.log(`   Sensor: ${sensorMac}`);

    // 3. Buscar mediciones huérfanas (campaign_id IS NULL) que coincidan con el rango de frecuencia
    console.log('\n🔍 Buscando mediciones huérfanas compatibles...');
    
    // Convertir a Hz con tolerancia
    const startFreqHz = Math.round(parseFloat(campaign.start_freq_mhz) * 1e6);
    const endFreqHz = Math.round(parseFloat(campaign.end_freq_mhz) * 1e6);
    const toleranceHz = 2000; // 2 kHz tolerancia

    // Buscar mediciones del sensor que no tengan campaign_id
    // y cuyos parámetros de frecuencia coincidan
    const orphansResult = await query(`
      SELECT COUNT(*) as count 
      FROM sensor_data 
      WHERE mac = $1 
        AND campaign_id IS NULL
        AND ABS(start_freq_hz - $2) <= $4
        AND ABS(end_freq_hz - $3) <= $4
    `, [sensorMac, startFreqHz, endFreqHz, toleranceHz]);

    const orphansCount = parseInt(orphansResult.rows[0].count);
    console.log(`   Encontradas ${orphansCount} mediciones huérfanas compatibles.`);

    if (orphansCount > 0) {
      console.log('\n🛠️  Asociando mediciones a la campaña...');
      
      const updateResult = await query(`
        UPDATE sensor_data 
        SET campaign_id = $1
        WHERE mac = $2 
          AND campaign_id IS NULL
          AND ABS(start_freq_hz - $3) <= $5
          AND ABS(end_freq_hz - $4) <= $5
      `, [campaign.id, sensorMac, startFreqHz, endFreqHz, toleranceHz]);
      
      console.log(`✅ ${updateResult.rowCount} mediciones actualizadas correctamente.`);
    } else {
      console.log('✨ No se requieren cambios.');
    }

    // 4. Resumen final
    const finalCount = await query(`
      SELECT COUNT(*) as count FROM sensor_data WHERE campaign_id = $1
    `, [campaign.id]);
    
    console.log(`\n📊 Total mediciones en campaña ${campaign.id}: ${finalCount.rows[0].count}`);

  } catch (error) {
    console.error('❌ Error:', error);
  }
  
  process.exit(0);
}

fixCampaignData();
