import pkg from 'pg';
const { Client } = pkg;

async function checkProduction() {
  const client = new Client({
    user: process.env.DB_USER,
  host: process.env.DB_HOST,
  database: process.env.DB_NAME,
  password: process.env.DB_PASSWORD,
  port: parseInt(process.env.DB_PORT),
  });

  try {
    await client.connect();
    console.log('✅ Conectado a PostgreSQL producción\n');

    // 1. Ver todos los sensores con su estado
    console.log('=== SENSORES EN PRODUCCIÓN ===\n');
    const sensors = await client.query(`
      SELECT id, name, mac, status,
             to_timestamp(created_at/1000) as created_at,
             to_timestamp(updated_at/1000) as updated_at
      FROM sensors 
      ORDER BY id
    `);
    console.table(sensors.rows);

    // 2. Ver cuántos tienen datos en sensor_status
    console.log('\n=== ÚLTIMA ACTUALIZACIÓN DE CADA SENSOR ===\n');
    const lastStatus = await client.query(`
      SELECT 
        s.id,
        s.name,
        s.mac,
        s.status as estado_db,
        ss.timestamp_ms,
        to_timestamp(ss.timestamp_ms/1000) as ultimo_status,
        EXTRACT(EPOCH FROM (NOW() - to_timestamp(ss.timestamp_ms/1000)))/60 as minutos_sin_datos
      FROM sensors s
      LEFT JOIN LATERAL (
        SELECT timestamp_ms
        FROM sensor_status
        WHERE mac = s.mac
        ORDER BY created_at DESC
        LIMIT 1
      ) ss ON true
      ORDER BY s.id
    `);
    console.table(lastStatus.rows);

    // 3. Ver estadísticas
    console.log('\n=== ESTADÍSTICAS ===\n');
    const stats = await client.query(`
      SELECT 
        COUNT(*) FILTER (WHERE status = 'active') as activos,
        COUNT(*) FILTER (WHERE status = 'inactive') as inactivos,
        COUNT(*) FILTER (WHERE status IS NULL) as sin_estado,
        COUNT(*) as total
      FROM sensors
    `);
    console.log(`Total sensores: ${stats.rows[0].total}`);
    console.log(`Activos: ${stats.rows[0].activos}`);
    console.log(`Inactivos: ${stats.rows[0].inactivos}`);
    console.log(`Sin estado: ${stats.rows[0].sin_estado}`);

    // 4. Ver sensores que deberían estar inactivos
    console.log('\n=== SENSORES QUE DEBERÍAN ESTAR INACTIVOS (>2 min sin datos) ===\n');
    const shouldBeInactive = await client.query(`
      SELECT 
        s.id,
        s.name,
        s.mac,
        s.status as estado_actual,
        ss.timestamp_ms,
        to_timestamp(ss.timestamp_ms/1000) as ultimo_status,
        EXTRACT(EPOCH FROM (NOW() - to_timestamp(ss.timestamp_ms/1000)))/60 as minutos_sin_datos
      FROM sensors s
      LEFT JOIN LATERAL (
        SELECT timestamp_ms
        FROM sensor_status
        WHERE mac = s.mac
        ORDER BY created_at DESC
        LIMIT 1
      ) ss ON true
      WHERE 
        s.status = 'active' 
        AND (
          ss.timestamp_ms IS NULL 
          OR ss.timestamp_ms < EXTRACT(EPOCH FROM NOW())::BIGINT * 1000 - (2 * 60 * 1000)
        )
      ORDER BY minutos_sin_datos DESC NULLS FIRST
    `);
    console.table(shouldBeInactive.rows);
    console.log(`\n⚠️  ${shouldBeInactive.rows.length} sensores deberían estar inactivos\n`);

    // 5. Ver sensores sin ningún dato
    console.log('=== SENSORES SIN NINGÚN DATO EN sensor_status ===\n');
    const noData = await client.query(`
      SELECT s.id, s.name, s.mac, s.status
      FROM sensors s
      LEFT JOIN sensor_status ss ON s.mac = ss.mac
      WHERE ss.mac IS NULL
      ORDER BY s.id
    `);
    console.table(noData.rows);

  } catch (error) {
    console.error('❌ Error:', error);
  } finally {
    await client.end();
    process.exit(0);
  }
}

checkProduction();
