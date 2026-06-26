ALTER TABLE sensor_configurations ADD COLUMN IF NOT EXISTS is_monitoring INTEGER DEFAULT 0;
