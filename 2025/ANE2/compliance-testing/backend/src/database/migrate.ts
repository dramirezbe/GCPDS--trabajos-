import { dbExec } from './connection';

export async function initDatabase() {
  // Tabla de Sensores
  await dbExec(`
    CREATE TABLE IF NOT EXISTS sensors (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      mac TEXT UNIQUE NOT NULL,
      name TEXT NOT NULL,
      description TEXT,
      lat REAL,
      lng REAL,
      alt REAL,
      status TEXT DEFAULT 'inactive',
      created_at INTEGER DEFAULT (strftime('%s', 'now') * 1000),
      updated_at INTEGER DEFAULT (strftime('%s', 'now') * 1000)
    )
  `);

  // Tabla de Antenas
  await dbExec(`
    CREATE TABLE IF NOT EXISTS antennas (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      type TEXT NOT NULL,
      frequency_min_hz INTEGER,
      frequency_max_hz INTEGER,
      gain_db REAL,
      description TEXT,
      created_at INTEGER DEFAULT (strftime('%s', 'now') * 1000),
      updated_at INTEGER DEFAULT (strftime('%s', 'now') * 1000)
    )
  `);

  // Tabla de asociación Sensor-Antena
  await dbExec(`
    CREATE TABLE IF NOT EXISTS sensor_antennas (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      sensor_id INTEGER NOT NULL,
      antenna_id INTEGER NOT NULL,
      port INTEGER NOT NULL,
      is_active INTEGER DEFAULT 1,
      created_at INTEGER DEFAULT (strftime('%s', 'now') * 1000),
      FOREIGN KEY (sensor_id) REFERENCES sensors(id) ON DELETE CASCADE,
      FOREIGN KEY (antenna_id) REFERENCES antennas(id) ON DELETE CASCADE,
      UNIQUE(sensor_id, port)
    )
  `);

  // Tabla de Status del Sensor
  await dbExec(`
    CREATE TABLE IF NOT EXISTS sensor_status (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      mac TEXT NOT NULL,
      cpu_0 REAL,
      cpu_1 REAL,
      cpu_2 REAL,
      cpu_3 REAL,
      ram_mb INTEGER,
      swap_mb INTEGER,
      disk_mb INTEGER,
      temp_c REAL,
      total_ram_mb INTEGER,
      total_swap_mb INTEGER,
      total_disk_mb INTEGER,
      delta_t_ms INTEGER,
      ping_ms REAL,
      timestamp_ms INTEGER,
      last_kal_ms INTEGER,
      last_ntp_ms INTEGER,
      logs TEXT,
      created_at INTEGER DEFAULT (strftime('%s', 'now') * 1000),
      FOREIGN KEY (mac) REFERENCES sensors(mac) ON DELETE CASCADE
    )
  `);

  // Tabla de GPS
  await dbExec(`
    CREATE TABLE IF NOT EXISTS sensor_gps (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      mac TEXT NOT NULL,
      lat REAL NOT NULL,
      lng REAL NOT NULL,
      alt REAL,
      created_at INTEGER DEFAULT (strftime('%s', 'now') * 1000),
      FOREIGN KEY (mac) REFERENCES sensors(mac) ON DELETE CASCADE
    )
  `);

  // Tabla de Datos de medición (spectrum data)
  await dbExec(`
    CREATE TABLE IF NOT EXISTS sensor_data (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      mac TEXT NOT NULL,
      campaign_id INTEGER,
      pxx TEXT NOT NULL,
      start_freq_hz INTEGER NOT NULL,
      end_freq_hz INTEGER NOT NULL,
      timestamp INTEGER NOT NULL,
      lat REAL,
      lng REAL,
      excursion_peak_to_peak_hz REAL,
      excursion_peak_deviation_hz REAL,
      excursion_rms_deviation_hz REAL,
      depth_peak_to_peak REAL,
      depth_peak_deviation REAL,
      depth_rms_deviation REAL,
      created_at INTEGER DEFAULT (strftime('%s', 'now') * 1000),
      FOREIGN KEY (mac) REFERENCES sensors(mac) ON DELETE CASCADE
    )
  `);

  // Tabla de Configuraciones (para GET-realtime)
  await dbExec(`
    CREATE TABLE IF NOT EXISTS sensor_configurations (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      mac TEXT NOT NULL,
      start_freq_hz INTEGER NOT NULL,
      end_freq_hz INTEGER NOT NULL,
      resolution_hz INTEGER,
      antenna_port INTEGER,
      window TEXT,
      overlap REAL,
      sample_rate_hz INTEGER,
      lna_gain INTEGER,
      vga_gain INTEGER,
      antenna_amp INTEGER DEFAULT 0,
      demod_type TEXT,
      demod_bandwidth_hz INTEGER,
      demod_center_freq_hz INTEGER,
      demod_with_metrics INTEGER DEFAULT 0,
      demod_port_socket TEXT,
      is_active INTEGER DEFAULT 1,
      created_at INTEGER DEFAULT (strftime('%s', 'now') * 1000),
      updated_at INTEGER DEFAULT (strftime('%s', 'now') * 1000),
      FOREIGN KEY (mac) REFERENCES sensors(mac) ON DELETE CASCADE
    )
  `);

  // Tabla de Campañas
  await dbExec(`
    CREATE TABLE IF NOT EXISTS campaigns (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      description TEXT,
      status TEXT DEFAULT 'scheduled',
      start_date TEXT,
      end_date TEXT,
      start_time TEXT,
      end_time TEXT,
      interval_seconds INTEGER,
      start_freq_mhz REAL,
      end_freq_mhz REAL,
      bandwidth_mhz REAL,
      resolution_khz REAL,
      preset TEXT DEFAULT 'custom',
      config TEXT,
      created_at TEXT DEFAULT (datetime('now')),
      updated_at TEXT DEFAULT (datetime('now'))
    )
  `);

  // Tabla de asociación Campaña-Sensor
  await dbExec(`
    CREATE TABLE IF NOT EXISTS campaign_sensors (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      campaign_id INTEGER NOT NULL,
      sensor_mac TEXT NOT NULL,
      created_at TEXT DEFAULT (datetime('now')),
      FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE,
      FOREIGN KEY (sensor_mac) REFERENCES sensors(mac) ON DELETE CASCADE,
      UNIQUE(campaign_id, sensor_mac)
    )
  `);

  // Índices para mejorar el rendimiento
  await dbExec(`
    CREATE INDEX IF NOT EXISTS idx_sensor_status_mac ON sensor_status(mac);
    CREATE INDEX IF NOT EXISTS idx_sensor_gps_mac ON sensor_gps(mac);
    CREATE INDEX IF NOT EXISTS idx_sensor_data_mac ON sensor_data(mac);
    CREATE INDEX IF NOT EXISTS idx_sensor_data_timestamp ON sensor_data(timestamp);
    CREATE INDEX IF NOT EXISTS idx_sensor_config_mac ON sensor_configurations(mac);
  `);

  console.log('✅ Database initialized successfully');
}

// Ejecutar si se llama directamente
if (require.main === module) {
  initDatabase();
  console.log('Migration completed');
  process.exit(0);
}
