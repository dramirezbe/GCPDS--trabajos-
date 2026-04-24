const { Client } = require('pg');

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

    const macsToReset = [
      'd8:3a:dd:f4:4e:d1', // ANE9
      'd8:3a:dd:f6:fc:be'  // ANE4
    ];

    console.log(`🔄 Reseteando estado a 'online' para los sensores: ${macsToReset.join(', ')}`);

    // Actualizar estado en la tabla sensors
    const updateQuery = `
      UPDATE sensors 
      SET status = 'online', updated_at = EXTRACT(EPOCH FROM NOW()) * 1000 
      WHERE mac = ANY($1::text[])
      RETURNING id, name, mac, status;
    `;

    const res = await client.query(updateQuery, [macsToReset]);

    if (res.rowCount > 0) {
      console.log('✅ Actualización exitosa. Sensores afectados:');
      res.rows.forEach(row => {
        console.log(`   - [${row.id}] ${row.name} (${row.mac}) -> ${row.status}`);
      });
    } else {
      console.log('⚠️ No se encontraron sensores con esas MACs para actualizar.');
    }

  } catch (err) {
    console.error('❌ Error durante la actualización:', err);
  } finally {
    await client.end();
    console.log('🔌 Conexión cerrada.');
  }
}

run();
