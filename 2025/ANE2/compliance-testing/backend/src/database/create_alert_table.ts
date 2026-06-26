
import { dbExec } from './connection';

export async function createAlertTable() {
  console.log('🔄 Creating sensor_history_alert table...');

  await dbExec(`
    CREATE TABLE IF NOT EXISTS sensor_history_alert (
      id SERIAL PRIMARY KEY,
      sensor_mac VARCHAR(17) NOT NULL REFERENCES sensors(mac) ON DELETE CASCADE,
      alert_type VARCHAR(50) NOT NULL,
      description TEXT,
      timestamp BIGINT NOT NULL,
      created_at BIGINT DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT * 1000
    );
    
    CREATE INDEX IF NOT EXISTS idx_sensor_history_alert_mac_timestamp 
    ON sensor_history_alert (sensor_mac, timestamp DESC);
    
    CREATE INDEX IF NOT EXISTS idx_sensor_history_alert_timestamp 
    ON sensor_history_alert (timestamp DESC);
  `);
  
  console.log('✅ Table sensor_history_alert created successfully');
}

createAlertTable().then(() => process.exit(0)).catch(err => {
  console.error(err);
  process.exit(1);
});
