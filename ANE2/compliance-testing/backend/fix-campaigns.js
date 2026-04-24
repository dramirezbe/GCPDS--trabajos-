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
    console.log('Connecting to database at 172.23.90.25...');
    await client.connect();
    console.log('Connected successfully.');

    const query = `
      UPDATE campaigns 
      SET status = 'completed', updated_at = NOW() 
      WHERE status IN ('scheduled', 'running') 
        AND ((end_date + COALESCE(end_time, '23:59:59')::time) AT TIME ZONE 'America/Bogota') <= NOW();
    `;

    console.log('Executing query...');
    const res = await client.query(query);
    console.log(`✅ Updated ${res.rowCount} campaigns to 'completed' status.`);
  } catch (err) {
    console.error('❌ Error:', err);
  } finally {
    await client.end();
  }
}

run();
