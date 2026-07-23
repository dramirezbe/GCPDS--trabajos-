# ANE DB Object Inventory

Initial object list copied from the old database and refined with the later `\dt` capture.

Source:

```text
ane_db=# \d
```

Note: the first pasted `\d` output said `(28 filas)`, but only 27 object rows were visible. The later `\dt` output confirmed the missing object: table `public.antennas`.

## Summary

| Category | Count from visible rows |
| --- | ---: |
| Tables | 15 |
| Sequences | 13 |
| Visible total | 28 |
| Reported total | 28 |

## Tables

| Schema | Name | Type | Owner | Notes |
| --- | --- | --- | --- | --- |
| public | antennas | table | ane_user | Antenna catalog table |
| public | audit_logs | table | ane_user | Audit/event log candidate |
| public | campaign_sensors | table | ane_user | Likely join table between campaigns and sensors |
| public | campaigns | table | ane_user | Campaign/project entity |
| public | compliance_reports_cache | table | ane_user | Cached reporting output |
| public | sensor_antennas | table | ane_user | Sensor antenna metadata/config |
| public | sensor_configurations | table | ane_user | Sensor configuration history or settings |
| public | sensor_data | table | ane_user | Likely time-series measurements |
| public | sensor_gps | table | ane_user | Likely time-series GPS samples |
| public | sensor_history_alert | table | ane_user | Likely alert history |
| public | sensor_status | table | ane_user | Likely latest or time-series status |
| public | sensor_status_backup_20241215 | table | ane_user | Backup snapshot from 2024-12-15 |
| public | sensors | table | ane_user | Sensor/device master table |
| public | system_configurations | table | ane_user | Global system settings |
| public | users | table | ane_user | Application users |

## Sequences

| Schema | Name | Type | Owner | Likely table |
| --- | --- | --- | --- | --- |
| public | antennas_id_seq | sequence | ane_user | antennas |
| public | audit_logs_id_seq | sequence | ane_user | audit_logs |
| public | campaign_sensors_id_seq | sequence | ane_user | campaign_sensors |
| public | campaigns_id_seq | sequence | ane_user | campaigns |
| public | compliance_reports_cache_id_seq | sequence | ane_user | compliance_reports_cache |
| public | sensor_antennas_id_seq | sequence | ane_user | sensor_antennas |
| public | sensor_configurations_id_seq | sequence | ane_user | sensor_configurations |
| public | sensor_data_id_seq | sequence | ane_user | sensor_data |
| public | sensor_gps_id_seq | sequence | ane_user | sensor_gps |
| public | sensor_history_alert_id_seq | sequence | ane_user | sensor_history_alert |
| public | sensor_status_id_seq | sequence | ane_user | sensor_status |
| public | sensors_id_seq | sequence | ane_user | sensors |
| public | users_id_seq | sequence | ane_user | users |

## Raw Object Snapshot

```text
 public  | antennas_id_seq                 | secuencia | ane_user
 public  | audit_logs                      | tabla     | ane_user
 public  | audit_logs_id_seq               | secuencia | ane_user
 public  | campaign_sensors                | tabla     | ane_user
 public  | campaign_sensors_id_seq         | secuencia | ane_user
 public  | campaigns                       | tabla     | ane_user
 public  | campaigns_id_seq                | secuencia | ane_user
 public  | compliance_reports_cache        | tabla     | ane_user
 public  | compliance_reports_cache_id_seq | secuencia | ane_user
 public  | sensor_antennas                 | tabla     | ane_user
 public  | sensor_antennas_id_seq          | secuencia | ane_user
 public  | sensor_configurations           | tabla     | ane_user
 public  | sensor_configurations_id_seq    | secuencia | ane_user
 public  | sensor_data                     | tabla     | ane_user
 public  | sensor_data_id_seq              | secuencia | ane_user
 public  | sensor_gps                      | tabla     | ane_user
 public  | sensor_gps_id_seq               | secuencia | ane_user
 public  | sensor_history_alert            | tabla     | ane_user
 public  | sensor_history_alert_id_seq     | secuencia | ane_user
 public  | sensor_status                   | tabla     | ane_user
 public  | sensor_status_backup_20241215   | tabla     | ane_user
 public  | sensor_status_id_seq            | secuencia | ane_user
 public  | sensors                         | tabla     | ane_user
 public  | sensors_id_seq                  | secuencia | ane_user
 public  | system_configurations           | tabla     | ane_user
 public  | users                           | tabla     | ane_user
 public  | users_id_seq                    | secuencia | ane_user
```

## Raw Table Snapshot

```text
ane_db=# \dt
                   Listado de relaciones
 Esquema |            Nombre             | Tipo  |  Dueno
---------+-------------------------------+-------+----------
 public  | antennas                      | tabla | ane_user
 public  | audit_logs                    | tabla | ane_user
 public  | campaign_sensors              | tabla | ane_user
 public  | campaigns                     | tabla | ane_user
 public  | compliance_reports_cache      | tabla | ane_user
 public  | sensor_antennas               | tabla | ane_user
 public  | sensor_configurations         | tabla | ane_user
 public  | sensor_data                   | tabla | ane_user
 public  | sensor_gps                    | tabla | ane_user
 public  | sensor_history_alert          | tabla | ane_user
 public  | sensor_status                 | tabla | ane_user
 public  | sensor_status_backup_20241215 | tabla | ane_user
 public  | sensors                       | tabla | ane_user
 public  | system_configurations         | tabla | ane_user
 public  | users                         | tabla | ane_user
(15 filas)
```
