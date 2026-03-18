import { query } from './connection';

async function checkData() {
  console.log('\n🔍 Verificando datos para reportes\n');
  
  // 1. Verificar campañas
  const campaigns = await query('SELECT id, name, status FROM campaigns LIMIT 5');
  console.log('📋 Campañas:', campaigns.rows.length);
  campaigns.rows.forEach(c => console.log(`   ID ${c.id}: ${c.name} (${c.status})`));
  
  // 2. Verificar sensores en campañas
  console.log('\n📡 Sensores en campañas:');
  const campaignSensors = await query(`
    SELECT cs.campaign_id, cs.sensor_mac, c.name as campaign_name
    FROM campaign_sensors cs
    JOIN campaigns c ON c.id = cs.campaign_id
    LIMIT 5
  `);
  campaignSensors.rows.forEach(cs => 
    console.log(`   Campaña ${cs.campaign_id} (${cs.campaign_name}): Sensor ${cs.sensor_mac}`)
  );
  
  // 3. Verificar datos GPS
  console.log('\n📍 Datos GPS disponibles:');
  const gpsData = await query('SELECT mac, lat, lng, created_at FROM sensor_gps ORDER BY created_at DESC LIMIT 5');
  if (gpsData.rows.length === 0) {
    console.log('   ⚠️  No hay datos GPS');
  } else {
    gpsData.rows.forEach(gps => 
      console.log(`   Sensor ${gps.mac}: lat=${gps.lat}, lng=${gps.lng}`)
    );
  }
  
  // 4. Verificar sensores registrados
  console.log('\n🔌 Sensores registrados:');
  const sensors = await query('SELECT mac, name, status FROM sensors LIMIT 5');
  sensors.rows.forEach(s => console.log(`   ${s.mac}: ${s.name} (${s.status})`));
  
  // 5. Verificar datos de mediciones
  console.log('\n📊 Mediciones disponibles:');
  const measurements = await query('SELECT mac, timestamp FROM sensor_data LIMIT 5');
  if (measurements.rows.length === 0) {
    console.log('   ⚠️  No hay mediciones');
  } else {
    measurements.rows.forEach(m => 
      console.log(`   Sensor ${m.mac}: ${new Date(m.timestamp).toISOString()}`)
    );
  }
  
  process.exit(0);
}

checkData().catch(console.error);
