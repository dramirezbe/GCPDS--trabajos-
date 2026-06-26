-- Script para actualizar las 4 antenas de producción
-- Fecha: 2025-12-13

-- Actualizar las 4 antenas existentes con los datos correctos
UPDATE antennas SET 
  name = 'Antena TDT',
  type = 'Direccional',
  frequency_min_hz = 470000000,
  frequency_max_hz = 698000000,
  gain_db = 6.0,
  description = 'Antena direccional para banda TDT (470-698 MHz)',
  updated_at = strftime('%s','now')*1000
WHERE id = 1;

UPDATE antennas SET 
  name = 'Antena VHF/UHF',
  type = 'Omnidireccional',
  frequency_min_hz = 25000000,
  frequency_max_hz = 1000000000,
  gain_db = 1.5,
  description = 'Antena omnidireccional de banda ancha (25 MHz - 1 GHz)',
  updated_at = strftime('%s','now')*1000
WHERE id = 2;

UPDATE antennas SET 
  name = 'Antena >2G',
  type = 'Direccional',
  frequency_min_hz = 600000000,
  frequency_max_hz = 6000000000,
  gain_db = 3.0,
  description = 'Antena para frecuencias superiores a 2G (600 MHz - 6 GHz)',
  updated_at = strftime('%s','now')*1000
WHERE id = 3;

UPDATE antennas SET 
  name = 'ANT 500',
  type = 'Omnidireccional',
  frequency_min_hz = 75000000,
  frequency_max_hz = 1000000000,
  gain_db = 1.0,
  description = 'Antena omnidireccional ANT 500 (75 MHz - 1 GHz)',
  updated_at = strftime('%s','now')*1000
WHERE id = 4;

-- Verificar antenas actualizadas
SELECT '=== Antenas actualizadas ===' as resultado;
SELECT id, name, type, frequency_min_hz/1000000 as freq_min_mhz, frequency_max_hz/1000000 as freq_max_mhz, gain_db 
FROM antennas 
WHERE id <= 4
ORDER BY id;
