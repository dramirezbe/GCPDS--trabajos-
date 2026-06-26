-- Script de migración para agregar columnas de filtro a sensor_configurations
-- Ejecutar este script si la tabla ya existe y necesita ser actualizada

-- Verificar si las columnas ya existen antes de agregarlas
DO $$ 
BEGIN
    -- Agregar columna filter_type si no existe
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='sensor_configurations' AND column_name='filter_type'
    ) THEN
        ALTER TABLE sensor_configurations ADD COLUMN filter_type VARCHAR(50);
        RAISE NOTICE 'Columna filter_type agregada';
    ELSE
        RAISE NOTICE 'Columna filter_type ya existe';
    END IF;

    -- Agregar columna filter_bw_hz si no existe
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='sensor_configurations' AND column_name='filter_bw_hz'
    ) THEN
        ALTER TABLE sensor_configurations ADD COLUMN filter_bw_hz INTEGER;
        RAISE NOTICE 'Columna filter_bw_hz agregada';
    ELSE
        RAISE NOTICE 'Columna filter_bw_hz ya existe';
    END IF;

    -- Agregar columna filter_order si no existe
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='sensor_configurations' AND column_name='filter_order'
    ) THEN
        ALTER TABLE sensor_configurations ADD COLUMN filter_order INTEGER;
        RAISE NOTICE 'Columna filter_order agregada';
    ELSE
        RAISE NOTICE 'Columna filter_order ya existe';
    END IF;
END $$;

-- Verificar las columnas agregadas
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'sensor_configurations' 
  AND column_name IN ('filter_type', 'filter_bw_hz', 'filter_order')
ORDER BY column_name;
