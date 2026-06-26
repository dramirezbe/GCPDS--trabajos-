-- Script de Restauración de Sensores de Producción ANE
-- Fecha: 2025-12-13

-- 1. Limpiar datos de sensores de prueba
DELETE FROM sensor_data WHERE mac IN ('00:11:22:33:44:55', 'AA:BB:CC:DD:EE:FF', '11:22:33:44:55:66');
DELETE FROM sensor_status WHERE mac IN ('00:11:22:33:44:55', 'AA:BB:CC:DD:EE:FF', '11:22:33:44:55:66');
DELETE FROM sensor_gps WHERE mac IN ('00:11:22:33:44:55', 'AA:BB:CC:DD:EE:FF', '11:22:33:44:55:66');
DELETE FROM sensor_configurations WHERE mac IN ('00:11:22:33:44:55', 'AA:BB:CC:DD:EE:FF', '11:22:33:44:55:66');
DELETE FROM sensor_antennas WHERE sensor_id IN (SELECT id FROM sensors WHERE mac IN ('00:11:22:33:44:55', 'AA:BB:CC:DD:EE:FF', '11:22:33:44:55:66'));

-- 2. Eliminar sensores de desarrollo
DELETE FROM sensors WHERE mac IN ('00:11:22:33:44:55', 'AA:BB:CC:DD:EE:FF', '11:22:33:44:55:66');

-- 3. Limpiar antenas duplicadas (mantener solo las primeras 4)
DELETE FROM antennas WHERE id > 4;

-- 4. Reiniciar el autoincrement de sensores
DELETE FROM sqlite_sequence WHERE name='sensors';
INSERT INTO sqlite_sequence (name, seq) VALUES ('sensors', 0);

-- 5. Insertar sensores de producción ANE (IP y Serial en description por ahora)
INSERT INTO sensors (name, mac, lat, lng, alt, status, description, created_at, updated_at) VALUES
('ANE1', 'd8:3a:dd:f7:1d:f2', 0, 0, 0, 'active', 'IP: 10.10.1.1 | Serial: 000000000000000087c867dc2945565f', strftime('%s','now')*1000, strftime('%s','now')*1000),
('ANE2', 'd8:3a:dd:f4:4e:26', 0, 0, 0, 'active', 'IP: 10.10.1.2 | Serial: 0000000000000000f75461dc288d32c3', strftime('%s','now')*1000, strftime('%s','now')*1000),
('ANE3', 'd8:3a:dd:f7:22:87', 0, 0, 0, 'active', 'IP: 10.10.1.3 | Serial: 000000000000000087c867dc2945565f', strftime('%s','now')*1000, strftime('%s','now')*1000),
('ANE4', 'd8:3a:dd:f6:fc:be', 0, 0, 0, 'active', 'IP: 10.10.1.4 | Serial: 0000000000000000b25062dc215b090b', strftime('%s','now')*1000, strftime('%s','now')*1000),
('ANE5', 'd8:3a:dd:f7:21:52', 0, 0, 0, 'active', 'IP: 10.10.1.5 | Serial: 0000000000000000f77c60dc287b27c3', strftime('%s','now')*1000, strftime('%s','now')*1000),
('ANE6', 'd8:3a:dd:f7:1a:cc', 0, 0, 0, 'active', 'IP: 10.10.1.6 | Serial: 000000000000000087c867dc2d1d885f', strftime('%s','now')*1000, strftime('%s','now')*1000),
('ANE7', 'd8:3a:dd:f7:1d:b6', 0, 0, 0, 'active', 'IP: 10.10.1.7 | Serial: 0000000000000000f75461dc298724c3', strftime('%s','now')*1000, strftime('%s','now')*1000),
('ANE8', 'd8:3a:dd:f7:1b:20', 0, 0, 0, 'active', 'IP: 10.10.1.8 | Serial: 0000000000000000272062dc232a39cb', strftime('%s','now')*1000, strftime('%s','now')*1000),
('ANE9', 'd8:3a:dd:f4:4e:d1', 0, 0, 0, 'active', 'IP: 10.10.1.9 | Serial: 0000000000000000675c62dc333e1dcf', strftime('%s','now')*1000, strftime('%s','now')*1000),
('ANE10', 'd8:3a:dd:f7:1d:90', 0, 0, 0, 'active', 'IP: 10.10.1.10 | Serial: 0000000000000000675c62dc328298cf', strftime('%s','now')*1000, strftime('%s','now')*1000),
('ANE11', 'b8:27:eb:08:e1:5d', 0, 0, 0, 'active', 'IP: 10.10.1.11 | Serial: 0000000000000000675c62dc328298cf', strftime('%s','now')*1000, strftime('%s','now')*1000);

-- 6. Asociar cada sensor con las 4 antenas
INSERT INTO sensor_antennas (sensor_id, antenna_id, port) VALUES
-- ANE1
(1, 1, 1), (1, 2, 2), (1, 3, 3), (1, 4, 4),
-- ANE2
(2, 1, 1), (2, 2, 2), (2, 3, 3), (2, 4, 4),
-- ANE3
(3, 1, 1), (3, 2, 2), (3, 3, 3), (3, 4, 4),
-- ANE4
(4, 1, 1), (4, 2, 2), (4, 3, 3), (4, 4, 4),
-- ANE5
(5, 1, 1), (5, 2, 2), (5, 3, 3), (5, 4, 4),
-- ANE6
(6, 1, 1), (6, 2, 2), (6, 3, 3), (6, 4, 4),
-- ANE7
(7, 1, 1), (7, 2, 2), (7, 3, 3), (7, 4, 4),
-- ANE8
(8, 1, 1), (8, 2, 2), (8, 3, 3), (8, 4, 4),
-- ANE9
(9, 1, 1), (9, 2, 2), (9, 3, 3), (9, 4, 4),
-- ANE10
(10, 1, 1), (10, 2, 2), (10, 3, 3), (10, 4, 4),
-- ANE11
(11, 1, 1), (11, 2, 2), (11, 3, 3), (11, 4, 4);

-- 7. VACUUM para recuperar espacio
VACUUM;

-- 8. Verificar resultados
SELECT '=== Sensores restaurados ===' as resultado;
SELECT id, name, mac, status FROM sensors ORDER BY id;

SELECT '';
SELECT '=== Antenas configuradas ===' as resultado;
SELECT id, name, type, frequency_min_hz, frequency_max_hz FROM antennas ORDER BY id;

SELECT '';
SELECT '=== Asociaciones sensor-antena ===' as resultado;
SELECT s.name as sensor, a.name as antenna, sa.port 
FROM sensor_antennas sa
JOIN sensors s ON sa.sensor_id = s.id
JOIN antennas a ON sa.antenna_id = a.id
ORDER BY s.id, sa.port;
