const { Client } = require('pg');
const fs = require('fs');
const path = require('path');

const client = new Client({
  user: process.env.DB_USER,
  host: process.env.DB_HOST,
  database: process.env.DB_NAME,
  password: process.env.DB_PASSWORD,
  port: parseInt(process.env.DB_PORT),
});

async function run() {
  try {
    console.log('🔌 Conectando a base de datos de producción (172.23.90.25)...');
    await client.connect();
    console.log('✅ Conectado exitosamente.');

    const sqlPath = path.join(__dirname, '../deploy/create_alert_history_table.sql');
    let sql = fs.readFileSync(sqlPath, 'utf8');
    
    // Remover comandos específicos de psql como \echo
    sql = sql.replace(/\\echo.*/g, '');

    console.log('📜 Ejecutando script SQL...');
    await client.query(sql);
    
    console.log('✅ Migración completada: Tabla sensor_history_alert creada.');
    
    // Verificar que la tabla existe
    const res = await client.query("SELECT to_regclass('public.sensor_history_alert')");
    if (res.rows[0].to_regclass) {
        console.log('🔍 Verificación: La tabla existe en el esquema public.');
    } else {
        console.error('❌ Error: La tabla no parece haber sido creada.');
    }

  } catch (err) {
    console.error('❌ Error durante la migración:', err);
  } finally {
    await client.end();
  }
}

run();
