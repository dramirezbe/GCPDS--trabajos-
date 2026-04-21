const { Client } = require('pg');

const client = new Client({
  user: 'ane_user',
  host: '172.23.90.25',
  database: 'ane_db',
  password: 'ANE_Secure_2025!_Unal',
  port: 5432,
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
