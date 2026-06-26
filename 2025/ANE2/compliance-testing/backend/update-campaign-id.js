const { Pool } = require('pg');
const pool = new Pool({
  user: process.env.DB_USER,
  host: process.env.DB_HOST,
  database: process.env.DB_NAME,
  password: process.env.DB_PASSWORD,
  port: parseInt(process.env.DB_PORT),
});

pool.query(
  "UPDATE sensor_data SET campaign_id = 1 WHERE mac = 'd0:65:78:9c:dd:d0' AND timestamp >= 1734861600000"
).then(res => {
  console.log(`\n✅ Actualizado ${res.rowCount} registros con campaign_id = 1\n`);
  pool.end();
}).catch(err => {
  console.error('Error:', err.message);
  pool.end();
});
