import { query, dbExec } from './connection';

export async function initDatabase() {
  console.log('🔄 Iniciando migración a PostgreSQL...');

  // Tabla de Sensores
  await dbExec(`
    CREATE TABLE IF NOT EXISTS sensors (
      id SERIAL PRIMARY KEY,
      mac VARCHAR(17) UNIQUE NOT NULL,
      name VARCHAR(255) NOT NULL,
      description TEXT,
      lat NUMERIC(10, 7),
      lng NUMERIC(10, 7),
      alt NUMERIC(10, 2),
      status VARCHAR(50) DEFAULT 'inactive',
      created_at BIGINT DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT * 1000,
      updated_at BIGINT DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT * 1000
    )
  `);

  // Tabla de Antenas
  await dbExec(`
    CREATE TABLE IF NOT EXISTS antennas (
      id SERIAL PRIMARY KEY,
      name VARCHAR(255) NOT NULL,
      type VARCHAR(100) NOT NULL,
      frequency_min_hz BIGINT,
      frequency_max_hz BIGINT,
      gain_db NUMERIC(5, 2),
      description TEXT,
      created_at BIGINT DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT * 1000,
      updated_at BIGINT DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT * 1000
    )
  `);

  // Tabla de asociación Sensor-Antena
  await dbExec(`
    CREATE TABLE IF NOT EXISTS sensor_antennas (
      id SERIAL PRIMARY KEY,
      sensor_id INTEGER NOT NULL,
      antenna_id INTEGER NOT NULL,
      port INTEGER NOT NULL,
      is_active INTEGER DEFAULT 1,
      created_at BIGINT DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT * 1000,
      FOREIGN KEY (sensor_id) REFERENCES sensors(id) ON DELETE CASCADE,
      FOREIGN KEY (antenna_id) REFERENCES antennas(id) ON DELETE CASCADE,
      UNIQUE(sensor_id, port)
    )
  `);

  // Tabla de Status del Sensor
  await dbExec(`
    CREATE TABLE IF NOT EXISTS sensor_status (
      id SERIAL PRIMARY KEY,
      mac VARCHAR(17) NOT NULL,
      cpu_0 NUMERIC(5, 2),
      cpu_1 NUMERIC(5, 2),
      cpu_2 NUMERIC(5, 2),
      cpu_3 NUMERIC(5, 2),
      ram_mb INTEGER,
      swap_mb INTEGER,
      disk_mb INTEGER,
      temp_c NUMERIC(5, 2),
      total_ram_mb INTEGER,
      total_swap_mb INTEGER,
      total_disk_mb INTEGER,
      delta_t_ms INTEGER,
      ping_ms NUMERIC(8, 3),
      timestamp_ms BIGINT,
      last_kal_ms BIGINT,
      last_ntp_ms BIGINT,
      logs TEXT,
      created_at BIGINT DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT * 1000,
      FOREIGN KEY (mac) REFERENCES sensors(mac) ON DELETE CASCADE
    )
  `);

  // Tabla de GPS
  await dbExec(`
    CREATE TABLE IF NOT EXISTS sensor_gps (
      id SERIAL PRIMARY KEY,
      mac VARCHAR(17) NOT NULL,
      lat NUMERIC(10, 7) NOT NULL,
      lng NUMERIC(10, 7) NOT NULL,
      alt NUMERIC(10, 2),
      created_at BIGINT DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT * 1000,
      FOREIGN KEY (mac) REFERENCES sensors(mac) ON DELETE CASCADE
    )
  `);

  // Tabla de Datos de medición (spectrum data)
  // Esta será convertida a hypertable con TimescaleDB
  await dbExec(`
    CREATE TABLE IF NOT EXISTS sensor_data (
      id SERIAL PRIMARY KEY,
      mac VARCHAR(17) NOT NULL,
      campaign_id INTEGER,
      pxx TEXT NOT NULL,
      start_freq_hz BIGINT NOT NULL,
      end_freq_hz BIGINT NOT NULL,
      "timestamp" BIGINT NOT NULL,
      lat NUMERIC(10, 7),
      lng NUMERIC(10, 7),
      excursion_peak_to_peak_hz NUMERIC(15, 3),
      excursion_peak_deviation_hz NUMERIC(15, 3),
      excursion_rms_deviation_hz NUMERIC(15, 3),
      depth_peak_to_peak NUMERIC(10, 6),
      depth_peak_deviation NUMERIC(10, 6),
      depth_rms_deviation NUMERIC(10, 6),
      created_at BIGINT DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT * 1000,
      FOREIGN KEY (mac) REFERENCES sensors(mac) ON DELETE CASCADE
    )
  `);

  // Tabla de Configuraciones (para GET-realtime)
  await dbExec(`
    CREATE TABLE IF NOT EXISTS sensor_configurations (
      id SERIAL PRIMARY KEY,
      mac VARCHAR(17) NOT NULL,
      start_freq_hz BIGINT NOT NULL,
      end_freq_hz BIGINT NOT NULL,
      resolution_hz INTEGER,
      antenna_port INTEGER,
      "window" VARCHAR(50),
      overlap NUMERIC(5, 2),
      sample_rate_hz INTEGER,
      lna_gain INTEGER,
      vga_gain INTEGER,
      antenna_amp INTEGER DEFAULT 0,
      demod_type VARCHAR(50),
      demod_bandwidth_hz INTEGER,
      demod_center_freq_hz INTEGER,
      demod_with_metrics INTEGER DEFAULT 0,
      demod_port_socket VARCHAR(100),
      filter_type VARCHAR(50),
      filter_bw_hz INTEGER,
      filter_order INTEGER,
      is_active INTEGER DEFAULT 1,
      created_at BIGINT DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT * 1000,
      updated_at BIGINT DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT * 1000,
      FOREIGN KEY (mac) REFERENCES sensors(mac) ON DELETE CASCADE
    )
  `);

  // Agregar columnas de filtro si no existen (para migraciones)
  try {
    await dbExec(`ALTER TABLE sensor_configurations ADD COLUMN IF NOT EXISTS filter_type VARCHAR(50)`);
    await dbExec(`ALTER TABLE sensor_configurations ADD COLUMN IF NOT EXISTS filter_bw_hz INTEGER`);
    await dbExec(`ALTER TABLE sensor_configurations ADD COLUMN IF NOT EXISTS filter_order INTEGER`);
    console.log('✅ Columnas de filtro verificadas/agregadas en sensor_configurations');
  } catch (error) {
    console.log('ℹ️ Nota: Error al verificar columnas de filtro (pueden ya existir):', error);
  }

  // Agregar columna status_admin a sensors (para migraciones)
  try {
    await dbExec(`ALTER TABLE sensors ADD COLUMN IF NOT EXISTS status_admin VARCHAR(50) DEFAULT 'active'`);
    // Asegurar que los registros existentes tengan un valor
    await dbExec(`UPDATE sensors SET status_admin = 'active' WHERE status_admin IS NULL`);
    console.log('✅ Columna status_admin verificada/agregada en sensors');
  } catch (error) {
    console.log('ℹ️ Nota: Error al verificar columna status_admin (puede ya existir):', error);
  }

  // Tabla de Usuarios
  await dbExec(`
    CREATE TABLE IF NOT EXISTS users (
      id SERIAL PRIMARY KEY,
      username VARCHAR(100) UNIQUE NOT NULL,
      password VARCHAR(255) NOT NULL,
      full_name VARCHAR(255) NOT NULL,
      email VARCHAR(255) UNIQUE NOT NULL,
      role VARCHAR(50) NOT NULL DEFAULT 'tecnico',
      is_active BOOLEAN DEFAULT TRUE,
      created_at TIMESTAMP DEFAULT NOW(),
      updated_at TIMESTAMP DEFAULT NOW()
    )
  `);

  // Tabla de Configuraciones del Sistema
  await dbExec(`
    CREATE TABLE IF NOT EXISTS system_configurations (
      key VARCHAR(100) PRIMARY KEY,
      value TEXT,
      description TEXT,
      updated_at TIMESTAMP DEFAULT NOW()
    )
  `);

  // Insertar valores por defecto para configuraciones del sistema
  try {
    const configs = [
      { key: 'center_freq_tolerance_khz', value: '100', description: 'Tolerancia de frecuencia central (kHz)' },
      { key: 'bandwidth_tolerance_khz', value: '10', description: 'Tolerancia de ancho de banda (kHz)' },
      { key: 'max_monitoring_time_min', value: '10', description: 'Tiempo máximo de monitoreo (minutos)' }
    ];

    for (const config of configs) {
      await query(`
        INSERT INTO system_configurations (key, value, description)
        VALUES ($1, $2, $3)
        ON CONFLICT (key) DO NOTHING
      `, [config.key, config.value, config.description]);
    }
    console.log('✅ Configuraciones del sistema inicializadas');
  } catch (error: any) {
    console.log('⚠️ Error al inicializar configuraciones del sistema:', error.message);
  }

  // Tabla de Campañas
  await dbExec(`
    CREATE TABLE IF NOT EXISTS campaigns (
      id SERIAL PRIMARY KEY,
      name VARCHAR(255) NOT NULL,
      description TEXT,
      status VARCHAR(50) DEFAULT 'scheduled',
      start_date DATE,
      end_date DATE,
      start_time TIME,
      end_time TIME,
      interval_seconds INTEGER,
      start_freq_mhz NUMERIC(10, 3),
      end_freq_mhz NUMERIC(10, 3),
      bandwidth_mhz NUMERIC(10, 3),
      resolution_khz NUMERIC(10, 3),
      preset VARCHAR(50) DEFAULT 'custom',
      config JSONB,
      created_by INTEGER,
      created_at TIMESTAMP DEFAULT NOW(),
      updated_at TIMESTAMP DEFAULT NOW(),
      FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
    )
  `);

  // Tabla de asociación Campaña-Sensor
  await dbExec(`
    CREATE TABLE IF NOT EXISTS campaign_sensors (
      id SERIAL PRIMARY KEY,
      campaign_id INTEGER NOT NULL,
      sensor_mac VARCHAR(17) NOT NULL,
      created_at TIMESTAMP DEFAULT NOW(),
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
    CREATE INDEX IF NOT EXISTS idx_sensor_data_timestamp ON sensor_data("timestamp");
    CREATE INDEX IF NOT EXISTS idx_sensor_config_mac ON sensor_configurations(mac);
    CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns(status);
    CREATE INDEX IF NOT EXISTS idx_campaigns_dates ON campaigns(start_date, end_date);
    CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
    CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
    CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
  `);

  console.log('✅ Tablas PostgreSQL creadas exitosamente');

  // Intentar crear hypertable con TimescaleDB si está disponible
  try {
    await query(`
      SELECT create_hypertable(
        'sensor_data', 
        'timestamp',
        if_not_exists => TRUE,
        migrate_data => TRUE
      );
    `);
    console.log('✅ Hypertable de TimescaleDB creada para sensor_data');
    
    // Configurar políticas de retención y compresión (opcional)
    // Ejemplo: comprimir datos después de 7 días
    await query(`
      SELECT add_compression_policy(
        'sensor_data',
        INTERVAL '7 days',
        if_not_exists => TRUE
      );
    `);
    console.log('✅ Política de compresión configurada (7 días)');
    
  } catch (error: any) {
    if (error.message && error.message.includes('extension "timescaledb"')) {
      console.log('⚠️  TimescaleDB no está instalado. Usando PostgreSQL estándar.');
      console.log('   Para instalar TimescaleDB: https://docs.timescale.com/install/latest/');
    } else {
      console.log('⚠️  No se pudo crear hypertable:', error.message);
      console.log('   La tabla sensor_data funcionará como tabla PostgreSQL estándar');
    }
  }

  // Crear usuario administrador por defecto si no existe
  try {
    const bcrypt = require('bcrypt');
    const hashedPassword = await bcrypt.hash('admin123', 10);
    
    await query(`
      INSERT INTO users (username, password, full_name, email, role)
      VALUES ($1, $2, $3, $4, $5)
      ON CONFLICT (username) DO NOTHING
    `, ['admin', hashedPassword, 'Administrador', 'admin@ane.gov.co', 'administrador']);
    
    console.log('✅ Usuario administrador creado (username: admin, password: admin123)');
  } catch (error: any) {
    console.log('⚠️  No se pudo crear usuario administrador:', error.message);
  }

  console.log('✅ Migración completada exitosamente');
}

// Ejecutar si se llama directamente
if (require.main === module) {
  initDatabase()
    .then(() => {
      console.log('✅ Migration completed');
      process.exit(0);
    })
    .catch((error) => {
      console.error('❌ Migration failed:', error);
      process.exit(1);
    });
}
