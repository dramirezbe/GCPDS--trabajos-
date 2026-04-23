-- Script de migración para agregar columnas de rango de filtro a sensor_configurations
-- Ejecutar este script si la tabla ya existe y necesita ser actualizada

DO $$ 
BEGIN
    -- Agregar columna filter_start_freq_hz si no existe
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='sensor_configurations' AND column_name='filter_start_freq_hz'
    ) THEN
        ALTER TABLE sensor_configurations ADD COLUMN filter_start_freq_hz BIGINT;
        RAISE NOTICE 'Columna filter_start_freq_hz agregada';
    ELSE
        RAISE NOTICE 'Columna filter_start_freq_hz ya existe';
    END IF;

    -- Agregar columna filter_end_freq_hz si no existe
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='sensor_configurations' AND column_name='filter_end_freq_hz'
    ) THEN
        ALTER TABLE sensor_configurations ADD COLUMN filter_end_freq_hz BIGINT;
        RAISE NOTICE 'Columna filter_end_freq_hz agregada';
    ELSE
        RAISE NOTICE 'Columna filter_end_freq_hz ya existe';
    END IF;
END $$;

-- Verificar las columnas agregadas
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'sensor_configurations' 
  AND column_name IN ('filter_start_freq_hz', 'filter_end_freq_hz')
ORDER BY column_name;
