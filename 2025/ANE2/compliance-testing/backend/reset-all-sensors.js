const { Client } = require('pg');
require('dotenv').config();

// Configuración de conexión (prioriza .env, fallback a defaults de producción)
const client = new Client({
  user: process.env.DB_USER,
  host: process.env.DB_HOST,
  database: process.env.DB_NAME,
  password: process.env.DB_PASSWORD,
  port: parseInt(process.env.DB_PORT),
});

async function run() {
  try {
    console.log('================================================');
    console.log('🔄 SCRIPT DE RESTAURACIÓN DE ESTADO DE SENSORES');
    console.log('================================================');
    console.log(`🔌 Conectando a DB ${client.host}:${client.port}/${client.database} como ${client.user}...`);
    
    await client.connect();
    console.log('✅ Conexión establecida.');

    console.log("\n📊 Ejecutando actualización masiva...");

    // 1. Actualizar estado en la tabla sensors
    // Reseteamos updated_at al tiempo actual para que tengan 5 minutos de gracia
    const updateQuery = `
      UPDATE sensors 
      SET status = 'online', updated_at = EXTRACT(EPOCH FROM NOW()) * 1000 
      WHERE status_admin != 'inactive' OR status_admin IS NULL
      RETURNING id, name, mac, status;
    `;

    const res = await client.query(updateQuery);

    console.log(`\n✅ Se actualizaron ${res.rowCount} sensores a 'online':`);
    res.rows.forEach(row => {
      console.log(`   Sensor: ${row.name.padEnd(30)} | MAC: ${row.mac} | Estado: ${row.status}`);
    });

    // 2. Insertar registros en sensor_status para que el sistema los vea como "recientes"
    // Esto es importante porque el backend mira la tabla sensor_status para validar
    console.log("\n📝 Insertando heartbeats recientes en sensor_status...");
    
    const timestamp = Date.now();
    for (const row of res.rows) {
      await client.query(`
        INSERT INTO sensor_status (mac, timestamp_ms, created_at)
        VALUES ($1, $2, NOW())
      `, [row.mac, timestamp]);
    }
    console.log("✅ Heartbeats insertados.");

  } catch (err) {
    console.error('\n❌ ERROR CRÍTICO:', err.message);
    if (err.code === '28P01') {
      console.error('   -> Error de autenticación. Verifique usuario y contraseña.');
    } else if (err.code === 'ECONNREFUSED') {
      console.error('   -> No se pudo conectar al servidor. Verifique host y puerto.');
    }
  } finally {
    await client.end();
    console.log('\n🔌 Conexión cerrada.');
    console.log('================================================');
  }
}

run();
