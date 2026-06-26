const { Client } = require('pg');
const fs = require('fs');
const path = require('path');

// Configuración de conexión (tomada de docker-compose.yml)
const config = {
  host: process.env.DB_HOST,
  port: parseInt(process.env.DB_PORT),
  database: process.env.DB_NAME,
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
};

async function runMigration() {
  console.log('🔌 Conectando a la base de datos...', {
    host: config.host,
    database: config.database,
    user: config.user
  });

  const client = new Client(config);

  try {
    await client.connect();
    console.log('✅ Conexión exitosa.');

    const sqlPath = path.join(__dirname, 'add-filter-columns.sql');
    if (!fs.existsSync(sqlPath)) {
      throw new Error(`Archivo SQL no encontrado: ${sqlPath}`);
    }

    const sql = fs.readFileSync(sqlPath, 'utf8');
    console.log('📝 Ejecutando script SQL...');
    
    await client.query(sql);
    console.log('✅ Migración completada exitosamente.');

  } catch (err) {
    console.error('❌ Error durante la migración:', err.message);
    if (err.code) console.error('Código de error:', err.code);
  } finally {
    await client.end();
  }
}

runMigration();
