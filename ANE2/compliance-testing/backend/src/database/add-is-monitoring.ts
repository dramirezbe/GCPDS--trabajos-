import { dbExec } from './connection';

async function migrate() {
  console.log('Running migration: Add is_monitoring to sensor_configurations');
  
  try {
    await dbExec(`
      ALTER TABLE sensor_configurations 
      ADD COLUMN is_monitoring INTEGER DEFAULT 0
    `);
    console.log('✅ Added is_monitoring column to sensor_configurations table');
  } catch (error: any) {
    if (error.message.includes('duplicate column name')) {
      console.log('ℹ️ Column is_monitoring already exists');
    } else {
      console.error('❌ Error adding column:', error);
      process.exit(1);
    }
  }

  process.exit(0);
}

migrate();
