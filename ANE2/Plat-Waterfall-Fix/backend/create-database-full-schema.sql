-- =====================================================================
-- ANE REALTIME - Script Completo de Creación de Base de Datos
-- PostgreSQL 16 + TimescaleDB
-- Generado consolidando todas las migraciones del proyecto
-- =====================================================================

-- =====================================================================
-- PASO 1: Crear usuario y base de datos
-- =====================================================================

-- Ejecutar como superusuario (postgres):
-- psql -U postgres -f create-database-full-schema.sql

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT FROM pg_user WHERE usename = 'ane_user') THEN
        CREATE USER ane_user WITH PASSWORD 'ANE_Secure_2024!_RSM';
        RAISE NOTICE 'Usuario ane_user creado';
    ELSE
        RAISE NOTICE 'Usuario ane_user ya existe';
    END IF;
END $$;

SELECT 'CREATE DATABASE ane_db OWNER ane_user'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'ane_db')\gexec

\c ane_db

-- =====================================================================
-- PASO 2: Habilitar extensiones
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- =====================================================================
-- PASO 3: Permisos
-- =====================================================================

GRANT ALL ON SCHEMA public TO ane_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ane_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ane_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ane_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ane_user;

-- =====================================================================
-- PASO 4: Tablas principales
-- =====================================================================

-- ----- USERS -----
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
);

-- ----- SENSORS -----
CREATE TABLE IF NOT EXISTS sensors (
    id SERIAL PRIMARY KEY,
    mac VARCHAR(17) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    lat NUMERIC(10, 7),
    lng NUMERIC(10, 7),
    alt NUMERIC(10, 2),
    status VARCHAR(50) DEFAULT 'inactive',
    status_admin VARCHAR(50) DEFAULT 'active',
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    updated_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at BIGINT DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT * 1000,
    updated_at BIGINT DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT * 1000
);

-- ----- ANTENNAS -----
CREATE TABLE IF NOT EXISTS antennas (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(100) NOT NULL,
    frequency_min_hz BIGINT,
    frequency_max_hz BIGINT,
    gain_db NUMERIC(5, 2),
    description TEXT,
    inventory_code VARCHAR(255),
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    updated_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at BIGINT DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT * 1000,
    updated_at BIGINT DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT * 1000
);

-- ----- SENSOR_ANTENNAS -----
CREATE TABLE IF NOT EXISTS sensor_antennas (
    id SERIAL PRIMARY KEY,
    sensor_id INTEGER NOT NULL REFERENCES sensors(id) ON DELETE CASCADE,
    antenna_id INTEGER NOT NULL REFERENCES antennas(id) ON DELETE CASCADE,
    port INTEGER NOT NULL,
    is_active INTEGER DEFAULT 1,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    updated_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at BIGINT DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT * 1000,
    updated_at BIGINT DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT,
    UNIQUE(sensor_id, port)
);

-- ----- CAMPAIGNS -----
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
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    updated_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ----- CAMPAIGN_SENSORS -----
CREATE TABLE IF NOT EXISTS campaign_sensors (
    id SERIAL PRIMARY KEY,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    sensor_mac VARCHAR(17) NOT NULL REFERENCES sensors(mac) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(campaign_id, sensor_mac)
);

-- ----- SENSOR_CONFIGURATIONS -----
CREATE TABLE IF NOT EXISTS sensor_configurations (
    id SERIAL PRIMARY KEY,
    mac VARCHAR(17) NOT NULL REFERENCES sensors(mac) ON DELETE CASCADE,
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
    filter_start_freq_hz BIGINT,
    filter_end_freq_hz BIGINT,
    is_monitoring INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    created_at BIGINT DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT * 1000,
    updated_at BIGINT DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT * 1000
);

-- ----- SENSOR_DATA (hypertable) -----
CREATE TABLE IF NOT EXISTS sensor_data (
    id BIGSERIAL,
    mac VARCHAR(17) NOT NULL,
    campaign_id INTEGER REFERENCES campaigns(id) ON DELETE SET NULL,
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
    created_at BIGINT DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT * 1000
);

-- ----- SENSOR_GPS (hypertable) -----
CREATE TABLE IF NOT EXISTS sensor_gps (
    id BIGSERIAL,
    mac VARCHAR(17) NOT NULL,
    lat NUMERIC(10, 7) NOT NULL,
    lng NUMERIC(10, 7) NOT NULL,
    alt NUMERIC(10, 2),
    created_at BIGINT DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT * 1000
);

-- ----- SENSOR_STATUS (hypertable) - versión con métricas de sistema -----
CREATE TABLE IF NOT EXISTS sensor_status (
    id BIGSERIAL,
    mac VARCHAR(17) NOT NULL,
    cpu_0 DOUBLE PRECISION,
    cpu_1 DOUBLE PRECISION,
    cpu_2 DOUBLE PRECISION,
    cpu_3 DOUBLE PRECISION,
    ram_mb BIGINT,
    swap_mb BIGINT,
    disk_mb BIGINT,
    total_ram_mb BIGINT,
    total_swap_mb BIGINT,
    total_disk_mb BIGINT,
    temp_c DOUBLE PRECISION,
    ping_ms DOUBLE PRECISION,
    delta_t_ms BIGINT,
    last_kal_ms BIGINT,
    last_ntp_ms BIGINT,
    logs TEXT,
    timestamp_ms BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ----- COMPLIANCE_REPORTS_CACHE -----
CREATE TABLE IF NOT EXISTS compliance_reports_cache (
    id SERIAL PRIMARY KEY,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    report_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(campaign_id)
);

-- ----- SENSOR_HISTORY_ALERT -----
CREATE TABLE IF NOT EXISTS sensor_history_alert (
    id SERIAL PRIMARY KEY,
    sensor_mac VARCHAR(17) NOT NULL REFERENCES sensors(mac) ON DELETE CASCADE,
    alert_type VARCHAR(50) NOT NULL,
    description TEXT,
    "timestamp" BIGINT NOT NULL,
    created_at BIGINT DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT * 1000
);

-- ----- AUDIT_LOGS -----
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    action VARCHAR(100) NOT NULL,
    details JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ----- SYSTEM_CONFIGURATIONS -----
CREATE TABLE IF NOT EXISTS system_configurations (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT,
    description TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ----- COBERTURAS -----
CREATE TABLE IF NOT EXISTS coberturas (
    id SERIAL PRIMARY KEY,
    frecuencia NUMERIC(15, 4),
    ancho_de_banda NUMERIC(15, 4),
    unidad_ancho_de_banda VARCHAR(10),
    potencia NUMERIC(15, 4),
    unidad_potencia VARCHAR(10),
    municipio VARCHAR(200),
    created_at TIMESTAMP DEFAULT NOW()
);

-- ----- FRECUENCIAS_CONSOLIDADAS -----
CREATE TABLE IF NOT EXISTS frecuencias_consolidadas (
    id SERIAL PRIMARY KEY,
    frecuencia NUMERIC(15, 4) NOT NULL,
    ancho_de_banda NUMERIC(15, 4),
    unidad_ancho_de_banda VARCHAR(10),
    potencia NUMERIC(15, 4),
    unidad_potencia VARCHAR(10),
    servicio VARCHAR(200),
    municipio VARCHAR(200),
    created_at TIMESTAMP DEFAULT NOW()
);

-- =====================================================================
-- PASO 5: Convertir tablas en hypertables (TimescaleDB)
-- =====================================================================

SELECT create_hypertable(
    'sensor_data',
    'timestamp',
    chunk_time_interval => 86400000000,
    if_not_exists => TRUE,
    migrate_data => TRUE
);

SELECT create_hypertable(
    'sensor_gps',
    'created_at',
    chunk_time_interval => 86400000000,
    if_not_exists => TRUE,
    migrate_data => TRUE
);

SELECT create_hypertable(
    'sensor_status',
    'timestamp_ms',
    chunk_time_interval => 86400000000,
    if_not_exists => TRUE,
    migrate_data => TRUE
);

-- =====================================================================
-- PASO 6: Índices
-- =====================================================================

-- sensor_data
CREATE INDEX IF NOT EXISTS idx_sensor_data_mac ON sensor_data(mac);
CREATE INDEX IF NOT EXISTS idx_sensor_data_timestamp ON sensor_data("timestamp");
CREATE INDEX IF NOT EXISTS idx_sensor_data_mac_timestamp ON sensor_data(mac, "timestamp" DESC);
CREATE INDEX IF NOT EXISTS idx_sensor_data_campaign ON sensor_data(campaign_id, "timestamp" DESC) WHERE campaign_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_sensor_data_freq_range ON sensor_data(start_freq_hz, end_freq_hz);

-- sensor_gps
CREATE INDEX IF NOT EXISTS idx_sensor_gps_mac ON sensor_gps(mac);
CREATE INDEX IF NOT EXISTS idx_sensor_gps_location ON sensor_gps(lat, lng);

-- sensor_status
CREATE INDEX IF NOT EXISTS idx_sensor_status_mac ON sensor_status(mac);
CREATE INDEX IF NOT EXISTS idx_sensor_status_timestamp ON sensor_status(timestamp_ms DESC);
CREATE INDEX IF NOT EXISTS idx_sensor_status_mac_timestamp ON sensor_status(mac, timestamp_ms DESC);

-- campaigns
CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns(status);
CREATE INDEX IF NOT EXISTS idx_campaigns_dates ON campaigns(start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_campaigns_created_by ON campaigns(created_by);
CREATE INDEX IF NOT EXISTS idx_campaigns_updated_by ON campaigns(updated_by);

-- sensor_configurations
CREATE INDEX IF NOT EXISTS idx_sensor_config_mac ON sensor_configurations(mac);

-- users
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- sensors (audit)
CREATE INDEX IF NOT EXISTS idx_sensors_created_by ON sensors(created_by);
CREATE INDEX IF NOT EXISTS idx_sensors_updated_by ON sensors(updated_by);

-- antennas (audit)
CREATE INDEX IF NOT EXISTS idx_antennas_created_by ON antennas(created_by);
CREATE INDEX IF NOT EXISTS idx_antennas_updated_by ON antennas(updated_by);

-- sensor_antennas (audit)
CREATE INDEX IF NOT EXISTS idx_sensor_antennas_created_by ON sensor_antennas(created_by);
CREATE INDEX IF NOT EXISTS idx_sensor_antennas_updated_by ON sensor_antennas(updated_by);

-- audit_logs
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);

-- sensor_history_alert
CREATE INDEX IF NOT EXISTS idx_sensor_history_alert_mac ON sensor_history_alert(sensor_mac);
CREATE INDEX IF NOT EXISTS idx_sensor_history_alert_type ON sensor_history_alert(alert_type);
CREATE INDEX IF NOT EXISTS idx_sensor_history_alert_timestamp ON sensor_history_alert("timestamp" DESC);

-- compliance_reports_cache
CREATE INDEX IF NOT EXISTS idx_compliance_reports_campaign ON compliance_reports_cache(campaign_id);

-- coberturas
CREATE INDEX IF NOT EXISTS idx_coberturas_frecuencia ON coberturas(frecuencia);
CREATE INDEX IF NOT EXISTS idx_coberturas_municipio ON coberturas(municipio);

-- frecuencias_consolidadas
CREATE INDEX IF NOT EXISTS idx_frecuencias_frecuencia ON frecuencias_consolidadas(frecuencia);
CREATE INDEX IF NOT EXISTS idx_frecuencias_municipio ON frecuencias_consolidadas(municipio);

-- =====================================================================
-- PASO 7: Compresión automática (TimescaleDB)
-- =====================================================================

ALTER TABLE sensor_data SET (
    timescaledb.compress,
    timescaledb.compress_orderby = '"timestamp" DESC',
    timescaledb.compress_segmentby = 'mac'
);
SELECT add_compression_policy('sensor_data', INTERVAL '7 days', if_not_exists => TRUE);

ALTER TABLE sensor_gps SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'created_at DESC',
    timescaledb.compress_segmentby = 'mac'
);
SELECT add_compression_policy('sensor_gps', INTERVAL '7 days', if_not_exists => TRUE);

ALTER TABLE sensor_status SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'timestamp_ms DESC',
    timescaledb.compress_segmentby = 'mac'
);
SELECT add_compression_policy('sensor_status', INTERVAL '7 days', if_not_exists => TRUE);

-- =====================================================================
-- PASO 8: Retención de datos (1 año)
-- =====================================================================

SELECT add_retention_policy('sensor_data', INTERVAL '1 year', if_not_exists => TRUE);
SELECT add_retention_policy('sensor_gps', INTERVAL '1 year', if_not_exists => TRUE);
SELECT add_retention_policy('sensor_status', INTERVAL '1 year', if_not_exists => TRUE);

-- =====================================================================
-- PASO 9: Funciones auxiliares
-- =====================================================================

CREATE OR REPLACE FUNCTION compress_old_chunks(
    p_table_name TEXT,
    older_than INTERVAL
)
RETURNS INTEGER AS $$
DECLARE
    chunks_compressed INTEGER := 0;
    chunk_record RECORD;
BEGIN
    FOR chunk_record IN 
        SELECT chunk_schema, chunk_name
        FROM timescaledb_information.chunks
        WHERE hypertable_name = p_table_name
        AND range_end < NOW() - older_than
        AND NOT is_compressed
    LOOP
        EXECUTE format('SELECT compress_chunk(''%I.%I'')', 
            chunk_record.chunk_schema, chunk_record.chunk_name);
        chunks_compressed := chunks_compressed + 1;
    END LOOP;
    RETURN chunks_compressed;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_hypertable_stats()
RETURNS TABLE (
    table_name TEXT,
    total_size TEXT,
    num_chunks INTEGER,
    compressed_chunks INTEGER,
    compression_ratio TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ht.hypertable_name::TEXT,
        pg_size_pretty(hypertable_size(format('%I.%I', ht.hypertable_schema, ht.hypertable_name)))::TEXT,
        ht.num_chunks::INTEGER,
        COALESCE((
            SELECT COUNT(*)::INTEGER
            FROM timescaledb_information.chunks c
            WHERE c.hypertable_name = ht.hypertable_name
            AND c.is_compressed = true
        ), 0),
        CASE 
            WHEN EXISTS (
                SELECT 1 FROM timescaledb_information.compressed_chunk_stats ccs
                WHERE ccs.hypertable_name = ht.hypertable_name
            ) THEN
                (SELECT CONCAT(
                    ROUND((1 - SUM(after_compression_total_bytes)::NUMERIC / NULLIF(SUM(before_compression_total_bytes), 0)) * 100, 2)::TEXT,
                    '%'
                )
                FROM timescaledb_information.compressed_chunk_stats ccs
                WHERE ccs.hypertable_name = ht.hypertable_name)
            ELSE '0%'
        END::TEXT
    FROM timescaledb_information.hypertables ht
    ORDER BY ht.hypertable_name;
END;
$$ LANGUAGE plpgsql;

-- =====================================================================
-- PASO 10: Datos iniciales
-- =====================================================================

-- Configuraciones del sistema por defecto
INSERT INTO system_configurations (key, value, description) VALUES
    ('center_freq_tolerance_khz', '100', 'Tolerancia de frecuencia central (kHz)'),
    ('bandwidth_tolerance_khz', '10', 'Tolerancia de ancho de banda (kHz)'),
    ('max_monitoring_time_min', '10', 'Tiempo máximo de monitoreo (minutos)')
ON CONFLICT (key) DO NOTHING;

-- Antenas predefinidas
INSERT INTO antennas (name, type, frequency_min_hz, frequency_max_hz, gain_db, description) VALUES
    ('HyperLOG 60100', 'Directional', 600000000, 10000000000, 5.0, 'Antena direccional de banda ancha 600MHz-10GHz'),
    ('HyperLOG 7060', 'Directional', 700000000, 6000000000, 5.0, 'Antena direccional de banda ancha 700MHz-6GHz'),
    ('Omnidireccional', 'Omnidirectional', 25000000, 1300000000, 2.0, 'Antena omnidireccional 25MHz-1.3GHz')
ON CONFLICT DO NOTHING;

-- =====================================================================
-- PASO 11: Comentarios descriptivos
-- =====================================================================

COMMENT ON TABLE users IS 'Usuarios del sistema con autenticación local y Azure AD';
COMMENT ON TABLE sensors IS 'Sensores de espectro radioeléctrico registrados';
COMMENT ON TABLE antennas IS 'Catálogo de antenas disponibles';
COMMENT ON TABLE sensor_antennas IS 'Asociación sensor-antena por puerto';
COMMENT ON TABLE campaigns IS 'Campañas de medición del espectro';
COMMENT ON TABLE campaign_sensors IS 'Sensores asignados a campañas';
COMMENT ON TABLE sensor_configurations IS 'Configuraciones activas de sensores para monitoreo';
COMMENT ON TABLE sensor_data IS 'Datos de medición de espectro (hypertable TimescaleDB)';
COMMENT ON TABLE sensor_gps IS 'Datos GPS de sensores (hypertable TimescaleDB)';
COMMENT ON TABLE sensor_status IS 'Métricas de sistema de sensores - CPU, RAM, disco, temp (hypertable TimescaleDB)';
COMMENT ON TABLE compliance_reports_cache IS 'Cache de reportes de cumplimiento por campaña';
COMMENT ON TABLE sensor_history_alert IS 'Historial de alertas generadas por sensores';
COMMENT ON TABLE audit_logs IS 'Auditoría de acciones del sistema';
COMMENT ON TABLE system_configurations IS 'Configuraciones globales del sistema';
COMMENT ON TABLE coberturas IS 'Datos de coberturas de frecuencia por municipio';
COMMENT ON TABLE frecuencias_consolidadas IS 'Consolidado de frecuencias asignadas con servicios';

-- =====================================================================
-- PASO 12: Permisos finales
-- =====================================================================

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ane_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ane_user;

-- =====================================================================
-- Verificación
-- =====================================================================

\echo ''
\echo '============================================='
\echo '  BASE DE DATOS ANE REALTIME - CREADA'
\echo '============================================='
\echo ''

SELECT tablename AS tabla FROM pg_catalog.pg_tables 
WHERE schemaname = 'public' ORDER BY tablename;

\echo ''
\echo 'Hypertables:'
SELECT hypertable_name, num_chunks, compression_enabled
FROM timescaledb_information.hypertables ORDER BY hypertable_name;

\echo ''
\echo 'Resumen:'
\echo '  - 16 tablas: users, sensors, antennas, sensor_antennas,'
\echo '    campaigns, campaign_sensors, sensor_configurations,'
\echo '    sensor_data, sensor_gps, sensor_status,'
\echo '    compliance_reports_cache, sensor_history_alert,'
\echo '    audit_logs, system_configurations,'
\echo '    coberturas, frecuencias_consolidadas'
\echo '  - 3 hypertables: sensor_data, sensor_gps, sensor_status'
\echo '  - Compresión: 7 días | Retención: 1 año'
\echo ''
